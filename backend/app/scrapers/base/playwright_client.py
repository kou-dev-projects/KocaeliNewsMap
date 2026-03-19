import asyncio
import random
from contextlib import asynccontextmanager
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
]


class PlaywrightClient:
    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30_000,
        wait_until: str = "domcontentloaded",
        min_delay_s: float = 1.0,
        max_delay_s: float = 3.0,
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self.min_delay_s = min_delay_s
        self.max_delay_s = max_delay_s
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

    async def _human_delay(self) -> None:
        await asyncio.sleep(random.uniform(self.min_delay_s, self.max_delay_s))

    @asynccontextmanager
    async def page(self):
        if self._browser is None:
            raise RuntimeError("Browser not started. Call start() first.")

        context: BrowserContext = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS)
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
            await self._human_delay()

            await page.goto(
                url,
                wait_until=wait_until or self.wait_until,
            )

            if wait_for:
                await page.wait_for_selector(wait_for, state="attached")

            await self._human_delay()
            return await page.content()