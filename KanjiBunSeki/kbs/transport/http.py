import requests

from .base import Transport


class HttpTransport(Transport):
    USER_AGENT = "Mozilla/5.0"

    def fetch(self, url: str) -> str:
        resp = requests.get(url, headers={"User-Agent": self.USER_AGENT}, timeout=30)
        resp.raise_for_status()
        return resp.text
