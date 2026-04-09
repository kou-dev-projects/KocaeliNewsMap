import pytest
import requests

from app.scrapers.base.crawl_api_client import CrawlApiClient, _looks_like_block_page
from app.settings import settings


def test_challenge_platform_token_alone_is_not_blocked():
    html = (
        "<html><head><script>const marker='challenge-platform';</script></head><body>"
        + ("x" * 16000)
        + "</body></html>"
    )
    assert _looks_like_block_page(html) is False


def test_short_page_with_challenge_platform_id_is_blocked():
    html = '<html><body><div id="challenge-platform"></div></body></html>'
    assert _looks_like_block_page(html) is True


def test_yenikocaeli_policy_uses_scrapingbee_once(monkeypatch):
    monkeypatch.setattr(settings, "crawl_api_provider", "cloudflare")
    monkeypatch.setattr(settings, "crawl_api_fallback_order", "scrapingbee")
    monkeypatch.setattr(settings, "crawl_api_timeout", 30)
    monkeypatch.setattr(settings, "crawl_api_retry_attempts", 2)
    monkeypatch.setattr(settings, "scrapingbee_api_key", "test-key")
    monkeypatch.setattr(settings, "cloudflare_account_id", "acct")
    monkeypatch.setattr(settings, "cloudflare_api_token", "token")

    client = CrawlApiClient()
    attempts: list[tuple[str, int | None]] = []

    def fake_fetch(provider: str, url: str, *, timeout: int | None = None) -> str:
        attempts.append((provider, timeout))
        raise RuntimeError("provider_boom")

    monkeypatch.setattr(client, "_fetch_with_provider", fake_fetch)

    with pytest.raises(RuntimeError, match="scrapingbee\\[1/1\\]"):
        client.fetch_html("https://www.yenikocaeli.com/")

    assert attempts == [("scrapingbee", 15)]


def test_timeout_error_is_not_retried(monkeypatch):
    monkeypatch.setattr(settings, "crawl_api_provider", "scrapingbee")
    monkeypatch.setattr(settings, "crawl_api_fallback_order", "")
    monkeypatch.setattr(settings, "crawl_api_timeout", 30)
    monkeypatch.setattr(settings, "crawl_api_retry_attempts", 2)
    monkeypatch.setattr(settings, "scrapingbee_api_key", "test-key")

    client = CrawlApiClient()
    attempts: list[tuple[str, int | None]] = []

    def fake_fetch(provider: str, url: str, *, timeout: int | None = None) -> str:
        attempts.append((provider, timeout))
        raise requests.ReadTimeout("provider_timed_out")

    monkeypatch.setattr(client, "_fetch_with_provider", fake_fetch)

    with pytest.raises(RuntimeError, match="scrapingbee\\[1/2\\]=ReadTimeout"):
        client.fetch_html("https://example.com/")

    assert attempts == [("scrapingbee", 30)]
