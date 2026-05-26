import requests

from .base import Transport


class HttpTransport(Transport):
    USER_AGENT = "Mozilla/5.0"

    def fetch(self, url: str) -> str:
        resp = requests.get(url, headers={"User-Agent": self.USER_AGENT}, timeout=30)
        resp.raise_for_status()
        # When the server omits a charset, requests defaults `encoding` to
        # ISO-8859-1, which mangles Shift_JIS / EUC-JP pages. Fall back to
        # chardet's best guess in that case.
        if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding
        return resp.text
