import asyncio

from backend.app.scrapers.base.playwright_client import PlaywrightClient
from backend.app.scrapers.bizim_yaka.listing import BizimYakaListingScraper
from backend.app.scrapers.bizim_yaka.detail import BizimYakaDetailScraper


LISTING_URL = "https://www.bizimyaka.com/"


async def main():
    client = PlaywrightClient(headless=True, timeout_ms=30000)
    await client.start()

    try:
        listing_scraper = BizimYakaListingScraper(
            client=client,
            listing_url=LISTING_URL,
        )

        links = await listing_scraper.fetch_links()
        print(f"Found {len(links)} links")

        for link in links[:10]:
            print(link)

        if links:
            detail_scraper = BizimYakaDetailScraper(client=client)

            for link in links[:3]:
                detail = await detail_scraper.fetch_detail(link)
                print("=" * 80)
                print(detail["url"])
                print(detail["title"])
                print(detail["published_at_raw"])
                print(detail["image_url"])
                print(detail["content"][:300])

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())