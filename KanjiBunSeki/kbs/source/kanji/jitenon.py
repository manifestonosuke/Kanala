import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import CData, Comment

from .base import KanjiSource


class JitenonKanjiSource(KanjiSource):
    # Kanken levels, ordered easiest → hardest so first-occurrence wins gives
    # each kanji its lowest-difficulty level.
    KYU_LABELS = [
        "kyu10", "kyu09", "kyu08", "kyu07", "kyu06",
        "kyu05", "kyu04", "kyu03", "kyu02j", "kyu02",
        "kyu01j", "kyu01",
    ]

    _KYU_RE = re.compile(r"^kyu\d+j?$")

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        escaped = re.escape(self.base_url)
        self._ENTRY_URL_RE = re.compile(rf"^{escaped}/(kanji[a-z]?)/(\d+)/?$")
        self._MAP_HREF_RE = re.compile(rf"{escaped}/(kanji[a-z]?)/(\d+)")

    CLASS_MAP = {
        "教育漢字": "教",
        "常用漢字": "常",
        "名前に使える漢字": "名",
        "人名用漢字": "人",
        "表外漢字": "外",
    }

    YOMI_ICON_TO_BUCKET = {
        "1": "常",
        "2": "常",
        "3": "常",
        "4": "外",
    }

    ZEN_TO_HAN = str.maketrans("０１２３４５６７８９＋－", "0123456789+-")

    def url_for(self, identifier: str) -> str:
        path = self._strip_kyu(identifier)
        return f"{self.base_url}/{path}"

    @classmethod
    def _strip_kyu(cls, identifier: str) -> str:
        head, sep, rest = identifier.partition("/")
        return rest if sep and cls._KYU_RE.match(head) else identifier

    def identifier_from_url(self, url: str) -> Optional[str]:
        m = self._ENTRY_URL_RE.match(url)
        if not m:
            return None
        return f"{m.group(1)}/{m.group(2)}"

    def map_pages(self) -> list[tuple[str, str]]:
        return [(label, f"{self.base_url}/cat/{label}") for label in self.KYU_LABELS]

    def parse_map_page(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        out: dict[str, str] = {}
        for a in soup.find_all("a", href=self._MAP_HREF_RE):
            m = self._MAP_HREF_RE.match(a["href"])
            if not m:
                continue
            text = a.get_text(strip=True)
            if not text:
                continue
            kanji = text[-1]  # listing format is "<rank-digit?><kanji>"
            path = f"{m.group(1)}/{m.group(2)}"
            out.setdefault(kanji, path)
        return out

    def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        kanji = self._kanji_char(soup)
        return {"kanji": kanji, "data": self._extract(soup)}

    @staticmethod
    def _kanji_char(soup: BeautifulSoup) -> str:
        h1 = soup.select_one("h1.ttl_main")
        if h1 is None:
            raise ValueError("Page title (h1.ttl_main) not found")
        m = re.search(r"「(.)」", h1.get_text())
        if not m:
            raise ValueError(f"Cannot extract kanji from h1: {h1.get_text()!r}")
        return m.group(1)

    @classmethod
    def _label(cls, elem: Tag) -> str:
        """Return text content with ruby <rt> furigana stripped."""
        clone = BeautifulSoup(str(elem), "html.parser")
        for rt in clone.select("rt"):
            rt.decompose()
        return clone.get_text(strip=True)

    @staticmethod
    def _full_text(elem: Tag) -> str:
        """Return all text including ruby furigana (BS4's RubyTextString)."""
        parts: list[str] = []
        for d in elem.descendants:
            if isinstance(d, NavigableString) and not isinstance(d, (Comment, CData)):
                parts.append(str(d))
        return "".join(parts).strip()

    def _extract(self, soup: BeautifulSoup) -> dict:
        table = soup.select_one("table.kanjirighttb")
        if table is None:
            raise ValueError("Main info table (table.kanjirighttb) not found")

        rows = self._labelled_rows(table)
        out: dict = {}
        out["読み"] = self._readings(rows)
        out["部首"] = self._radical(rows)
        out["画数"] = self._strokes(rows)
        shubetsu = self._shubetsu(rows)
        out["種別"] = shubetsu
        out["学年"] = self._gakunen(rows)
        out["漢字検定"] = self._kentei(rows)
        out["意味"] = self._meanings(rows)
        out["Unicode"] = self._unicode(soup)
        out["漢字構成"] = self._kousei(soup)
        out["分類"] = self._bunrui(shubetsu)
        return out

    def _labelled_rows(self, table: Tag) -> list[tuple[str, Tag]]:
        """Walk table rows, propagating <th rowspan=...> labels to subsequent <td> rows."""
        pairs: list[tuple[str, Tag]] = []
        current_label: Optional[str] = None
        for tr in table.select("tr"):
            th = tr.find("th", recursive=False)
            td = tr.find("td", recursive=False)
            if th is not None:
                current_label = self._label(th)
            if td is not None and current_label is not None:
                pairs.append((current_label, td))
        return pairs

    def _readings(self, rows: list[tuple[str, Tag]]) -> dict:
        out: dict = {"音": {}, "訓": {}}
        for label, td in rows:
            if label == "音読み":
                key = "音"
            elif label == "訓読み":
                key = "訓"
            else:
                continue
            bucket = self._yomi_bucket(td)
            reading = self._reading_text(td)
            if not reading:
                continue
            out[key].setdefault(bucket, []).append(reading)
        return {k: v for k, v in out.items() if v}

    def _yomi_bucket(self, td: Tag) -> str:
        img = td.select_one("span.yomi_icon img")
        if img is None:
            return "常"
        src = img.get("src", "")
        m = re.search(r"yomi_icon(\d+)", src)
        if not m:
            return "常"
        return self.YOMI_ICON_TO_BUCKET.get(m.group(1), "常")

    def _reading_text(self, td: Tag) -> str:
        a = td.select_one("a")
        text = self._label(a if a is not None else td)
        text = text.translate(self.ZEN_TO_HAN)
        text = re.sub(r"[（(](.+?)[)）]", r".\1", text)
        return text

    def _radical(self, rows) -> str:
        for label, td in rows:
            if label != "部首":
                continue
            text = self._label(td)
            m = re.match(r"(.)部", text)
            return m.group(1) if m else text
        return ""

    def _strokes(self, rows) -> str:
        for label, td in rows:
            if label != "画数":
                continue
            text = self._label(td).translate(self.ZEN_TO_HAN)
            total = re.search(r"(\d+)画", text)
            split = re.search(r"(\d+)\+(\d+)", text)
            if total and split:
                return f"{total.group(1)}:{split.group(1)}+{split.group(2)}"
            return total.group(1) if total else text
        return ""

    def _shubetsu(self, rows) -> list[str]:
        for label, td in rows:
            if label != "種別":
                continue
            text = self._label(td)
            return [self.CLASS_MAP.get(p.strip(), p.strip()) for p in text.split("/")]
        return []

    def _gakunen(self, rows) -> str:
        for label, td in rows:
            if label != "学年":
                continue
            text = self._label(td).translate(self.ZEN_TO_HAN)
            m = re.search(r"小学校(\d+)年生", text)
            if m:
                return f"小{m.group(1)}"
            if "中学校" in text:
                return "中"
            if "高校" in text or "高等学校" in text:
                return "高"
            return text
        return ""

    def _kentei(self, rows) -> str:
        for label, td in rows:
            if label != "漢字検定":
                continue
            return self._label(td).translate(self.ZEN_TO_HAN)
        return ""

    def _meanings(self, rows) -> list[str]:
        out: list[str] = []
        for label, td in rows:
            if label != "意味":
                continue
            out.append(self._full_text(td))
        return out

    def _unicode(self, soup: BeautifulSoup) -> str:
        tbl = soup.select_one("table.moji_code")
        if tbl is None:
            return ""
        for tr in tbl.select("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th is not None and td is not None and self._label(th) == "Unicode":
                return self._label(td)
        return ""

    def _kousei(self, soup: BeautifulSoup) -> list[str]:
        h2 = soup.find("h2", id="m_kousei")
        if h2 is None:
            return []
        section = h2.find_parent("section") or h2.parent
        out: list[str] = []
        for li in section.select("ul li"):
            a = li.select_one("a")
            txt = (a or li).get_text(strip=True)
            if txt:
                out.append(txt)
        return out

    @staticmethod
    def _bunrui(shubetsu: list[str]) -> dict:
        out: dict = {}
        if "教" in shubetsu:
            out["教"] = [True, []]
        if "常" in shubetsu:
            out["常"] = [True, []]
        if "人" in shubetsu or ("名" in shubetsu and "常" not in shubetsu):
            out["人名"] = [True, []]
        return out
