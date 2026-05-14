import json
from pathlib import Path
from typing import Optional

from .source.kanji.base import KanjiSource
from .transport.base import Transport


class KanjiMap:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                self._data = json.load(f)

    def get(self, kanji: str) -> Optional[str]:
        return self._data.get(kanji)

    def has(self, kanji: str) -> bool:
        return kanji in self._data

    def replace(self, data: dict[str, str]) -> None:
        self._data = dict(data)

    def all(self) -> dict[str, str]:
        return dict(self._data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, sort_keys=True)


def build_map(source: KanjiSource, transport: Transport) -> dict[str, str]:
    """Walk source.map_pages() in order and merge into {kanji: "<label>/<path>"}.
    First occurrence wins, so the source's ordering controls precedence."""
    result: dict[str, str] = {}
    for label, url in source.map_pages():
        page_map = source.parse_map_page(transport.fetch(url))
        for kanji, path in page_map.items():
            if kanji not in result:
                result[kanji] = f"{label}/{path}"
    return result
