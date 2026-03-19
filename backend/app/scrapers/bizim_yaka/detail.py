from backend.app.scrapers.base.playwright_client import PlaywrightClient

from .parser import parse_detail
from .selectors import DETAIL_TITLE


class BizimYakaDetailScraper:
    def __init__(self, client: PlaywrightClient):
        self.client = client

    async def fetch_detail(self, url: str) -> dict:
        last_error = None

        for _ in range(2):
            try:
                html = await self.client.get_html(
                    url=url,
                    wait_for=DETAIL_TITLE,
                )
                return parse_detail(html=html, url=url)
            except Exception as exc:
                last_error = exc

        raise last_error