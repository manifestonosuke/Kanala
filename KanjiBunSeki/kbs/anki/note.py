from abc import ABC, abstractmethod

from .view import KanjiView, TangoView


class AnkiNote(ABC):
    NAME: str
    FIELDS: list[str]

    @abstractmethod
    def render(self, view) -> dict: ...


class Type1Note(AnkiNote):
    NAME = "kbs-type1"
    FIELDS = ["漢字", "部首", "音読", "訓読", "意味", "分類"]

    def render(self, view: KanjiView) -> dict:
        return {
            "漢字": view.kanji(),
            "部首": view.bushu(),
            "音読": self._readings(*view.on()),
            "訓読": self._readings(*view.kun()),
            "意味": "; ".join(view.imi()),
            "分類": self._classification(view),
        }

    @staticmethod
    def _readings(joyo: list[str], ext: list[str]) -> str:
        parts = []
        if joyo:
            parts.append("・".join(joyo))
        if ext:
            parts.append(f"[外] {'・'.join(ext)}")
        return " ".join(parts)

    @staticmethod
    def _classification(view: KanjiView) -> str:
        parts = []
        if view.is_joyo():
            parts.append("常")
        if view.kanken():
            parts.append(view.kanken())
        if view.gakunen():
            parts.append(view.gakunen())
        return " ".join(parts)


class TangoVocabNote(AnkiNote):
    NAME = "kbs-tango"
    FIELDS = ["表", "裏"]

    def render(self, view: TangoView) -> dict:
        lines = [view.headword()]
        for d in view.definitions():
            field = d.get("分野", "")
            text = d.get("本文", "")
            lines.append(f"[{field}] {text}" if field else text)
        return {
            "表": view.reading(),
            "裏": "<br>".join(lines),
        }
