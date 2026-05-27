import argparse
import sys
import time
from pathlib import Path

from . import anki, kanken
from .acquirer import KanjiAcquirer
from .display.cli import CliDisplay
from .map import KanjiMap, build_map
from .source.kanji.base import KanjiSource
from .sources import DEFAULT, DEFAULT_TANGO, SOURCES
from .store import KanjiStore
from .tango import Tango
from .transport.base import Transport
from .transport.http import HttpTransport

DATA_BASE = Path(__file__).resolve().parent.parent / "data"


def _data_dir(source_name: str) -> Path:
    return DATA_BASE / source_name / "kanji"


def _resolve_paths(args: argparse.Namespace) -> None:
    cfg = SOURCES.get(args.source, {})
    if cfg.get("type") != "kanji":
        return
    d = _data_dir(args.source)
    if args.store is None:
        args.store = d / "kanji.json"
    if args.map is None:
        args.map = d / "kanji_map.json"


def _vcheck(args: argparse.Namespace, label: str, path: Path) -> None:
    if args.verbose:
        state = "exists" if path.exists() else "missing"
        print(f"[v] {label}: {path} ({state})", file=sys.stderr)


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
    cfg = SOURCES[args.source]
    source: KanjiSource = cfg["class"](cfg)
    transport = HttpTransport()
    _vcheck(args, "Store", args.store)
    store = KanjiStore(args.store)
    display = CliDisplay()

    is_url = args.target.startswith(("http://", "https://"))
    is_kanji_char = len(args.target) == 1 and not is_url

    if is_kanji_char and not args.refresh and store.has(args.target):
        display.show(args.target, store.get(args.target))
        return

    if cfg["bulk"]:
        sys.exit(
            f"Source {cfg['name']!r} is bulk-only; run "
            f"`kbs.py --source {cfg['name']} build` first, then `get` reads from the store."
        )

    _vcheck(args, "Map", args.map)
    kmap = KanjiMap(args.map)
    identifier = _resolve_identifier(args.target, source, transport, kmap, cfg)

    kanji, data = KanjiAcquirer(source, transport).acquire(identifier)
    store.add(kanji, data)
    store.save()
    display.show(kanji, data)


def cmd_map(args: argparse.Namespace) -> None:
    cfg = SOURCES[args.source]
    if not cfg["needs_map"]:
        sys.exit(f"Source {cfg['name']!r} does not use a map.")
    _vcheck(args, "Map", args.map)
    _refresh_map(KanjiMap(args.map), cfg["class"](cfg), HttpTransport(), cfg["name"])


def _ask_continue() -> bool:
    try:
        ans = input("Continue? [Y/n] ").strip().lower()
    except EOFError:
        return False
    return ans not in {"n", "no"}


def _build_bulk(
    args: argparse.Namespace,
    cfg: dict,
    source: KanjiSource,
    transport: Transport,
    store: KanjiStore,
) -> None:
    print(f"fetching {source.bulk_url()}", end="", flush=True)
    start = time.perf_counter()
    entries = KanjiAcquirer(source, transport).acquire_all()
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    print(f" {elapsed_ms}ms → {len(entries)} entries")

    added = updated = 0
    for kanji, data in entries.items():
        if store.has(kanji):
            if not args.refresh:
                continue
            updated += 1
        else:
            added += 1
        store.add(kanji, data)
    store.save()
    skipped = len(entries) - added - updated
    print(
        f"Built {added} new, {updated} refreshed, {skipped} skipped → {args.store}"
    )


def cmd_build(args: argparse.Namespace) -> None:
    cfg = SOURCES[args.source]
    source: KanjiSource = cfg["class"](cfg)
    transport = HttpTransport()
    _vcheck(args, "Store", args.store)
    store = KanjiStore(args.store)

    if cfg["bulk"]:
        _build_bulk(args, cfg, source, transport, store)
        return

    _vcheck(args, "Map", args.map)
    kmap = KanjiMap(args.map)

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


def _is_kanji(c: str) -> bool:
    return "一" <= c <= "鿿"


