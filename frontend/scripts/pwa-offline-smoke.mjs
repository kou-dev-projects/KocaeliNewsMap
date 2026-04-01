import { chromium } from "playwright-core";

import { writeFile } from "node:fs/promises";

import {
  resolveChromePath,
  resolveOutputPath,
  withQaServer,
} from "./pwa-shared.mjs";

const chromePath = await resolveChromePath();
const WAIT_TIMEOUT_MS = 45000;
const POLL_INTERVAL_MS = 1000;

await withQaServer(async (baseUrl) => {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
  });

  const context = await browser.newContext({
    serviceWorkers: "allow",
  });
  const page = await context.newPage();

  async function waitForMapCanvas() {
    await page.waitForSelector("text=Map View", { timeout: WAIT_TIMEOUT_MS });
    await page.waitForFunction(
      () => Boolean(document.querySelector(".maplibregl-canvas")),
      null,
      { timeout: WAIT_TIMEOUT_MS },
    );
  }

  async function readCachedTileCount() {
    return page.evaluate(async () => {
      const cache = await caches.open("pulse-map-tiles-v1");
      const keys = await cache.keys();
      return keys.length;
    });
  }

  async function waitForCachedTiles() {
    const deadline = Date.now() + WAIT_TIMEOUT_MS;

    while (Date.now() < deadline) {
      const count = await readCachedTileCount();
      if (count > 0) {
        return count;
      }
      await page.waitForTimeout(POLL_INTERVAL_MS);
    }

    return 0;
  }

  try {
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await waitForMapCanvas();
    await page.evaluate(() => navigator.serviceWorker.ready);
    const cachedTileCount = await waitForCachedTiles();

    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded" });
    await waitForMapCanvas();

    const offlineState = await page.evaluate(async () => {
      const cache = await caches.open("pulse-map-tiles-v1");
      const keys = await cache.keys();
      return {
        title: document.title,
        mapCanvasVisible: Boolean(document.querySelector(".maplibregl-canvas")),
        cachedTileCount: keys.length,
        online: navigator.onLine,
      };
    });

    console.log(
      JSON.stringify(
        {
          baseUrl,
          cachedTileCount,
          offlineState,
        },
        null,
        2,
      ),
    );

    await writeFile(
      resolveOutputPath("pwa-offline-summary.json"),
      JSON.stringify(
        {
          passed: offlineState.mapCanvasVisible && offlineState.cachedTileCount > 0,
          baseUrl,
          cachedTileCount,
          offlineState,
        },
        null,
        2,
      ),
      "utf-8",
    );

    if (!offlineState.mapCanvasVisible || offlineState.cachedTileCount < 1) {
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
});
