from __future__ import annotations

import time
from typing import Iterable
from urllib.parse import urlparse

import requests

from app.scrapers.base.block_detection import looks_like_blocked
from app.settings import settings


_SUPPORTED_PROVIDERS = {"scrapingbee", "cloudflare"}
_DOMAIN_POLICIES = {
    # Cloudflare content rendering is consistently slow/unreliable for this source.
    "yenikocaeli.com": {
        "providers": ("scrapingbee",),
        "timeout": 15,
        "retry_attempts": 1,
    },
}


def _normalize_provider_name(value: str) -> str:
    return value.strip().lower()


def _looks_like_block_page(html: str) -> bool:
    if looks_like_blocked(html):
        return True

    lowered = html.lower()

    # Cloudflare blocked response frequently appears as a minimal <pre> page.
    if (
        "your request was blocked" in lowered
        and "<pre" in lowered
        and "white-space: pre-wrap" in lowered
    ):
        return True

    return False


class CrawlApiClient:
    def __init__(self) -> None:
        self.provider = _normalize_provider_name(settings.crawl_api_provider)
        self.provider_order = self._build_provider_order(
            primary_provider=self.provider,
            fallback_order=self._parse_fallback_order(settings.crawl_api_fallback_order),
        )
        self.timeout = settings.crawl_api_timeout
        self.retry_attempts = max(settings.crawl_api_retry_attempts, 1)
        self.retry_backoff_seconds = max(settings.crawl_api_retry_backoff_seconds, 0.0)
        self.rate_limit_backoff_seconds = max(settings.crawl_api_rate_limit_backoff_seconds, 0.0)

    @property
    def enabled(self) -> bool:
        return bool(self._configured_provider_order())

    def fetch_html(self, url: str) -> str:
        configured_order, request_timeout, retry_attempts = self._resolve_request_policy(url)
        if not configured_order:
            raise RuntimeError("crawl_api_provider_not_configured")

        errors: list[str] = []
        for provider in configured_order:
            for attempt in range(1, retry_attempts + 1):
                try:
                    html = self._fetch_with_provider(provider, url, timeout=request_timeout)
                    if not html.strip():
                        raise RuntimeError(f"{provider}_empty_html")
                    if _looks_like_block_page(html):
                        raise RuntimeError(f"{provider}_blocked_html")
                    return html
                except Exception as exc:
                    errors.append(
                        f"{provider}[{attempt}/{retry_attempts}]={type(exc).__name__}:{exc}"
                    )
                    if not self._should_retry_exception(exc):
                        break
                    if (
                        attempt < retry_attempts
                        and self.retry_backoff_seconds > 0
                    ):
                        sleep_seconds = self.retry_backoff_seconds * attempt
                        lowered_error = str(exc).lower()
                        if "429" in lowered_error or "rate limit" in lowered_error:
                            sleep_seconds = max(sleep_seconds, self.rate_limit_backoff_seconds)
                        time.sleep(sleep_seconds)

        raise RuntimeError("crawl_api_all_providers_failed: " + " | ".join(errors))

    def _fetch_with_provider(self, provider: str, url: str, *, timeout: int | None = None) -> str:
        if provider == "scrapingbee":
            return self._fetch_with_scrapingbee(url, timeout=timeout)
        if provider == "cloudflare":
            return self._fetch_with_cloudflare_content(url, timeout=timeout)
        raise RuntimeError(f"unsupported_crawl_api_provider:{provider}")

    @staticmethod
    def _parse_fallback_order(value: str) -> list[str]:
        if not value:
            return []
        seen: set[str] = set()
        providers: list[str] = []
        for raw in value.split(","):
            provider = _normalize_provider_name(raw)
            if provider and provider not in seen:
                seen.add(provider)
                providers.append(provider)
        return providers

    @staticmethod
    def _build_provider_order(*, primary_provider: str, fallback_order: Iterable[str]) -> list[str]:
        ordered: list[str] = []
        for provider in [primary_provider, *fallback_order]:
            if provider in _SUPPORTED_PROVIDERS and provider not in ordered:
                ordered.append(provider)
        return ordered

    def _configured_provider_order(self) -> list[str]:
        providers: list[str] = []
        for provider in self.provider_order:
            if provider == "scrapingbee" and settings.scrapingbee_api_key:
                providers.append(provider)
            elif (
                provider == "cloudflare"
                and settings.cloudflare_account_id
                and settings.cloudflare_api_token
            ):
                providers.append(provider)
        return providers

    def _resolve_request_policy(self, url: str) -> tuple[list[str], int, int]:
        configured_order = self._configured_provider_order()
        policy = self._domain_policy(url)
        if policy is None:
            return configured_order, self.timeout, self.retry_attempts

        allowed_order = [
            provider
            for provider in policy.get("providers", ())
            if provider in configured_order
        ]
        provider_order = allowed_order or configured_order
        timeout = int(policy.get("timeout", self.timeout))
        retry_attempts = max(int(policy.get("retry_attempts", self.retry_attempts)), 1)
        return provider_order, timeout, retry_attempts

    @staticmethod
    def _domain_policy(url: str) -> dict[str, object] | None:
        hostname = (urlparse(url).hostname or "").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return _DOMAIN_POLICIES.get(hostname)

    @staticmethod
    def _should_retry_exception(exc: Exception) -> bool:
        if isinstance(exc, requests.Timeout):
            return False

        lowered = str(exc).lower()
        if "timed out" in lowered:
            return False
        if "blocked_html" in lowered or "empty_html" in lowered:
            return False
        if "http_4" in lowered and "429" not in lowered:
            return False

        return True

    def _fetch_with_scrapingbee(self, url: str, *, timeout: int | None = None) -> str:
        api_key = settings.scrapingbee_api_key
        if not api_key:
            raise RuntimeError("scrapingbee_api_key_missing")

        response = requests.get(
            "https://app.scrapingbee.com/api/v1/",
            params={
                "api_key": api_key,
                "url": url,
                "render_js": "true",
                "premium_proxy": "true",
                "country_code": "tr",
            },
            timeout=timeout or self.timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"scrapingbee_http_{response.status_code}")

        return response.text

    def _fetch_with_cloudflare_content(self, url: str, *, timeout: int | None = None) -> str:
        account_id = settings.cloudflare_account_id
        api_token = settings.cloudflare_api_token
        if not account_id:
            raise RuntimeError("cloudflare_account_id_missing")
        if not api_token:
            raise RuntimeError("cloudflare_api_token_missing")

        endpoint_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/"
            "browser-rendering/content"
        )
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            endpoint_url,
            headers=headers,
            json={"url": url},
            timeout=timeout or self.timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"cloudflare_content_http_{response.status_code}")

        payload = response.json()
        if not payload.get("success", False):
            errors = payload.get("errors") or []
            if errors:
                first = errors[0]
                code = first.get("code")
                message = first.get("message")
                raise RuntimeError(f"cloudflare_content_failed_{code}:{message}")
            raise RuntimeError("cloudflare_content_failed")

        result = payload.get("result")
        if not isinstance(result, str) or "<" not in result:
            raise RuntimeError("cloudflare_content_no_html")

        return result
