import argparse
import sys
import time
from pathlib import Path

from .acquirer import KanjiAcquirer
from .display.cli import CliDisplay
from .map import KanjiMap, build_map
from .source.kanji.base import KanjiSource
from .sources import DEFAULT, SOURCES
from .store import KanjiStore
from .transport.base import Transport
from .transport.http import HttpTransport

SOURCE_BASE = Path("/data/home/pierre/Perso/Claude/source")
SOURCE_NAME = SOURCES[DEFAULT]["name"]
SOURCE_DIR  = SOURCE_BASE / SOURCE_NAME

KDB_NAME  = SOURCE_DIR / "kanji.json"
KMAP_NAME = SOURCE_DIR / "kanji_map.json"


def _refresh_map(
    kmap: KanjiMap, source: KanjiSource, transport: Transport, source_name: str
) -> None:
    print(f"Updating kanji map (source: {source_name})…", file=sys.stderr)
    data = build_map(source, transport)
    kmap.replace(data)
    kmap.save()
    print(f"Map saved: {len(data)} entries → {kmap.path}", file=sys.stderr)


def _resolve_identifier(
    arg: str,
    source: KanjiSource,
    transport: Transport,
    kmap: KanjiMap,
    cfg: dict,
) -> str:
    if arg.startswith(("http://", "https://")):
        ident = source.identifier_from_url(arg)
        if ident is None:
            sys.exit(f"URL not recognised by source: {arg}")
        return ident

    if len(arg) != 1:
        sys.exit(
            f"Cannot resolve {arg!r}: pass either a single kanji character or a source URL."
        )

    if not cfg["needs_map"]:
        return arg

    value = kmap.get(arg)
    if value is None:
        _refresh_map(kmap, source, transport, cfg["name"])
        value = kmap.get(arg)
    if value is None:
        sys.exit(f"「{arg}」 not found by source {cfg['name']!r}.")
    return value


def cmd_get(args: argparse.Namespace) -> None:
    cfg = SOURCES[DEFAULT]
    source: KanjiSource = cfg["class"](cfg)
    transport = HttpTransport()
    store = KanjiStore(args.store)
    display = CliDisplay()

    is_url = args.target.startswith(("http://", "https://"))
    is_kanji_char = len(args.target) == 1 and not is_url

    if is_kanji_char and not args.refresh and store.has(args.target):
        display.show(args.target, store.get(args.target))
        return

    kmap = KanjiMap(args.map)
    identifier = _resolve_identifier(args.target, source, transport, kmap, cfg)

    kanji, data = KanjiAcquirer(source, transport).acquire(identifier)
    store.add(kanji, data)
    store.save()
    display.show(kanji, data)


def cmd_map(args: argparse.Namespace) -> None:
    cfg = SOURCES[DEFAULT]
    if not cfg["needs_map"]:
        sys.exit(f"Source {cfg['name']!r} does not use a map.")
    _refresh_map(KanjiMap(args.map), cfg["class"](cfg), HttpTransport(), cfg["name"])


def _ask_continue() -> bool:
    try:
        ans = input("Continue? [Y/n] ").strip().lower()
    except EOFError:
        return False
    return ans not in {"n", "no"}


def cmd_build(args: argparse.Namespace) -> None:
    cfg = SOURCES[DEFAULT]
    source: KanjiSource = cfg["class"](cfg)
    transport = HttpTransport()
    kmap = KanjiMap(args.map)
    store = KanjiStore(args.store)

    if cfg["needs_map"] and not kmap.all():
        _refresh_map(kmap, source, transport, cfg["name"])

    if cfg["needs_map"]:
        targets = list(kmap.all().keys())
    else:
        sys.exit(f"Source {cfg['name']!r} does not use a map; build is not supported.")
    if not targets:
        sys.exit("Map is empty — nothing to build.")

    acquirer = KanjiAcquirer(source, transport)
    built = skipped = failed = 0
    stopped_at: str | None = None

    for kanji in targets:
        if not args.refresh and store.has(kanji):
            skipped += 1
            continue

        print(f"fetching {kanji}", end="", flush=True)
        start = time.perf_counter()
        try:
            k, data = acquirer.acquire(kmap.get(kanji))
            store.add(k, data)
            store.save()
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            print(f" {elapsed_ms}ms")
            built += 1
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            print(f" FAILED {elapsed_ms}ms: {e}")
            failed += 1
            if not _ask_continue():
                stopped_at = kanji
                break

    summary = f"Built {built}, skipped {skipped}, failed {failed}"
    if stopped_at is not None:
        summary += f", stopped at 「{stopped_at}」"
    print(summary)


def main() -> None:
    parser = argparse.ArgumentParser(prog="kbs")
    parser.add_argument(
        "--store",
        type=Path,
        default=KDB_NAME,
        help=f"JSON store path (default: {KDB_NAME})",
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=KMAP_NAME,
        help=f"Kanji→path map JSON (default: {KMAP_NAME})",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_get = sub.add_parser(
        "get",
        help="Show a kanji from the store, fetching it first if missing",
    )
    p_get.add_argument(
        "target",
        type=str,
        help="Kanji character (e.g. 生) or full source URL",
    )
    p_get.add_argument(
        "-r", "--refresh", action="store_true",
        help="Re-fetch from source even if the kanji is already in the store",
    )
    p_get.set_defaults(func=cmd_get)

    p_map = sub.add_parser("map", help="Rebuild the kanji→path map")
    p_map.set_defaults(func=cmd_map)

    p_build = sub.add_parser(
        "build",
        help="Fetch every kanji in the map into the local store",
    )
    p_build.add_argument(
        "-r", "--refresh", action="store_true",
        help="Re-fetch even entries already in the store",
    )
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
