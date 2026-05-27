from abc import ABC, abstractmethod
from argparse import Namespace
from pathlib import Path


class AnkiCard(ABC):
    NAME: str
    SOURCE: str
    FIELDS: list[str]
    KEY: str

    @abstractmethod
    def build(self, args: Namespace, data_base: Path) -> list[dict]:
        """Return rendered rows ({field_name: value}). May prompt the user."""
