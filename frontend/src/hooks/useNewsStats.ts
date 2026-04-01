"use client";

import { useQuery } from "@tanstack/react-query";

import type { FilterState } from "@/components/filters/FilterSidebar";
import {
  EMPTY_STATS,
  fetchNewsStats,
  type NewsStats,
} from "@/lib/news-api";

export function useNewsStats(filters: FilterState) {
  return useQuery<NewsStats>({
    queryKey: ["news-stats", filters],
    queryFn: () => fetchNewsStats(filters),
    placeholderData: EMPTY_STATS,
    staleTime: 30_000,
  });
}
