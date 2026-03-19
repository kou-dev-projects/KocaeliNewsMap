from backend.app.scrapers.base.playwright_client import PlaywrightClient
from backend.app.scrapers.base.robots import RobotsChecker

from .parser import parse_listing_links


class BizimYakaListingScraper:
    def __init__(self, client: PlaywrightClient, listing_url: str):
        self.client = client
        self.listing_url = listing_url
        self.robots = RobotsChecker(strict=False)

    async def fetch_links(self) -> list[str]:
        allowed, reason = self.robots.can_fetch(self.listing_url)

        if not allowed:
            raise PermissionError(reason)

        if "could not be verified" in reason:
            print(f"warning: {reason}")

        html = await self.client.get_html(url=self.listing_url)
        return parse_listing_links(html=html, base_url=self.listing_url)