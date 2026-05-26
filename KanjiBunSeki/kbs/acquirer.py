from datetime import datetime, timezone

from .source.kanji.base import KanjiSource
from .transport.base import Transport


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class KanjiAcquirer:
    def __init__(self, source: KanjiSource, transport: Transport):
        self._source = source
        self._transport = transport

    def acquire(self, identifier: str) -> tuple[str, dict]:
        url = self._source.url_for(identifier)
        text = self._transport.fetch(url)
        result = self._source.parse(text)
        data = result["data"]
        data["取得日時"] = _now_iso()
        return result["kanji"], data

    def acquire_all(self) -> dict[str, dict]:
        text = self._transport.fetch(self._source.bulk_url())
        entries = self._source.parse_all(text)
        ts = _now_iso()
        for data in entries.values():
            data["取得日時"] = ts
        return entries
