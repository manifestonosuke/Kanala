import json
from pathlib import Path
from typing import Optional


class KanjiStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def add(self, kanji: str, data: dict) -> None:
        self._data[kanji] = data

    def get(self, kanji: str) -> Optional[dict]:
        return self._data.get(kanji)

    def has(self, kanji: str) -> bool:
        return kanji in self._data

    def all(self) -> dict:
        return dict(self._data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
