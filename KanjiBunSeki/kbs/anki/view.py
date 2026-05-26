from abc import ABC, abstractmethod


class KanjiView(ABC):
    @abstractmethod
    def kanji(self) -> str: ...
    @abstractmethod
    def bushu(self) -> str: ...
    @abstractmethod
    def on(self) -> tuple[list[str], list[str]]: ...
    @abstractmethod
    def kun(self) -> tuple[list[str], list[str]]: ...
    @abstractmethod
    def imi(self) -> list[str]: ...
    @abstractmethod
    def is_joyo(self) -> bool: ...
    @abstractmethod
    def kanken(self) -> str: ...
    @abstractmethod
    def gakunen(self) -> str: ...


class JitenonView(KanjiView):
    def __init__(self, kanji: str, data: dict):
        self._k = kanji
        self._d = data

    def kanji(self) -> str:
        return self._k

    def bushu(self) -> str:
        return self._d.get("部首", "")

    def on(self) -> tuple[list[str], list[str]]:
        block = self._d.get("読み", {}).get("音", {})
        return block.get("常", []), block.get("外", [])

    def kun(self) -> tuple[list[str], list[str]]:
        block = self._d.get("読み", {}).get("訓", {})
        return block.get("常", []), block.get("外", [])

    def imi(self) -> list[str]:
        return self._d.get("意味", [])

    def is_joyo(self) -> bool:
        return "常" in self._d.get("種別", [])

    def kanken(self) -> str:
        return self._d.get("漢字検定", "")

    def gakunen(self) -> str:
        return self._d.get("学年", "")
