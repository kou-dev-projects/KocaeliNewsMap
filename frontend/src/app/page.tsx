"use client"

import { Suspense, useDeferredValue, useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { Globe2, Loader2, MapPinned, Newspaper, TrendingUp, X } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"

import { ScrapeLogPanel } from "@/components/ScrapeLogPanel"
import InfoCard from "@/components/map/InfoCard"
import MapView, { type MapThemeMode, type NewsMapItem } from "@/components/map/MapView"
import { DateRangeSelector } from "@/components/pulse/date-range-selector"
import { DistrictSelector, type DistrictOption } from "@/components/pulse/district-selector"
import { EnhancedCategoryBar } from "@/components/pulse/enhanced-category-bar"
import { EnhancedSidebar } from "@/components/pulse/enhanced-sidebar"
import { EnterpriseHeader } from "@/components/pulse/enterprise-header"
import { LiveNewsFeed, type LiveNewsFeedItem } from "@/components/pulse/live-news-feed"
import { SplashScreen } from "@/components/pulse/splash-screen"
import { StatsCard } from "@/components/pulse/stats-card"
import { useNewsDashboard } from "@/hooks/useNewsDashboard"
import type { NewsQueryFilters } from "@/lib/filter-state"
import { EMPTY_DASHBOARD_RESPONSE } from "@/lib/news-api"
import { newsKeys } from "@/lib/news-query-keys"
import { bootstrapScrape, fetchLatestScrapeRun } from "@/lib/scrape-api"

declare global {
  interface Window {
    __pulseHomeAutoScrapeStarted?: boolean
  }
}

const DEFAULT_MAP_LIMIT = Number(process.env.NEXT_PUBLIC_MAP_LIMIT || "1000")
type PulseCategory = LiveNewsFeedItem["pulseCategory"]

function toFeedCategory(raw?: string | null): LiveNewsFeedItem["pulseCategory"] {
  switch (raw) {
    case "trafik_kazasi":
      return "traffic"
    case "yangin":
      return "fire"
    case "elektrik_kesintisi":
      return "outage"
    case "hirsizlik":
      return "theft"
    case "kulturel_etkinlik":
      return "event"
    default:
      return "breaking"
  }
}

function buildQueryFilters(input: {
  districts?: string[]
  search?: string
  dateFrom?: string
  dateTo?: string
  limit?: number
}): NewsQueryFilters {
  const filters: NewsQueryFilters = {}

  if (input.districts && input.districts.length > 0) {
    filters.districts = input.districts
  }
  if (input.search) {
    filters.search = input.search
  }
  if (input.dateFrom) {
    filters.dateFrom = input.dateFrom
  }
  if (input.dateTo) {
    filters.dateTo = input.dateTo
  }
  if (input.limit) {
    filters.limit = input.limit
  }

  return filters
}

function normalizeDistrict(value?: string | null): string {
  if (!value) {
    return ""
  }

  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
}

function formatDistrictName(value?: string | null): string {
  if (!value) {
    return "Bilinmeyen"
  }

  return value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toLocaleUpperCase("tr-TR") + part.slice(1))
    .join(" ")
}

function parseDateValue(value?: string | null): number {
  if (!value) {
    return 0
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 0
  }

  return date.getTime()
}

function formatRelativeTime(value?: string | null): string {
  const timestamp = parseDateValue(value)
  if (!timestamp) {
    return "Bilinmeyen"
  }

  const diffMinutes = Math.max(1, Math.round((Date.now() - timestamp) / 60_000))

  if (diffMinutes < 60) {
    return `${diffMinutes} dk önce`
  }

  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) {
    return `${diffHours} saat önce`
  }

  const diffDays = Math.round(diffHours / 24)
  return `${diffDays} gün önce`
}

function isLikelyLive(item: NewsMapItem): boolean {
  const timestamp = parseDateValue(item.published_at_raw)
  if (!timestamp) {
    return false
  }

  return Date.now() - timestamp <= 6 * 60 * 60 * 1000
}

function isRecentNews(item: NewsMapItem): boolean {
  const timestamp = parseDateValue(item.published_at_raw)
  if (!timestamp) {
    return false
  }

  return Date.now() - timestamp <= 90 * 60 * 1000
}

