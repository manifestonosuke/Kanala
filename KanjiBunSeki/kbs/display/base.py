from abc import ABC, abstractmethod
from typing import Optional


class Display(ABC):
    @abstractmethod
    def show(self, kanji: str, data: Optional[dict]) -> None: ...
