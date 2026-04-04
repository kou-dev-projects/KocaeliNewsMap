import type { NewsQueryFilters } from "@/lib/filter-state";

export const newsKeys = {
  all: ["news"] as const,
  dashboard: (filters: NewsQueryFilters) => [...newsKeys.all, "dashboard", filters] as const,
  stats: (filters: NewsQueryFilters) => [...newsKeys.all, "stats", filters] as const,
  map: (filters: NewsQueryFilters) => [...newsKeys.all, "map", filters] as const,
};