function formatDateInputValue(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function getDefaultDateRange() {
  const end = new Date()
  end.setHours(0, 0, 0, 0)

  const start = new Date(end)
  start.setDate(end.getDate() - 2)

  return {
    dateFrom: formatDateInputValue(start),
    dateTo: formatDateInputValue(end),
  }
}

function normalizeDateRange(dateFrom: string, dateTo: string) {
  if (!dateFrom && !dateTo) {
    return { dateFrom: undefined, dateTo: undefined }
  }

  if (dateFrom && dateTo && dateFrom > dateTo) {
    return { dateFrom: dateTo, dateTo: dateFrom }
  }

  return {
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  }
}

function HomeFallback() {
  return (
    <div className="fixed inset-0 bg-background p-4">
      <div className="h-16 w-full animate-shimmer rounded-2xl glass" />
      <div className="mt-4 h-[calc(100%-6rem)] w-full animate-shimmer rounded-2xl glass" />
    </div>
  )
}

function HomeContent() {
  const queryClient = useQueryClient()
  const defaultDateRange = useMemo(() => getDefaultDateRange(), [])
  const [selectedNews, setSelectedNews] = useState<NewsMapItem | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<PulseCategory | null>(null)
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([])
  const [dateFrom, setDateFrom] = useState(defaultDateRange.dateFrom)
  const [dateTo, setDateTo] = useState(defaultDateRange.dateTo)
  const [searchKeyword, setSearchKeyword] = useState("")
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [mapThemeMode, setMapThemeMode] = useState<MapThemeMode>("light")
  const [showSplash, setShowSplash] = useState(true)
  const [scrapeReloadSignal, setScrapeReloadSignal] = useState(0)
  const deferredSearchKeyword = useDeferredValue(searchKeyword)
  const normalizedSearchKeyword = deferredSearchKeyword.trim()
  const normalizedDateRange = useMemo(
    () => normalizeDateRange(dateFrom, dateTo),
    [dateFrom, dateTo],
  )

  const dashboardFilters = useMemo(
    () =>
      buildQueryFilters({
        districts: selectedDistricts.length > 0 ? selectedDistricts : undefined,
        search: normalizedSearchKeyword || undefined,
        dateFrom: normalizedDateRange.dateFrom,
        dateTo: normalizedDateRange.dateTo,
        limit: DEFAULT_MAP_LIMIT,
      }),
    [
      normalizedDateRange.dateFrom,
      normalizedDateRange.dateTo,
      normalizedSearchKeyword,
      selectedDistricts,
    ],
  )

  const {
    data: dashboardData = EMPTY_DASHBOARD_RESPONSE,
    error: dashboardError,
    isLoading: dashboardLoading,
  } = useNewsDashboard(dashboardFilters)

  const stats = dashboardData.stats
  const mapData = dashboardData.map

  const districtOptions = useMemo<DistrictOption[]>(
    () =>
      dashboardData.district_facets.map((bucket) => ({
        id: normalizeDistrict(bucket.key),
        name: formatDistrictName(bucket.key),
        newsCount: bucket.count,
      })),
    [dashboardData.district_facets],
  )

  const effectiveSelectedDistricts = useMemo(
    () =>
      selectedDistricts.length === 0
        ? districtOptions.map((district) => district.id)
        : selectedDistricts,
    [districtOptions, selectedDistricts],
  )

  const mapItems = useMemo(() => {
    return [...mapData.items].sort(
      (a, b) => parseDateValue(b.published_at_raw) - parseDateValue(a.published_at_raw),
    )
  }, [mapData.items])

  const categoryCounts = useMemo<Record<string, number>>(
    () =>
      dashboardData.category_facets.reduce<Record<string, number>>((accumulator, bucket) => {
        const categoryKey = toFeedCategory(bucket.key)
        accumulator[categoryKey] = (accumulator[categoryKey] || 0) + bucket.count
        return accumulator
      }, {}),
    [dashboardData.category_facets],
  )

  const visibleMapItems = useMemo(() => {
    if (!selectedCategory) {
      return mapItems
    }

    return mapItems.filter((item) => toFeedCategory(item.category) === selectedCategory)
  }, [mapItems, selectedCategory])

  const liveFeedItems = useMemo<LiveNewsFeedItem[]>(() => {
    return visibleMapItems.slice(0, 8).map((item) => ({
      ...item,
      isRecent: isRecentNews(item),
      pulseCategory: toFeedCategory(item.category),
      timeLabel: formatRelativeTime(item.published_at_raw),
    }))
  }, [visibleMapItems])

  const visibleSelectedNews =
    selectedNews && visibleMapItems.some((item) => item.id === selectedNews.id)
      ? selectedNews
      : null

  const globalTotalNews = stats.total || mapData.total
  const liveCount = useMemo(() => visibleMapItems.filter(isLikelyLive).length, [visibleMapItems])
  const visibleMapCount = visibleMapItems.length
  const filteredSourceCount = useMemo(
    () =>
      new Set(
        visibleMapItems
          .map((item) => item.source_domain || item.source_name)
          .filter(Boolean),
      ).size,
    [visibleMapItems],
  )

  const dataErrorMessage = useMemo(() => {
    if (!dashboardError) {
      return ""
    }

    return dashboardError instanceof Error
      ? dashboardError.message
      : "Veri akışında beklenmeyen bir hata oluştu."
  }, [dashboardError])

  const isActiveScrapeStatus = (status?: string | null) =>
    status === "pending" || status === "running"

  const wait = (durationMs: number) =>
    new Promise((resolve) => window.setTimeout(resolve, durationMs))

  useEffect(() => {
    if (typeof window === "undefined") {
      return
    }

    if (window.__pulseHomeAutoScrapeStarted) {
      return
    }

    window.__pulseHomeAutoScrapeStarted = true
    let cancelled = false

    const triggerInitialScrape = async () => {
      try {
        const latestRun = await fetchLatestScrapeRun()
        if (cancelled) {
          return
        }

        if (isActiveScrapeStatus(latestRun.status) && latestRun.job_id) {
          setScrapeReloadSignal((current) => current + 1)
          return
        }

        let result: Awaited<ReturnType<typeof bootstrapScrape>> | null = null
        for (let attempt = 0; attempt < 3; attempt += 1) {
          try {
            result = await bootstrapScrape({ reset: true })
            break
          } catch {
            if (attempt === 2 || cancelled) {
              break
            }
            await wait(1200 * (attempt + 1))
          }
        }

        if (cancelled) {
          return
        }

        if (result && "job_id" in result && result.reason !== "job_already_running") {
          queryClient.removeQueries({ queryKey: newsKeys.all })
          queryClient.setQueryData(
            newsKeys.dashboard(dashboardFilters),
            EMPTY_DASHBOARD_RESPONSE,
          )
        }
      } finally {
        if (!cancelled) {
          setScrapeReloadSignal((current) => current + 1)
        }
      }
    }

    void triggerInitialScrape()

    return () => {
      cancelled = true
    }
  }, [dashboardFilters, queryClient])

  return (
    <>
      {showSplash ? <SplashScreen onComplete={() => setShowSplash(false)} /> : null}

      <main className="relative h-screen w-screen overflow-hidden bg-transparent">
        <EnterpriseHeader
          searchQuery={searchKeyword}
          onSearchChange={setSearchKeyword}
          onMenuToggle={() => setIsPanelOpen((current) => !current)}
          isMenuOpen={isPanelOpen}
          totalNews={globalTotalNews}
          liveCount={liveCount}
          mapThemeMode={mapThemeMode}
          onMapThemeModeChange={setMapThemeMode}
        />

        <div className="absolute inset-0 z-0">
          <motion.div
            className="h-full w-full overflow-hidden"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
          >
            <MapView
              className="h-full w-full"
              themeMode={mapThemeMode}
              items={visibleMapItems}
              onMarkerSelect={setSelectedNews}
            />
          </motion.div>

          {dashboardLoading ? (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="glass inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Veriler yükleniyor...
              </div>
            </div>
          ) : null}

          {!dashboardLoading && dataErrorMessage ? (
            <div className="pointer-events-none absolute inset-x-0 top-32 flex justify-center px-4">
              <div className="glass rounded-xl border border-destructive/30 px-4 py-3 text-sm text-destructive shadow-lg">
                {dataErrorMessage}
              </div>
            </div>
          ) : null}

          {!dashboardLoading && !dataErrorMessage && visibleMapItems.length === 0 ? (
            <div className="pointer-events-none absolute inset-x-0 top-32 flex justify-center px-4">
              <div className="glass rounded-xl px-4 py-3 text-sm text-muted-foreground shadow-lg">
                Aktif filtrelere göre gösterilecek haber bulunamadı.
              </div>
            </div>
          ) : null}
        </div>

        <LiveNewsFeed news={liveFeedItems} onNewsClick={setSelectedNews} hidden={isPanelOpen} />

        <div className="pointer-events-none absolute bottom-4 left-1/2 z-20 hidden w-full max-w-[1600px] -translate-x-1/2 px-4 xl:block">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{
              opacity: isPanelOpen ? 0 : 1,
              y: isPanelOpen ? 12 : 0,
              pointerEvents: isPanelOpen ? "none" : "auto",
            }}
            transition={{ delay: 0.26 }}
            className="pointer-events-auto hidden xl:block"
          >
            <div className="rounded-2xl glass p-1.5 shadow-2xl">
              <div
                className="grid items-stretch gap-2"
                style={{ gridTemplateColumns: "1.08fr 1.08fr 7.84fr" }}
              >
                <DistrictSelector
                  districts={districtOptions}
                  selected={effectiveSelectedDistricts}
                  onChange={setSelectedDistricts}
                />
                <DateRangeSelector
                  dateFrom={dateFrom}
                  dateTo={dateTo}
                  onDateFromChange={setDateFrom}
                  onDateToChange={setDateTo}
                  onResetToDefault={() => {
                    setDateFrom(defaultDateRange.dateFrom)
                    setDateTo(defaultDateRange.dateTo)
                  }}
                />
                <div>
                  <EnhancedCategoryBar
                    selectedCategory={selectedCategory}
                    onCategoryChange={(category) =>
                      setSelectedCategory(category as PulseCategory | null)
                    }
                    categoryCounts={categoryCounts}
                    embedded
                  />
                  </div>
              </div>
            </div>
          </motion.div>
        </div>

        <EnhancedSidebar
          isOpen={isPanelOpen}
          onClose={() => setIsPanelOpen(false)}
          title="Canlı Kontrol Paneli"
          subtitle="Özet kartlar üstte, scrape işlemleri hemen altında."
        >
          {dataErrorMessage ? (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {dataErrorMessage}
            </div>
          ) : null}

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <StatsCard
                title="Toplam"
                value={globalTotalNews}
                icon={<Newspaper className="h-4 w-4" />}
                color="bg-primary"
                delay={0}
              />
              <StatsCard
                title="Haritada"
                value={visibleMapCount}
                icon={<MapPinned className="h-4 w-4" />}
                color="bg-emerald-500"
                delay={0.05}
              />
              <StatsCard
                title="Kaynak"
                value={filteredSourceCount || stats.active_sources}
                icon={<Globe2 className="h-4 w-4" />}
                color="bg-sky-500"
                delay={0.1}
              />
              <StatsCard
                title="Son 6 Saat"
                value={liveCount}
                icon={<TrendingUp className="h-4 w-4" />}
                color="bg-violet-500"
                delay={0.15}
              />
            </div>

            <div
              className="rounded-xl border border-border/60 bg-secondary/40 px-3 py-2 text-xs text-muted-foreground"
              data-testid="visible-news-count"
            >
              Haritada {visibleMapCount} / toplam {globalTotalNews} haber
            </div>

            <ScrapeLogPanel variant="embedded" reloadSignal={scrapeReloadSignal} />
          </div>
        </EnhancedSidebar>

        {visibleSelectedNews ? (
          <motion.div
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.22 }}
            className="pointer-events-none absolute inset-x-4 top-28 z-20 flex justify-center xl:inset-x-auto xl:right-6 xl:top-28"
          >
            <div className="pointer-events-auto relative w-full max-w-[58rem]">
              <button
                type="button"
                onClick={() => setSelectedNews(null)}
                className="absolute right-3 top-3 z-10 rounded-full border border-border/70 bg-background/80 p-2 text-foreground shadow-sm backdrop-blur transition hover:bg-background"
                aria-label="Haber detayını kapat"
              >
                <X className="h-4 w-4" />
              </button>
              <InfoCard
                item={visibleSelectedNews}
                className="shadow-[0_24px_60px_rgba(15,23,42,0.22)]"
              />
            </div>
          </motion.div>
        ) : null}
      </main>
    </>
  )
}

export default function Home() {
  return (
    <Suspense fallback={<HomeFallback />}>
      <HomeContent />
    </Suspense>
  )
}
