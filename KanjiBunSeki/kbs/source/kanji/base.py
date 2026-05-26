from abc import ABC
from typing import Optional


class KanjiSource(ABC):
    """Abstract base for kanji data sources.

    Two operating modes:

    - **Per-kanji** (jitenon): implement `url_for`, `parse`, `map_pages`,
      `parse_map_page`, `identifier_from_url`. The acquirer fetches one URL
      per kanji.
    - **Bulk** (bunka.org): implement `bulk_url` and `parse_all`. A single fetch
      yields every entry. The registry marks these with `"bulk": True`.

    Methods a source doesn't use raise NotImplementedError by default.
    """

    # ---- per-kanji mode ------------------------------------------------
    def url_for(self, identifier: str) -> str:
        raise NotImplementedError(f"{type(self).__name__} has no per-kanji URL")

    def parse(self, text: str) -> dict:
        raise NotImplementedError(f"{type(self).__name__} has no per-kanji parse")

    def map_pages(self) -> list[tuple[str, str]]:
        raise NotImplementedError(f"{type(self).__name__} has no map pages")

    def parse_map_page(self, text: str) -> dict[str, str]:
        raise NotImplementedError(f"{type(self).__name__} has no map parser")

    def identifier_from_url(self, url: str) -> Optional[str]:
        return None

    # ---- bulk mode -----------------------------------------------------
    def bulk_url(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} is not a bulk source")

    def parse_all(self, text: str) -> dict[str, dict]:
        """Parse a bulk-fetched page into {kanji_char: data}."""
        raise NotImplementedError(f"{type(self).__name__} is not a bulk source")