KANKEN_LEVEL_TO_STORE = kanken.LEVEL_TO_STORE
KANKEN_DISPLAY_ORDER = kanken.DISPLAY_ORDER
KANKEN_STORE_TO_LEVEL = kanken.STORE_TO_LEVEL


def _print_rows(rows: list[tuple[str, list[str]]]) -> None:
    rows = [r for r in rows if r[1]]
    if not rows:
        return
    width = max(len(label) for label, _ in rows)
    for label, chars in rows:
        print(f"{label:<{width}} : {''.join(chars)} : {len(chars)} kanji")


def _classify_three(
    query: str, entries: dict, predicate
) -> tuple[list[str], list[str], list[str]]:
    in_, out, unknown = [], [], []
    for c in query:
        if c.isspace():
            continue
        if not _is_kanji(c):
            out.append(c)
            continue
        data = entries.get(c)
        if data is None:
            unknown.append(c)
        elif predicate(data):
            in_.append(c)
        else:
            out.append(c)
    return in_, out, unknown


def _list_matching(
    args: argparse.Namespace, entries: dict, predicate, label: str
) -> None:
    hits = [k for k, v in entries.items() if predicate(v)]
    if not hits:
        sys.exit(f"No {label} kanji in store.")
    print("".join(hits), flush=True)
    if args.verbose:
        print(f"[v] {len(hits)} kanji displayed", file=sys.stderr)


def cmd_anki(args: argparse.Namespace) -> None:
    card_cls = anki.CARDS.get(args.type)
    if card_cls is None:
        sys.exit(
            f"Unknown anki type {args.type!r}. Available: {', '.join(sorted(anki.CARDS))}"
        )
    card = card_cls()
    rows = card.build(args, DATA_BASE)
    out = args.out or anki.default_out_path(DATA_BASE, card.NAME)
    added, replaced, skipped = anki.CsvFormat().write(
        rows, out, card.FIELDS, card.KEY,
    )
    print(f"{card.NAME}: added {added}, replaced {replaced}, skipped {skipped} → {out}")


def cmd_tango(args: argparse.Namespace) -> None:
    source_name = args.source
    cfg = SOURCES.get(source_name)
    if not cfg or cfg.get("type") != "tango":
        source_name = DEFAULT_TANGO
        cfg = SOURCES[source_name]

    source = cfg["class"](cfg)
    transport = HttpTransport()

    url = source.url_for(args.word)
    print(f"fetching {url}", end="", flush=True)
    start = time.perf_counter()
    try:
        entry = Tango(source, transport).lookup(args.word)
    except Exception as e:
        print(" FAILED")
        sys.exit(f"  {e}")
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    print(f" {elapsed_ms}ms")

    headword = entry["見出し"]
    reading = entry["読み"][0] if entry["読み"] else ""
    pos = entry["品詞"]
    print()
    print(f"{headword} ({reading}) — {pos}")
    for d in entry["語義"]:
        tag = f"[{d['分野']}] " if d["分野"] else ""
        print(f"  {d['番号']}. {tag}{d['本文']}")


def cmd_kanken(args: argparse.Namespace) -> None:
    _vcheck(args, "Store", args.store)
    store = KanjiStore(args.store)
    entries = store.all()
    if not entries:
        sys.exit("No data in store.")

    if not args.args:
        sys.exit(
            "Usage: kbs.py kanken <level> [<kanji>...]   "
            "OR kbs.py kanken <kanji>...   "
            f"(levels: {' '.join(KANKEN_DISPLAY_ORDER)})"
        )

    first = args.args[0]
    if first in KANKEN_LEVEL_TO_STORE:
        target = KANKEN_LEVEL_TO_STORE[first]
        predicate = lambda d: d.get("漢字検定") == target
        query = "".join(args.args[1:])

        if not query:
            _list_matching(args, entries, predicate, f"kanken {first}")
            return

        in_, out, unknown = _classify_three(query, entries, predicate)
        _print_rows([
            (f"kanken {first}", in_),
            (f"not kanken {first}", out),
            ("unknown", unknown),
        ])
        return

    query = "".join(args.args)
    buckets: dict[str, list[str]] = {lvl: [] for lvl in KANKEN_DISPLAY_ORDER}
    unknown = []
    for c in query:
        if c.isspace():
            continue
        if not _is_kanji(c):
            unknown.append(c)
            continue
        data = entries.get(c)
        if data is None:
            unknown.append(c)
            continue
        lvl = KANKEN_STORE_TO_LEVEL.get(data.get("漢字検定"))
        if lvl is None:
            unknown.append(c)
        else:
            buckets[lvl].append(c)

    rows = [(f"kanken {lvl}", buckets[lvl]) for lvl in KANKEN_DISPLAY_ORDER if buckets[lvl]]
    if unknown:
        rows.append(("unknown", unknown))
    if not rows:
        sys.exit("No kanji to classify.")
    _print_rows(rows)


