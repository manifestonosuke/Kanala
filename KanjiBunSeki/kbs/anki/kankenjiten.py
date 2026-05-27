import sys
from argparse import Namespace
from pathlib import Path

from .. import kanken
from ..store import KanjiStore
from .base import AnkiCard

USAGE = (
    "Usage: kbs.py anki --type kankenjiten <selector> [<selector> ...]\n"
    "  selector = kanken level (1, 1.5, 2, 2.5, 3..10),\n"
    "             range (1-3, includes 1.5 and 2.5),\n"
    "             or a string of kanji characters (e.g. 生学校)."
)


def _is_kanji(c: str) -> bool:
    return "一" <= c <= "鿿"


class KankenjitenCard(AnkiCard):
    NAME = "kankenjiten"
    SOURCE = "jitenon"
    FIELDS = ["漢字", "部首", "音読", "訓読", "意味", "分類"]
    KEY = "漢字"

    def build(self, args: Namespace, data_base: Path) -> list[dict]:
        selectors = getattr(args, "args", None) or []
        if not selectors:
            sys.exit(USAGE)

        store_path = data_base / self.SOURCE / "kanji" / "kanji.json"
        store = KanjiStore(store_path).all()
        if not store:
            sys.exit(
                f"Empty store — run `kbs.py --source {self.SOURCE} build` first."
            )

        levels: set[str] = set()
        explicit: list[str] = []
        unknown: list[str] = []
        missing: list[str] = []

        for tok in selectors:
            parsed = kanken.parse_selector(tok)
            if parsed is not None:
                levels.update(parsed)
                continue
            for c in tok:
                if c.isspace():
                    continue
                if not _is_kanji(c):
                    unknown.append(c)
                    continue
                if c not in store:
                    missing.append(c)
                    continue
                explicit.append(c)

        if unknown:
            print(f"warning: ignoring non-kanji input: {''.join(unknown)}", file=sys.stderr)
        if missing:
            print(
                f"warning: not in store ({len(missing)}): {''.join(missing)}",
                file=sys.stderr,
            )

        selected: dict[str, dict] = {k: store[k] for k in explicit}
        if levels:
            store_labels = {kanken.LEVEL_TO_STORE[l] for l in levels}
            for k, d in store.items():
                if d.get("漢字検定") in store_labels:
                    selected.setdefault(k, d)

        if not selected:
            sys.exit("No matching kanji.")

        return [self._render(k, d) for k, d in selected.items()]

    def _render(self, kanji: str, d: dict) -> dict:
        on = d.get("読み", {}).get("音", {})
        kun = d.get("読み", {}).get("訓", {})
        return {
            "漢字": kanji,
            "部首": d.get("部首", ""),
            "音読": self._readings(on.get("常", []), on.get("外", [])),
            "訓読": self._readings(kun.get("常", []), kun.get("外", [])),
            "意味": "; ".join(d.get("意味", [])),
            "分類": self._classification(d),
        }

    @staticmethod
    def _readings(joyo: list[str], ext: list[str]) -> str:
        parts = []
        if joyo:
            parts.append("・".join(joyo))
        if ext:
            parts.append(f"[外] {'・'.join(ext)}")
        return " ".join(parts)

    @staticmethod
    def _classification(d: dict) -> str:
        parts = []
        if "常" in d.get("種別", []):
            parts.append("常")
        if d.get("漢字検定"):
            parts.append(d["漢字検定"])
        if d.get("学年"):
            parts.append(d["学年"])
        return " ".join(parts)
