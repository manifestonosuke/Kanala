import sys
import time
from argparse import Namespace
from pathlib import Path

from ..sources import SOURCES
from ..tango import Tango
from ..transport.http import HttpTransport
from .base import AnkiCard


class TangowikiCard(AnkiCard):
    NAME = "tangowiki"
    SOURCE = "wiktionary"
    FIELDS = ["見出し", "表", "裏"]
    KEY = "見出し"

    def build(self, args: Namespace, data_base: Path) -> list[dict]:
        tokens = getattr(args, "args", None) or []
        if len(tokens) != 1:
            sys.exit("Usage: kbs.py anki --type tangowiki <word>")
        word = tokens[0]

        cfg = SOURCES[self.SOURCE]
        source = cfg["class"](cfg)
        transport = HttpTransport()

        print(f"fetching {source.url_for(word)}", end="", flush=True)
        start = time.perf_counter()
        try:
            entry = Tango(source, transport).lookup(word)
        except Exception as e:
            print(" FAILED")
            sys.exit(f"  {e}")
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        print(f" {elapsed_ms}ms")

        self._show(entry)
        selected = self._prompt_selection(entry["語義"])
        return [self._render(entry, selected)]

    @staticmethod
    def _show(entry: dict) -> None:
        headword = entry["見出し"]
        reading = entry["読み"][0] if entry["読み"] else ""
        pos = entry["品詞"]
        print()
        print(f"{headword} ({reading}) — {pos}")
        for d in entry["語義"]:
            tag = f"[{d['分野']}] " if d["分野"] else ""
            print(f"  {d['番号']}. {tag}{d['本文']}")

    def _prompt_selection(self, definitions: list[dict]) -> list[int]:
        while True:
            try:
                raw = input("\n採用する語義の番号は？ (例: 1,3-5)  > ")
            except EOFError:
                sys.exit("\nNo selection given.")
            try:
                picked = _parse_selection(raw, len(definitions))
                if picked:
                    return picked
            except ValueError as e:
                print(f"  入力が無効です: {e}")

    def _render(self, entry: dict, selected: list[int]) -> dict:
        headword = entry["見出し"]
        reading = entry["読み"][0] if entry["読み"] else ""
        keep = set(selected)
        lines = [headword]
        for d in entry["語義"]:
            if d["番号"] not in keep:
                continue
            field = d.get("分野", "")
            text = d.get("本文", "")
            lines.append(f"[{field}] {text}" if field else text)
        return {
            "見出し": headword,
            "表": reading,
            "裏": "<br>".join(lines),
        }


def _parse_selection(raw: str, n: int) -> list[int]:
    if not raw.strip():
        raise ValueError("empty selection")
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a), int(b)
            if lo > hi:
                raise ValueError(f"invalid range {part!r}")
            result.update(range(lo, hi + 1))
        else:
            result.add(int(part))
    if not all(1 <= i <= n for i in result):
        raise ValueError(f"numbers must be between 1 and {n}")
    return sorted(result)
