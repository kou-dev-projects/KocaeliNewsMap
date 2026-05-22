from __future__ import annotations

import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


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
        retry_total: int = 3,
        retry_connect: int = 3,
        retry_read: int = 3,
        retry_status: int = 3,
    ) -> None:
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)
        retry_strategy = Retry(
            total=retry_total,
            connect=retry_connect,
            read=retry_read,
            status=retry_status,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET", "HEAD"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

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
