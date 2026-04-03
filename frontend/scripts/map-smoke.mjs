import { writeFile } from "node:fs/promises";

import { chromium } from "playwright-core";

import {
  resolveChromePath,
  resolveOutputPath,
  withQaServer,
} from "./pwa-shared.mjs";

const chromePath = await resolveChromePath();
const WAIT_TIMEOUT_MS = 60000;
const CATEGORY_IDS = [
  "breaking",
  "traffic",
  "crime",
  "weather",
  "event",
  "economy",
  "sports",
  "health",
];

function parseVisibleCount(text) {
  const match = text.match(/(\d+)\s*\/\s*(\d+)\s*haber/i);
  if (!match) {
    throw new Error(`Visible count text could not be parsed: ${text}`);
  }

  return {
    visible: Number(match[1]),
    total: Number(match[2]),
  };
}

function parseChipCount(text) {
  const match = text.match(/(\d+)\s*$/);
  return match ? Number(match[1]) : 0;
}

async function waitForVisibleCount(page) {
  await page.waitForFunction(
    () => {
      const node = document.querySelector('[data-testid="visible-news-count"]');
      return Boolean(node?.textContent?.match(/\d+\s*\/\s*\d+\s*haber/i));
    },
    null,
    { timeout: WAIT_TIMEOUT_MS },
  );

  const text = (await page.getByTestId("visible-news-count").textContent()) || "";
  return {
    text,
    ...parseVisibleCount(text),
  };
}

async function pickCategoryToFilter(page, baselineVisible) {
  for (const categoryId of CATEGORY_IDS) {
    const locator = page.getByTestId(`category-chip-${categoryId}`);
    const chipText = ((await locator.textContent()) || "").trim();
    const count = parseChipCount(chipText);
    if (count > 0 && count < baselineVisible) {
      return { categoryId, count, chipText };
    }
  }

  for (const categoryId of CATEGORY_IDS) {
    const locator = page.getByTestId(`category-chip-${categoryId}`);
    const chipText = ((await locator.textContent()) || "").trim();
    const count = parseChipCount(chipText);
    if (count > 0) {
      return { categoryId, count, chipText };
    }
  }

  throw new Error("No category chip with live data could be found.");
}

await withQaServer(async (baseUrl) => {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
  });
  const page = await context.newPage();
  const seenRequests = [];
  const consoleMessages = [];
  const pageErrors = [];

  page.on("request", (request) => {
    seenRequests.push(request.url());
  });
  page.on("console", (message) => {
    consoleMessages.push(`${message.type()}: ${message.text()}`);
  });
  page.on("pageerror", (error) => {
    pageErrors.push(error.message);
  });

  try {
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(
      () => Boolean(document.querySelector(".maplibregl-canvas")),
      null,
      { timeout: WAIT_TIMEOUT_MS },
    );

    await page.getByTestId("live-news-item-0").waitFor({ timeout: WAIT_TIMEOUT_MS });
    const firstFeedTitle = ((await page.getByTestId("live-news-item-title-0").textContent()) || "").trim();
    if (!firstFeedTitle) {
      throw new Error("Live news feed did not expose a clickable first item.");
    }

    await page.getByTestId("live-news-item-0").click();
    await page.getByTestId("control-panel-toggle").click();
    await page.getByTestId("news-info-card").waitFor({ timeout: WAIT_TIMEOUT_MS });
    await page.waitForFunction(
      (expected) => {
        const node = document.querySelector('[data-testid="news-info-title"]');
        return (node?.textContent || "").trim() === expected;
      },
      firstFeedTitle,
      { timeout: WAIT_TIMEOUT_MS },
    );
    const selectedTitle = ((await page.getByTestId("news-info-title").textContent()) || "").trim();
    const infoStatus = ((await page.getByTestId("news-info-status").textContent()) || "").trim();

    const initialCount = await waitForVisibleCount(page);
    if (initialCount.visible < 1 || initialCount.total < 1) {
      throw new Error(`Live dataset is empty: ${initialCount.text}`);
    }

    const selectedCategory = await pickCategoryToFilter(page, initialCount.visible);
    await page.getByTestId(`category-chip-${selectedCategory.categoryId}`).click();
    await page.waitForFunction(
      (expectedVisible) => {
        const node = document.querySelector('[data-testid="visible-news-count"]');
        const text = node?.textContent || "";
        const match = text.match(/(\d+)\s*\/\s*(\d+)\s*haber/i);
        return Boolean(match) && Number(match[1]) === expectedVisible;
      },
      selectedCategory.count,
      { timeout: WAIT_TIMEOUT_MS },
    );

    const filteredCount = await waitForVisibleCount(page);

    const summary = {
      passed:
        seenRequests.some((url) => url.includes("/api/v1/news/map")) &&
        seenRequests.some((url) => url.includes("/api/v1/news/stats")) &&
        selectedTitle.length > 0 &&
        filteredCount.visible === selectedCategory.count &&
        filteredCount.total >= filteredCount.visible &&
        infoStatus.length > 0,
      baseUrl,
      selectedTitle,
      infoStatus,
      initialCount,
      filteredCount,
      selectedCategory,
      seenRequests,
    };

    await writeFile(
      resolveOutputPath("map-smoke-summary.json"),
      JSON.stringify(summary, null, 2),
      "utf-8",
    );

    console.log(JSON.stringify(summary, null, 2));

    if (!summary.passed) {
      process.exitCode = 1;
    }
  } catch (error) {
    const failureSummary = {
      passed: false,
      baseUrl,
      error: error instanceof Error ? error.message : String(error),
      seenRequests,
      consoleMessages,
      pageErrors,
      bodyText: await page.locator("body").textContent().catch(() => ""),
    };

    await page.screenshot({
      path: resolveOutputPath("map-smoke-failure.png"),
      fullPage: true,
    }).catch(() => undefined);
    await writeFile(
      resolveOutputPath("map-smoke-summary.json"),
      JSON.stringify(failureSummary, null, 2),
      "utf-8",
    );
    console.log(JSON.stringify(failureSummary, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
});
