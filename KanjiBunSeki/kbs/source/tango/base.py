from abc import ABC, abstractmethod


class TangoSource(ABC):
    """Abstract base for vocabulary (単語) data sources.

    One lookup → one URL → one structured entry. The acquirer (`Tango`)
    composes a TangoSource with a Transport.
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.base_url = cfg["base_url"]

    @abstractmethod
    def url_for(self, word: str) -> str:
        """Build the fetch URL for the given word."""

    @abstractmethod
    def parse(self, text: str, word: str) -> dict:
        """Parse the fetched page into a structured entry.

        Returns a dict with keys: 見出し, 読み (list), 品詞, 語義 (list of
        {番号, 分野, 本文}). The acquirer stamps 取得日時.
        """
