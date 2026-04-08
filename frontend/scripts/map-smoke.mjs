import { writeFile } from "node:fs/promises";

import { chromium } from "playwright-core";

import {
  resolveChromePath,
  resolveOutputPath,
  withQaServer,
} from "./pwa-shared.mjs";

const chromePath = await resolveChromePath();
const WAIT_TIMEOUT_MS = 45000;
const EVENT_TITLE = "Sinema salonlarinda 6 yeni film";
const MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const BUILDING_SOURCE_URL = "https://tiles.openfreemap.org/planet";
const SMOKE_TILE_URL = "https://smoke.invalid/buildings/{z}/{x}/{y}.pbf";
const MAP_RESPONSE = {
  total: 2,
  items: [
    {
      id: "news-centered-event",
      title: EVENT_TITLE,
      summary: "Bu hafta sinema salonlarinda 6 yeni film vizyona giriyor.",
      source_name: "Bizim Yaka Kocaeli",
      source_domain: "bizimyaka.com.tr",
      url: "https://example.com/sinema",
      published_at_raw: "2026-04-02T20:00:00+03:00",
      category: "kulturel_etkinlik",
      category_confidence: 0.96,
      district: "izmit",
      geocode_status: "resolved",
      latitude: 40.7654,
      longitude: 29.9213,
    },
    {
      id: "news-traffic-2",
      title: "TEM otoyolunda trafik kazasi",
      summary: "Gebze gecisinde zincirleme trafik kazasi meydana geldi.",
      source_name: "Ozgur Kocaeli",
      source_domain: "ozgurkocaeli.com.tr",
      url: "https://example.com/trafik",
      published_at_raw: "2026-04-02T19:30:00+03:00",
      category: "trafik_kazasi",
      category_confidence: 0.88,
      district: "gebze",
      geocode_status: "approximate",
      latitude: 40.8004,
      longitude: 29.4307,
    },
  ],
};

const DETAIL_RESPONSE = {
  ...MAP_RESPONSE.items[0],
  content_text:
    "Kocaeli genelinde bu hafta vizyona giren yeni filmler kultur sanat takvimini hareketlendirdi. Izmit merkezli programda salonlar hafta sonuna kadar dolu seyirci bekliyor.",
  location_text_extracted: "Izmit merkez",
  source_base_url: "https://bizimyaka.com.tr",
  source_domains: ["bizimyaka.com.tr", "ozgurkocaeli.com.tr", "kocaeligazetesi.com.tr"],
  source_sites: [
    { domain: "bizimyaka.com.tr", url: "https://bizimyaka.com.tr", is_primary: true },
    { domain: "ozgurkocaeli.com.tr", url: "https://ozgurkocaeli.com.tr", is_primary: false },
    { domain: "kocaeligazetesi.com.tr", url: "https://kocaeligazetesi.com.tr", is_primary: false },
  ],
};

const STATS_RESPONSE = {
  total: 2,
  geocoded_total: 2,
  last_3d_total: 2,
  active_sources: 2,
  categories: [
    { key: "kulturel_etkinlik", count: 1 },
    { key: "trafik_kazasi", count: 1 },
  ],
  districts: [
    { key: "izmit", count: 1 },
    { key: "gebze", count: 1 },
  ],
};

const MAP_STYLE_RESPONSE = {
  version: 8,
  name: "pulse-smoke-style",
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: {
        "background-color": "#dbeafe",
      },
    },
  ],
};

const BUILDING_SOURCE_RESPONSE = {
  tilejson: "3.0.0",
  name: "pulse-smoke-buildings",
  minzoom: 15,
  maxzoom: 15,
  scheme: "xyz",
  tiles: [SMOKE_TILE_URL],
  vector_layers: [
    {
      id: "building",
    },
  ],
};

function jsonResponse(body) {
  return {
    status: 200,
    contentType: "application/json",
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "access-control-allow-headers": "*",
    },
    body: JSON.stringify(body),
  };
}

