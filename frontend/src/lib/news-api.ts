import type { FilterState } from "@/components/filters/FilterSidebar";
import type { NewsMapItem } from "@/components/map/MapView";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type NewsStats = {
  total: number;
  geocoded_total: number;
  last_24h_total: number;
  active_sources: number;
  categories: Array<{ key: string; count: number }>;
  districts: Array<{ key: string; count: number }>;
};

export type NewsMapResponse = {
  items: NewsMapItem[];
  total: number;
};

export const EMPTY_STATS: NewsStats = {
  total: 0,
  geocoded_total: 0,
  last_24h_total: 0,
  active_sources: 0,
  categories: [],
  districts: [],
};

export const EMPTY_MAP_RESPONSE: NewsMapResponse = {
  items: [],
  total: 0,
};

export function buildStatsUrl(filters: FilterState) {
  const url = new URL("/api/v1/news/stats", API_BASE_URL);

  if (filters.category) {
    url.searchParams.set("category", filters.category);
  }

  if (filters.district) {
    url.searchParams.set("district", filters.district);
  }

  if (filters.dateFrom) {
    url.searchParams.set("date_from", filters.dateFrom);
  }

  if (filters.dateTo) {
    url.searchParams.set("date_to", filters.dateTo);
  }

  return url.toString();
}

export function buildMapUrl(filters: FilterState) {
  const url = new URL("/api/v1/news/map", API_BASE_URL);

  if (filters.category) {
    url.searchParams.set("category", filters.category);
  }

  if (filters.district) {
    url.searchParams.set("district", filters.district);
  }

  if (filters.dateFrom) {
    url.searchParams.set("date_from", filters.dateFrom);
  }

  if (filters.dateTo) {
    url.searchParams.set("date_to", filters.dateTo);
  }

  url.searchParams.set("limit", "500");

  return url.toString();
}

export async function fetchNewsStats(filters: FilterState): Promise<NewsStats> {
  const response = await fetch(buildStatsUrl(filters), {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Stats request failed with status ${response.status}`);
  }

  return (await response.json()) as NewsStats;
}
