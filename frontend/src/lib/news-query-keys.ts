import type { FilterState } from "@/lib/filter-state";

export const newsKeys = {
  all: ["news"] as const,
  stats: (filters: FilterState) => [...newsKeys.all, "stats", filters] as const,
  map: (filters: FilterState) => [...newsKeys.all, "map", filters] as const,
};