async function waitForTextFragment(page, testId, fragment) {
  await page.waitForFunction(
    ([targetTestId, expected]) => {
      const node = document.querySelector(`[data-testid="${targetTestId}"]`);
      return node?.textContent?.includes(expected) ?? false;
    },
    [testId, fragment],
    { timeout: WAIT_TIMEOUT_MS },
  );
}

async function clickCenteredMarker(page) {
  const mapBox = await page.getByTestId("news-map").boundingBox();
  if (!mapBox) {
    throw new Error("Map bounding box could not be resolved.");
  }

  const clickX = mapBox.x + mapBox.width / 2;
  const clickY = mapBox.y + mapBox.height / 2;

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await page.mouse.click(clickX, clickY);
    try {
      await waitForTextFragment(page, "news-info-title", EVENT_TITLE);
      return;
    } catch {
      await page.waitForTimeout(400);
    }
  }

  throw new Error("Centered marker could not be selected.");
}

await withQaServer(async (baseUrl) => {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
  });

  const context = await browser.newContext();
  const seenRequests = [];
  const consoleMessages = [];
  const pageErrors = [];

  await context.route("**/api/v1/news/stats*", async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(jsonResponse(STATS_RESPONSE));
  });
  await context.route(`${MAP_STYLE_URL}*`, async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(jsonResponse(MAP_STYLE_RESPONSE));
  });
  await context.route(`${BUILDING_SOURCE_URL}*`, async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(jsonResponse(BUILDING_SOURCE_RESPONSE));
  });
  await context.route(`${SMOKE_TILE_URL.replace("{z}/{x}/{y}", "**")}`, async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill({
      status: 404,
      body: "",
    });
  });
  await context.route("**/api/v1/news/map*", async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(jsonResponse(MAP_RESPONSE));
  });
  await context.route(/\/api\/v1\/news\/(?!map(?:\?|$)|stats(?:\?|$)|dashboard(?:\?|$))[^/?]+(?:\?.*)?$/i, async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(jsonResponse(DETAIL_RESPONSE));
  });
  await context.route("**/api/scrape/bootstrap", async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(
      jsonResponse({
        status: "already_initialized",
        reason: "smoke_test",
      }),
    );
  });
  await context.route("**/api/scrape/refresh", async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(
      jsonResponse({
        job_id: "refresh-smoke",
        status: "pending",
        status_url: "/api/scrape/job-status?job_id=refresh-smoke",
      }),
    );
  });
  await context.route("**/api/scrape/job-status*", async (route) => {
    seenRequests.push(route.request().url());
    await route.fulfill(
      jsonResponse({
        job_id: "refresh-smoke",
        status: "completed",
        source: null,
        trigger_type: "manual",
        created_at: Date.now(),
        attempt_count: 1,
      }),
    );
  });

  const page = await context.newPage();
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
    await page.getByTestId("control-panel-toggle").click();
    await waitForTextFragment(page, "visible-news-count", "2 / 2 haber gosteriliyor");
    await page.waitForTimeout(1200);

    await clickCenteredMarker(page);
    await page.getByTestId("news-info-card").waitFor({ timeout: WAIT_TIMEOUT_MS });
    const infoStatus = (await page.getByTestId("news-info-status").textContent()) || "";

    await page.getByTestId("category-chip-event").click();
    await waitForTextFragment(page, "visible-news-count", "1 / 2 haber gosteriliyor");
    const visibleCountText =
      (await page.getByTestId("visible-news-count").textContent()) || "";

    const summary = {
      passed:
        seenRequests.some((url) => url.includes("/api/v1/news/map")) &&
        seenRequests.some((url) => url.includes("/api/v1/news/stats")) &&
        infoStatus.includes("Dogrulanmis konum") &&
        visibleCountText.includes("1 / 2 haber gosteriliyor"),
      baseUrl,
      selectedTitle: (await page.getByTestId("news-info-title").textContent()) || "",
      infoStatus,
      visibleCountText,
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
