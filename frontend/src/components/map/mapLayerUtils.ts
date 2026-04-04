import type { NewsMapItem } from "@/components/map/MapView";

export type MapLayerMode = "markers" | "heatmap" | "combined";

export type DeckNewsPoint = {
  id: string;
  position: [number, number];
  radius: number;
  color: [number, number, number, number];
  title: string;
  publishedLabel: string;
  category: string;
  sourceItem: NewsMapItem;
};

export const CATEGORY_COLORS: Record<string, [number, number, number, number]> = {
  trafik_kazasi: [249, 115, 22, 220],
  yangin: [220, 38, 38, 220],
  elektrik_kesintisi: [202, 138, 4, 220],
  hirsizlik: [124, 58, 237, 220],
  kulturel_etkinlik: [2, 132, 199, 220],
  unknown: [15, 23, 42, 220],
};

export const CATEGORY_LEGEND = [
  { key: "trafik_kazasi", label: "Trafik Kazasi" },
  { key: "yangin", label: "Yangin" },
  { key: "elektrik_kesintisi", label: "Elektrik Kesintisi" },
  { key: "hirsizlik", label: "Hirsizlik" },
  { key: "kulturel_etkinlik", label: "Kulturel Etkinlik" },
] as const;

const DEFAULT_COLOR: [number, number, number, number] = CATEGORY_COLORS.unknown;
const MIN_MARKER_RADIUS = 8;
const MAX_MARKER_RADIUS = 18;
const KOCAELI_BENCHMARK_CENTER: [number, number] = [29.9213, 40.7654];

function normalizeConfidence(confidence?: number | null) {
  if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
    return 0.5;
  }

  if (confidence > 1) {
    return Math.max(0, Math.min(1, confidence / 100));
  }

  return Math.max(0, Math.min(1, confidence));
}

export function getCategoryColor(category?: string | null) {
  if (!category) {
    return DEFAULT_COLOR;
  }

  return CATEGORY_COLORS[category] ?? DEFAULT_COLOR;
}

export function formatPublishedAt(value?: string | null) {
  if (!value) {
    return "Tarih yok";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function adaptNewsItemsToDeckPoints(items: NewsMapItem[]): DeckNewsPoint[] {
  return items.map((item) => {
    const confidence = normalizeConfidence(item.category_confidence);
    const radius = MIN_MARKER_RADIUS + confidence * (MAX_MARKER_RADIUS - MIN_MARKER_RADIUS);

    return {
      id: item.id,
      position: [item.longitude, item.latitude],
      radius,
      color: getCategoryColor(item.category),
      title: item.title,
      publishedLabel: formatPublishedAt(item.published_at_raw),
      category: item.category ?? "unknown",
      sourceItem: item,
    };
  });
}

export function buildBenchmarkPoints(
  points: DeckNewsPoint[],
  minimumCount = 1000,
): DeckNewsPoint[] {
  if (points.length >= minimumCount) {
    return points;
  }

  if (points.length === 0) {
    return Array.from({ length: minimumCount }, (_, index) => {
      const category = CATEGORY_LEGEND[index % CATEGORY_LEGEND.length]?.key ?? "unknown";
      const ring = Math.floor(index / 36) + 1;
      const step = index % 36;
      const angle = (step / 36) * Math.PI * 2;
      const longitudeOffset = Math.cos(angle) * ring * 0.0015;
      const latitudeOffset = Math.sin(angle) * ring * 0.0011;

      const sourceItem: NewsMapItem = {
        id: `benchmark-${index}`,
        title: `Benchmark nokta ${index + 1}`,
        source_name: "Benchmark",
        source_domain: "local",
        url: "#",
        published_at_raw: "2026-04-01T12:00:00Z",
        category,
        category_confidence: 0.7,
        district: "izmit",
        geocode_status: "resolved",
        latitude: KOCAELI_BENCHMARK_CENTER[1] + latitudeOffset,
        longitude: KOCAELI_BENCHMARK_CENTER[0] + longitudeOffset,
      };

      return {
        id: sourceItem.id,
        position: [sourceItem.longitude, sourceItem.latitude],
        radius: 14,
        color: getCategoryColor(category),
        title: sourceItem.title,
        publishedLabel: formatPublishedAt(sourceItem.published_at_raw),
        category,
        sourceItem,
      };
    });
  }

  const benchmarkPoints = points.slice();
  let index = 0;

  while (benchmarkPoints.length < minimumCount) {
    const basePoint = points[index % points.length]!;
    const wave = (benchmarkPoints.length % 9) - 4;
    const ring = Math.floor(benchmarkPoints.length / points.length) + 1;
    const longitudeOffset = wave * 0.00022 + ring * 0.00003;
    const latitudeOffset = ((index % 7) - 3) * 0.00018 - ring * 0.00002;

    benchmarkPoints.push({
      ...basePoint,
      id: `${basePoint.id}-bench-${benchmarkPoints.length}`,
      position: [
        basePoint.position[0] + longitudeOffset,
        basePoint.position[1] + latitudeOffset,
      ],
    });

    index += 1;
  }

  return benchmarkPoints;
}
