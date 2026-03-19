import asyncio

from backend.app.scrapers.base.playwright_client import PlaywrightClient
from backend.app.scrapers.ses_kocaeli.listing import SesKocaeliListingScraper
from backend.app.scrapers.ses_kocaeli.detail import SesKocaeliDetailScraper


LISTING_URL = "https://www.seskocaeli.com/"


async def main():
    client = PlaywrightClient(headless=True, timeout_ms=30000)
    await client.start()

    try:
        listing_scraper = SesKocaeliListingScraper(
            client=client,
            listing_url=LISTING_URL,
        )

        links = await listing_scraper.fetch_links()
        print(f"Found {len(links)} links")

        for link in links[:5]:
            print(link)

        if links:
            detail_scraper = SesKocaeliDetailScraper(client=client)
            detail = await detail_scraper.fetch_detail(links[0])
            print(detail)

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())