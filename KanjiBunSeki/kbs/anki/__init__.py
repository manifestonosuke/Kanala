from pathlib import Path

from .base import AnkiCard
from .format import CsvFormat
from .kankenjiten import KankenjitenCard
from .tangowiki import TangowikiCard

CARDS: dict[str, type[AnkiCard]] = {
    KankenjitenCard.NAME: KankenjitenCard,
    TangowikiCard.NAME:   TangowikiCard,
}
DEFAULT_CARD = KankenjitenCard.NAME


def default_out_path(data_base: Path, card_name: str) -> Path:
    return data_base / "anki" / f"{card_name}.{CsvFormat.EXT}"
