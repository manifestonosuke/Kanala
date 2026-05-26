import re

from bs4 import BeautifulSoup

from .base import KanjiSource


# Kana ranges (excluding the half-width space `、`); ー and 中点 included.
_KATAKANA_RE = re.compile(r"^[ァ-ヺーー・]+$")
_HIRAGANA_RE = re.compile(r"^[ぁ-ゖー・]+$")

# 漢字 cell: "新" or "新 （旧）" — full-width parens, optional full-width space.
_KANJI_PAREN_RE = re.compile(r"^\s*(\S)\s*[（(]\s*(\S)\s*[）)]\s*$")


class BunkaKanjiSource(KanjiSource):
    """常用漢字表 sourced from bunka.go.jp.

    Single-page bulk source: one fetch of the 常用漢字索引 table gives all
    ~2,136 entries. No per-kanji URL, no kanji→path map.
    """

    INDEX_PATH = (
        "/kokugo_nihongo/sisaku/joho/joho/kijun/"
        "naikaku/kanji/joyokanjisakuin/index.html"
    )

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")

    def bulk_url(self) -> str:
        return self.base_url + self.INDEX_PATH

    def parse_all(self, text: str) -> dict[str, dict]:
        soup = BeautifulSoup(text, "html.parser")
        table = soup.find("table", class_="display")
        if table is None:
            raise RuntimeError(
                "bunka 常用漢字 table (table.display) not found in fetched HTML"
            )

        entries: dict[str, dict] = {}
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            kanji_cell   = cells[0].get_text(" ", strip=True)
            yomi_cell    = cells[1].get_text(" ", strip=True)
            remarks_cell = cells[3].get_text(" ", strip=True)

            kanji, kouki = self._split_kanji_cell(kanji_cell)
            if kanji is None:
                continue  # header row or empty

            on, kun = self._split_yomi_cell(yomi_cell)

            entries[kanji] = {
                "康熙": kouki,
                "読み": {
                    "音": {"常": on},
                    "訓": {"常": kun},
                },
                "備考": remarks_cell,
                "付表": {},
            }
        return entries

    @staticmethod
    def _split_kanji_cell(cell: str) -> tuple[str | None, str]:
        if not cell or cell == "漢字":
            return None, ""
        m = _KANJI_PAREN_RE.match(cell)
        if m:
            return m.group(1), m.group(2)
        c = cell.strip()
        return (c[0], "") if c else (None, "")

    @staticmethod
    def _split_yomi_cell(cell: str) -> tuple[list[str], list[str]]:
        on: list[str] = []
        kun: list[str] = []
        for tok in cell.split():
            if _KATAKANA_RE.match(tok):
                on.append(tok)
            elif _HIRAGANA_RE.match(tok):
                kun.append(tok)
        return on, kun
