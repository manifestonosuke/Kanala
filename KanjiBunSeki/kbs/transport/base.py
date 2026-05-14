from abc import ABC, abstractmethod


class Transport(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str:
        """Fetch a URL and return its body as text."""
        ...
