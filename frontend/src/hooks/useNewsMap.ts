"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { FilterState } from "@/lib/filter-state";
import {
  fetchNewsMap,
  type NewsMapResponse,
} from "@/lib/news-api";
import { newsKeys } from "@/lib/news-query-keys";

export function useNewsMap(filters: FilterState) {
  return useQuery<NewsMapResponse>({
    queryKey: newsKeys.map(filters),
    queryFn: () => fetchNewsMap(filters),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}
