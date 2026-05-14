from datetime import datetime, timezone

from .source.kanji.base import KanjiSource
from .transport.base import Transport


class KanjiAcquirer:
    def __init__(self, source: KanjiSource, transport: Transport):
        self._source = source
        self._transport = transport

    def acquire(self, identifier: str) -> tuple[str, dict]:
        url = self._source.url_for(identifier)
        text = self._transport.fetch(url)
        result = self._source.parse(text)
        data = result["data"]
        data["取得日時"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        return result["kanji"], data
