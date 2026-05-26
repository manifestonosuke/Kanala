import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import TangoSource


_POS_HEADINGS = (
    "名詞", "動詞", "形容詞", "形容動詞", "副詞",
    "連体詞", "感動詞", "接続詞", "助詞", "助動詞",
)

_READING_RE = re.compile(r"[（(]\s*([぀-ゟ・ー]+)\s*[）)]")
_FIELD_RE   = re.compile(r"^[（(]\s*([^)）]+?)\s*[）)]\s*(.+)$")


class WiktionaryTangoSource(TangoSource):
    def url_for(self, word: str) -> str:
        return f"{self.base_url}/wiki/{quote(word)}"

    def parse(self, text: str, word: str) -> dict:
        soup = BeautifulSoup(text, "html.parser")
        ja = self._find_japanese_section(soup)
        if ja is None:
            raise ValueError(f"No 日本語 section for {word!r}")

        entry: dict = {
            "見出し": word,
            "読み":   [],
            "品詞":   "",
            "語義":   [],
        }

        in_pos = False
        for el in ja.find_all_next():
            if el.name == "h2":
                break
            if el.name == "h3":
                heading = self._heading_text(el)
                if heading in _POS_HEADINGS:
                    in_pos = True
                    if not entry["品詞"]:
                        entry["品詞"] = heading
                else:
                    in_pos = False
                continue
            if not in_pos:
                continue
            if el.name == "p" and not entry["読み"]:
                reading = self._extract_reading(el)
                if reading:
                    entry["読み"].append(reading)
            if el.name == "ol" and not entry["語義"]:
                entry["語義"] = self._parse_definitions(el)
                break

        if not entry["語義"]:
            raise ValueError(f"No definitions found for {word!r}")
        return entry

    @staticmethod
    def _find_japanese_section(soup: BeautifulSoup):
        for h in soup.find_all("h2"):
            if h.get_text(strip=True) == "日本語":
                return h
        return None

    @staticmethod
    def _heading_text(el) -> str:
        for s in el.find_all("span"):
            t = s.get_text(strip=True)
            if t:
                return t
        return el.get_text(strip=True)

    @classmethod
    def _extract_reading(cls, p) -> str:
        text = p.get_text("", strip=True)
        m = _READING_RE.search(text)
        return m.group(1) if m else ""

    @classmethod
    def _parse_definitions(cls, ol) -> list[dict]:
        defs: list[dict] = []
        for i, li in enumerate(ol.find_all("li", recursive=False), 1):
            for nested in li.find_all(["ol", "ul", "dl"]):
                nested.decompose()
            text = li.get_text("", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            m = _FIELD_RE.match(text)
            if m:
                defs.append({"番号": i, "分野": m.group(1), "本文": m.group(2)})
            else:
                defs.append({"番号": i, "分野": "", "本文": text})
        return defs
