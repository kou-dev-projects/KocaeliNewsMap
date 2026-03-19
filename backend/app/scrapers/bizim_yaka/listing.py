from backend.app.scrapers.base.playwright_client import PlaywrightClient

from .parser import parse_listing_links


class BizimYakaListingScraper:
    def __init__(self, client: PlaywrightClient, listing_url: str):
        self.client = client
        self.listing_url = listing_url

    async def fetch_links(self) -> list[str]:
        html = await self.client.get_html(url=self.listing_url)
        return parse_listing_links(html=html, base_url=self.listing_url)