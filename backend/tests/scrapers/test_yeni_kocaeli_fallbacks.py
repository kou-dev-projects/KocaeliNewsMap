from app.scrapers.yeni_kocaeli.detail import YeniKocaeliDetailScraper
from app.scrapers.yeni_kocaeli.listing import YeniKocaeliListingScraper


class BlockedStaticClient:
    def get_text(self, url: str) -> str:
        return "<html><body>Just a moment...</body></html>"

    def close(self) -> None:
        return None


class FailIfCalledCrawlApi:
    enabled = True

    def fetch_html(self, url: str) -> str:
        raise AssertionError("crawl_api_should_not_be_called")


class FakePlaywrightClient:
    def __init__(self, html: str, **kwargs):
        self._html = html
        self.stop_called = False

    async def get_html(self, **kwargs) -> str:
        return self._html

    async def stop(self) -> None:
        self.stop_called = True


def test_yeni_kocaeli_listing_uses_playwright_before_crawl_api():
    scraper = YeniKocaeliListingScraper(client=BlockedStaticClient())
    scraper.crawl_api = FailIfCalledCrawlApi()
    created_clients: list[FakePlaywrightClient] = []

    def fake_factory(**kwargs):
        client = FakePlaywrightClient(
            "<html><body><main><a href='/haber/test/1.html'>ok</a></main></body></html>",
            **kwargs,
        )
        created_clients.append(client)
        return client

    scraper.playwright_client_factory = fake_factory

    html = scraper.fetch_listing_html("https://www.yenikocaeli.com")

    assert "/haber/test/1.html" in html
    assert created_clients[0].stop_called is True


def test_yeni_kocaeli_detail_uses_playwright_before_crawl_api():
    scraper = YeniKocaeliDetailScraper(client=BlockedStaticClient())
    scraper.crawl_api = FailIfCalledCrawlApi()
    created_clients: list[FakePlaywrightClient] = []

    def fake_factory(**kwargs):
        client = FakePlaywrightClient(
            "<html><body><h1>Baslik</h1><div class='news'><p>Icerik</p></div></body></html>",
            **kwargs,
        )
        created_clients.append(client)
        return client

    scraper.playwright_client_factory = fake_factory

    html = scraper.fetch_detail_html("https://www.yenikocaeli.com/haber/test/1.html")

    assert "<h1>Baslik</h1>" in html
    assert created_clients[0].stop_called is True
