import type { NewsQueryFilters } from "@/lib/filter-state";
import type { NewsMapItem } from "@/components/map/MapView";

function resolveApiBaseUrl() {
  // Browser requests go through Next.js /api rewrite to avoid CORS and loopback pitfalls.
  if (typeof window !== "undefined") {
    return "";
  }

  return process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
}

function buildApiPath(pathname: string) {
  const apiBaseUrl = resolveApiBaseUrl();
  if (!apiBaseUrl) {
    return pathname;
  }

  return new URL(pathname, apiBaseUrl).toString();
}

const DEFAULT_MAP_LIMIT = Number(process.env.NEXT_PUBLIC_MAP_LIMIT || "1000");

export type NewsStats = {
  total: number;
  geocoded_total: number;
  last_3d_total: number;
  active_sources: number;
  categories: Array<{ key: string; count: number }>;
  districts: Array<{ key: string; count: number }>;
};

export type NewsMapResponse = {
  items: NewsMapItem[];
  total: number;
};

export type NewsDashboardResponse = {
  map: NewsMapResponse;
  stats: NewsStats;
  category_facets: Array<{ key: string; count: number }>;
  district_facets: Array<{ key: string; count: number }>;
};

export type NewsDetail = NewsMapItem & {
  content_text: string;
  location_text_extracted?: string | null;
  source_base_url?: string | null;
  source_domains: string[];
  source_sites: Array<{
    domain: string;
    url: string;
    is_primary: boolean;
  }>;
};

export const EMPTY_STATS: NewsStats = {
  total: 0,
  geocoded_total: 0,
  last_3d_total: 0,
  active_sources: 0,
  categories: [],
  districts: [],
};

export const EMPTY_MAP_RESPONSE: NewsMapResponse = {
  items: [],
  total: 0,
};

export const EMPTY_DASHBOARD_RESPONSE: NewsDashboardResponse = {
  map: EMPTY_MAP_RESPONSE,
  stats: EMPTY_STATS,
  category_facets: [],
  district_facets: [],
};

function appendMultiValue(url: URL, key: string, values?: string[]) {
  if (!values || values.length === 0) {
    return;
  }

  values
    .map((value) => value.trim())
    .filter(Boolean)
    .forEach((value) => {
      url.searchParams.append(key, value);
    });
}

export function buildStatsUrl(filters: NewsQueryFilters) {
  const url = new URL(buildApiPath("/api/v1/news/stats"), "http://localhost");

  appendMultiValue(url, "categories", filters.categories);
  appendMultiValue(url, "districts", filters.districts);

  if (filters.search) {
    url.searchParams.set("search", filters.search);
  }

  if (filters.dateFrom) {
    url.searchParams.set("date_from", filters.dateFrom);
  }

  if (filters.dateTo) {
    url.searchParams.set("date_to", filters.dateTo);
  }

  return resolveApiBaseUrl() ? url.toString() : `${url.pathname}${url.search}`;
}

export function buildMapUrl(filters: NewsQueryFilters) {
  const url = new URL(buildApiPath("/api/v1/news/map"), "http://localhost");

  appendMultiValue(url, "categories", filters.categories);
  appendMultiValue(url, "districts", filters.districts);

  if (filters.search) {
    url.searchParams.set("search", filters.search);
  }

  if (filters.dateFrom) {
    url.searchParams.set("date_from", filters.dateFrom);
  }

  if (filters.dateTo) {
    url.searchParams.set("date_to", filters.dateTo);
  }

  url.searchParams.set("limit", String(filters.limit ?? DEFAULT_MAP_LIMIT));

  return resolveApiBaseUrl() ? url.toString() : `${url.pathname}${url.search}`;
}

export function buildDashboardUrl(filters: NewsQueryFilters) {
  const url = new URL(buildApiPath("/api/v1/news/dashboard"), "http://localhost");

  appendMultiValue(url, "categories", filters.categories);
  appendMultiValue(url, "districts", filters.districts);

  if (filters.search) {
    url.searchParams.set("search", filters.search);
  }

  if (filters.dateFrom) {
    url.searchParams.set("date_from", filters.dateFrom);
  }

  if (filters.dateTo) {
    url.searchParams.set("date_to", filters.dateTo);
  }

  url.searchParams.set("limit", String(filters.limit ?? DEFAULT_MAP_LIMIT));

  return resolveApiBaseUrl() ? url.toString() : `${url.pathname}${url.search}`;
}

export async function fetchNewsStats(filters: NewsQueryFilters): Promise<NewsStats> {
  const response = await fetch(buildStatsUrl(filters), {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Stats request failed with status ${response.status}`);
  }

  return (await response.json()) as NewsStats;
}

export async function fetchNewsMap(filters: NewsQueryFilters): Promise<NewsMapResponse> {
  const response = await fetch(buildMapUrl(filters), {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Map request failed with status ${response.status}`);
  }

  return (await response.json()) as NewsMapResponse;
}

export async function fetchNewsDashboard(
  filters: NewsQueryFilters,
): Promise<NewsDashboardResponse> {
  const response = await fetch(buildDashboardUrl(filters), {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Dashboard request failed with status ${response.status}`);
  }

  return (await response.json()) as NewsDashboardResponse;
}

export async function fetchNewsDetail(newsId: string): Promise<NewsDetail> {
  const response = await fetch(buildApiPath(`/api/v1/news/${encodeURIComponent(newsId)}`), {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Detail request failed with status ${response.status}`);
  }

  return (await response.json()) as NewsDetail;
}
