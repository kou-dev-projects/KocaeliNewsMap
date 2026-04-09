"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { NewsQueryFilters } from "@/lib/filter-state";
import {
  fetchNewsDashboard,
  type NewsDashboardResponse,
} from "@/lib/news-api";
import { newsKeys } from "@/lib/news-query-keys";

export function useNewsDashboard(filters: NewsQueryFilters) {
  return useQuery<NewsDashboardResponse>({
    queryKey: newsKeys.dashboard(filters),
    queryFn: () => fetchNewsDashboard(filters),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}
