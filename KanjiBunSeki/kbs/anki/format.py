import csv
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


class CsvFormat(AnkiFormat):
    """Tab-separated, append mode. Anki imports TSV cleanly; cell content
    with embedded `<br>` is rendered as a line break inside the card."""

    EXT = "csv"
    DELIMITER = "\t"

    def write(self, notes: list[dict], out: Path) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(
                f,
                delimiter=self.DELIMITER,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )
            for n in notes:
                writer.writerow(list(n.values()))
