from datetime import datetime, timezone

from .source.tango.base import TangoSource
from .transport.base import Transport


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Tango:
    """Vocabulary acquirer — composes a TangoSource with a Transport."""

    def __init__(self, source: TangoSource, transport: Transport):
        self._source = source
        self._transport = transport

    def lookup(self, word: str) -> dict:
        url = self._source.url_for(word)
        text = self._transport.fetch(url)
        data = self._source.parse(text, word)
        data["取得日時"] = _now_iso()
        return data
