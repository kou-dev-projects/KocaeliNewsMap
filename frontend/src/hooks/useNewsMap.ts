"use client";

import { useQuery } from "@tanstack/react-query";

import type { FilterState } from "@/components/filters/FilterSidebar";
import {
  EMPTY_MAP_RESPONSE,
  fetchNewsMap,
  type NewsMapResponse,
} from "@/lib/news-api";

export function useNewsMap(filters: FilterState) {
  return useQuery<NewsMapResponse>({
    queryKey: ["news-map", filters],
    queryFn: () => fetchNewsMap(filters),
    placeholderData: EMPTY_MAP_RESPONSE,
    staleTime: 30_000,
  });
}
