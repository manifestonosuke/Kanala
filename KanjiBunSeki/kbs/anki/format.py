import json
from abc import ABC, abstractmethod
from pathlib import Path


class AnkiFormat(ABC):
    EXT: str

    @abstractmethod
    def write(self, notes: list[dict], out: Path) -> None: ...


class JsonFormat(AnkiFormat):
    EXT = "json"

    def write(self, notes: list[dict], out: Path) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(notes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
