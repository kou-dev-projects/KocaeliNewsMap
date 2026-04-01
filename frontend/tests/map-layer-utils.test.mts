import test from "node:test";
import assert from "node:assert/strict";

import {
  adaptNewsItemsToDeckPoints,
  buildBenchmarkPoints,
  CATEGORY_COLORS,
  getCategoryColor,
} from "../src/components/map/mapLayerUtils.ts";
import type { NewsMapItem } from "../src/components/map/MapView.tsx";

function createItem(overrides: Partial<NewsMapItem> = {}): NewsMapItem {
  return {
    id: "news-1",
    title: "Test haber",
    source_name: "Kaynak",
    source_domain: "example.com",
    url: "https://example.com/news-1",
    published_at_raw: "2026-04-01T10:00:00Z",
    category: "yangin",
    category_confidence: 0.75,
    district: "izmit",
    geocode_status: "resolved",
    latitude: 40.7654,
    longitude: 29.9213,
    ...overrides,
  };
}

test("category colors return the configured mapping", () => {
  assert.deepEqual(getCategoryColor("yangin"), CATEGORY_COLORS.yangin);
  assert.deepEqual(getCategoryColor("unknown-category"), CATEGORY_COLORS.unknown);
  assert.deepEqual(getCategoryColor(null), CATEGORY_COLORS.unknown);
});

test("news items adapt to deck points with confidence-scaled radius", () => {
  const points = adaptNewsItemsToDeckPoints([
    createItem({ category_confidence: 0 }),
    createItem({ id: "news-2", category_confidence: 1 }),
  ]);

  assert.equal(points.length, 2);
  assert.equal(points[0]?.radius, 6);
  assert.equal(points[1]?.radius, 20);
  assert.deepEqual(points[1]?.position, [29.9213, 40.7654]);
});

test("benchmark builder expands small datasets to 1000 points", () => {
  const points = adaptNewsItemsToDeckPoints([createItem()]);
  const benchmarkPoints = buildBenchmarkPoints(points);

  assert.equal(benchmarkPoints.length, 1000);
  assert.notEqual(benchmarkPoints[1]?.id, benchmarkPoints[0]?.id);
  assert.notDeepEqual(
    benchmarkPoints[1]?.position,
    benchmarkPoints[0]?.position,
  );
});

test("benchmark builder generates a synthetic dataset when live data is empty", () => {
  const benchmarkPoints = buildBenchmarkPoints([]);

  assert.equal(benchmarkPoints.length, 1000);
  assert.equal(benchmarkPoints[0]?.sourceItem.source_name, "Benchmark");
  assert.equal(benchmarkPoints[0]?.title, "Benchmark nokta 1");
  assert.notDeepEqual(
    benchmarkPoints[0]?.position,
    benchmarkPoints[1]?.position,
  );
});

test("benchmark builder keeps large datasets untouched", () => {
  const points = adaptNewsItemsToDeckPoints(
    Array.from({ length: 1001 }, (_, index) =>
      createItem({
        id: `news-${index}`,
        longitude: 29.9213 + index * 0.00001,
      }),
    ),
  );

  const benchmarkPoints = buildBenchmarkPoints(points);
  assert.equal(benchmarkPoints.length, 1001);
  assert.equal(benchmarkPoints, points);
});
