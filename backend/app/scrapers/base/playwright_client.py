from contextlib import asynccontextmanager
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)


class PlaywrightClient:
    def __init__(
        self,
        headless: bool = False,
        timeout_ms: int = 30_000,
        wait_until: str = "domcontentloaded",
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless
        )

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    @asynccontextmanager
    async def page(self):
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")

        context: BrowserContext = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            )
        )

        page: Page = await context.new_page()
        page.set_default_timeout(self.timeout_ms)

        try:
            yield page
        finally:
            await context.close()

    async def get_html(
        self,
        url: str,
        wait_for: str | None = None,
        wait_until: str | None = None,
    ) -> str:
        async with self.page() as page:
            await page.goto(
                url,
                wait_until=wait_until or self.wait_until,
            )

            if wait_for:
                await page.wait_for_selector(wait_for, state="attached")

            return await page.content()