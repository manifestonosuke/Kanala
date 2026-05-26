from pathlib import Path

from .format import AnkiFormat, CsvFormat, JsonFormat
from .note import AnkiNote, TangoVocabNote, Type1Note
from .view import JitenonView, KanjiView, TangoView

NOTE_TYPES: dict[str, type[AnkiNote]] = {
    "type1": Type1Note,
    "tango": TangoVocabNote,
}
FORMATS: dict[str, type[AnkiFormat]] = {
    "json": JsonFormat,
    "csv":  CsvFormat,
}
VIEWS: dict[str, type[KanjiView]] = {"jitenon": JitenonView}

DEFAULT_TYPE = "type1"
DEFAULT_FORMAT = "json"


class Anki:
    def __init__(
        self,
        view_cls: type[KanjiView],
        note: AnkiNote,
        fmt: AnkiFormat,
    ):
        self.view_cls = view_cls
        self.note = note
        self.fmt = fmt

    def generate(self, store: dict, out: Path) -> int:
        rendered = [
            self.note.render(self.view_cls(k, d)) for k, d in store.items()
        ]
        self.fmt.write(rendered, out)
        return len(rendered)


def default_out_path(data_base: Path, type_name: str, fmt_name: str) -> Path:
    return data_base / "anki" / f"{NOTE_TYPES[type_name].NAME}.{FORMATS[fmt_name].EXT}"
