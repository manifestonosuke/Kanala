from abc import ABC, abstractmethod
from typing import Optional


class KanjiSource(ABC):
    @abstractmethod
    def url_for(self, identifier: str) -> str:
        """Build a fetch URL from a map value or path identifier.

        The identifier may include a leading kanken-level segment
        (e.g. "kyu05/kanji/043") as recorded in the map; that segment
        is informational and is stripped before building the URL.
        """
        ...

    @abstractmethod
    def parse(self, text: str) -> dict:
        """Parse a fetched entry page into {"kanji": str, "data": dict}."""
        ...

    @abstractmethod
    def map_pages(self) -> list[tuple[str, str]]:
        """Return the list of (label, url) pages to scrape for the kanji→path map.

        Label is the metadata prefix prepended to each kanji's path in the map.
        Order matters: first occurrence of a kanji wins, so iterate easiest-first.
        """
        ...

    @abstractmethod
    def parse_map_page(self, text: str) -> dict[str, str]:
        """Parse a map page into {kanji_char: path}, where path is the
        source-specific URL fragment without any label prefix."""
        ...

    @abstractmethod
    def identifier_from_url(self, url: str) -> Optional[str]:
        """If `url` is a recognised entry URL for this source, return the
        path identifier (e.g. "kanji/043"); else return None."""
        ...