def _is_joyo(data: dict) -> bool:
    return "常" in data.get("種別", [])


def cmd_joyo(args: argparse.Namespace) -> None:
    _vcheck(args, "Store", args.store)
    store = KanjiStore(args.store)
    entries = store.all()
    if not entries:
        sys.exit("No data in store.")

    if not args.kanji:
        _list_matching(args, entries, _is_joyo, "joyo")
        return

    in_, out, unknown = _classify_three(
        "".join(args.kanji), entries, _is_joyo
    )
    _print_rows([("joyo", in_), ("not joyo", out), ("unknown", unknown)])


def main() -> None:
    parser = argparse.ArgumentParser(prog="kbs")
    parser.add_argument(
        "--source",
        choices=sorted(SOURCES.keys()),
        default=DEFAULT,
        help=f"Data source (default: {DEFAULT})",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="JSON store path (default: <data>/<source>/kanji/kanji.json)",
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=None,
        help="Kanji→path map JSON (default: <data>/<source>/kanji/kanji_map.json)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print source file check messages to stderr",
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

    p_joyo = sub.add_parser(
        "joyo",
        help="Without args: list all 常用 kanji in the store. With args: classify each input kanji as joyo / not joyo / unknown.",
    )
    p_joyo.add_argument(
        "kanji",
        nargs="*",
        type=str,
        help="Optional kanji string(s) (e.g. 生今明 or 罪 漢字検定). When given, classifies each character.",
    )
    p_joyo.set_defaults(func=cmd_joyo)

    p_kanken = sub.add_parser(
        "kanken",
        help="Kanken (漢字検定) by level. `kanken <lvl>` lists; `kanken <lvl> <kanji>` classifies; `kanken <kanji>...` aggregates per level.",
    )
    p_kanken.add_argument(
        "args",
        nargs="*",
        type=str,
        help="Optional level (1, 1.5, 2, 2.5, 3..10) followed by kanji string(s).",
    )
    p_kanken.set_defaults(func=cmd_kanken)

    p_anki = sub.add_parser(
        "anki",
        help="Add Anki cards. Each --type is bound to one source; output is CSV.",
    )
    p_anki.add_argument(
        "--type",
        choices=sorted(anki.CARDS.keys()),
        default=anki.DEFAULT_CARD,
        help=f"Card type (default: {anki.DEFAULT_CARD})",
    )
    p_anki.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: data/anki/<type>.csv)",
    )
    p_anki.add_argument(
        "args",
        nargs="*",
        type=str,
        help="Card-specific args. tangowiki: one word. kankenjiten: kanken levels/ranges and/or kanji chars.",
    )
    p_anki.set_defaults(func=cmd_anki)

    p_tango = sub.add_parser(
        "tango",
        help="Display a vocabulary entry (lookup only — use `anki --type tangowiki <word>` to add a card).",
    )
    p_tango.add_argument(
        "word",
        type=str,
        help="Word to look up (e.g. 幕府).",
    )
    p_tango.set_defaults(func=cmd_tango)

    args = parser.parse_args()
    _resolve_paths(args)
    args.func(args)


if __name__ == "__main__":
    main()
