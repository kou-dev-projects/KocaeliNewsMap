"use client"

import { useQuery } from "@tanstack/react-query"

import { fetchNewsDetail, type NewsDetail } from "@/lib/news-api"

export function useNewsDetail(newsId: string | null) {
  return useQuery<NewsDetail>({
    queryKey: ["news", "detail", newsId],
    queryFn: () => fetchNewsDetail(newsId as string),
    enabled: Boolean(newsId),
    staleTime: 30_000,
  })
}
