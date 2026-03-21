from __future__ import annotations

import time
from typing import Optional

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


class StaticHttpClient:
    def __init__(
        self,
        timeout: int = 20,
        delay_seconds: float = 1.0,
        headers: Optional[dict] = None,
    ) -> None:
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)

    def get(self, url: str) -> requests.Response:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        time.sleep(self.delay_seconds)
        return response

    def get_text(self, url: str) -> str:
        response = self.get(url)
        return response.text

    def close(self) -> None:
        self.session.close()