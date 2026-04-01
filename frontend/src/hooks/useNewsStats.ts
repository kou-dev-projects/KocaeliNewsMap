"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { FilterState } from "@/components/filters/FilterSidebar";
import {
  fetchNewsStats,
  type NewsStats,
} from "@/lib/news-api";
import { newsKeys } from "@/lib/news-query-keys";

export function useNewsStats(filters: FilterState) {
  return useQuery<NewsStats>({
    queryKey: newsKeys.stats(filters),
    queryFn: () => fetchNewsStats(filters),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}
