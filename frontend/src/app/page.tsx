"use client";

import { Suspense, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { useTheme } from "next-themes";
import {
  AlertTriangle,
  BriefcaseBusiness,
  CalendarDays,
  Car,
  CloudRain,
  Globe2,
  Loader2,
  MapPinned,
  Newspaper,
  TrendingUp,
} from "lucide-react";

import InfoCard from "@/components/map/InfoCard";
import MapView, { type NewsMapItem } from "@/components/map/MapView";
import {
  CategoryFilter,
  type PulseCategoryOption,
} from "@/components/pulse/category-filter";
import { DistrictSelector, type DistrictOption } from "@/components/pulse/district-selector";
import { EnhancedSidebar } from "@/components/pulse/enhanced-sidebar";
import { EnterpriseHeader } from "@/components/pulse/enterprise-header";
import { EnhancedCategoryBar } from "@/components/pulse/enhanced-category-bar";
import { LiveNewsFeed, type LiveNewsFeedItem } from "@/components/pulse/live-news-feed";
import { ScrapingLog, type PulseLogEntry } from "@/components/pulse/scraping-log";
import { SplashScreen } from "@/components/pulse/splash-screen";
import { StatsCard } from "@/components/pulse/stats-card";
import { StatsPanel } from "@/components/pulse/stats-panel";
import { TimelineSlider } from "@/components/pulse/timeline-slider";
import { useNewsMap } from "@/hooks/useNewsMap";
import { useNewsStats } from "@/hooks/useNewsStats";
import type { NewsQueryFilters } from "@/lib/filter-state";
import { EMPTY_MAP_RESPONSE, EMPTY_STATS } from "@/lib/news-api";
import { newsKeys } from "@/lib/news-query-keys";
import {
  bootstrapScrape,
  fetchScrapeJobStatus,
  refreshScrape,
  type ScrapeQueuedResponse,
} from "@/lib/scrape-api";

type PulseTone = "info" | "success" | "warning" | "error";
type PulseCategoryId = "traffic" | "crime" | "weather" | "event" | "economy";
type FeedCategoryId = LiveNewsFeedItem["pulseCategory"];

const CATEGORY_OPTIONS: PulseCategoryOption[] = [
  { id: "traffic", label: "Trafik", icon: <Car className="h-3.5 w-3.5" />, color: "bg-amber-500" },
  { id: "crime", label: "Asayiş", icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "bg-red-500" },
  { id: "weather", label: "Hava", icon: <CloudRain className="h-3.5 w-3.5" />, color: "bg-blue-500" },
  { id: "event", label: "Etkinlik", icon: <CalendarDays className="h-3.5 w-3.5" />, color: "bg-emerald-500" },
  { id: "economy", label: "Gündem", icon: <BriefcaseBusiness className="h-3.5 w-3.5" />, color: "bg-purple-500" },
];

const ALL_CATEGORY_IDS = CATEGORY_OPTIONS.map((option) => option.id);
const DEFAULT_MAP_LIMIT = Number(process.env.NEXT_PUBLIC_MAP_LIMIT || "5000");
const EMPTY_COUNTS: Record<FeedCategoryId, number> = {
  breaking: 0,
  traffic: 0,
  fire: 0,
  outage: 0,
  theft: 0,
  event: 0,
};
const CATEGORY_FILTER_MAP: Record<PulseCategoryId, string[]> = {
  traffic: ["trafik_kazasi"],
  crime: ["hirsizlik", "yangin"],
  weather: ["elektrik_kesintisi"],
  event: ["kulturel_etkinlik"],
  economy: ["unknown"],
};

function toFeedCategory(raw?: string | null): LiveNewsFeedItem["pulseCategory"] {
  switch (raw) {
    case "trafik_kazasi":
      return "traffic";
    case "yangin":
      return "fire";
    case "elektrik_kesintisi":
      return "outage";
    case "hirsizlik":
      return "theft";
    case "kulturel_etkinlik":
      return "event";
    default:
      return "breaking";
  }
}

function toCategoryBarCategory(raw?: string | null): Exclude<FeedCategoryId, "breaking"> | null {
  switch (raw) {
    case "trafik_kazasi":
      return "traffic";
    case "yangin":
      return "fire";
    case "elektrik_kesintisi":
      return "outage";
    case "hirsizlik":
      return "theft";
    case "kulturel_etkinlik":
      return "event";
    default:
      return null;
  }
}

function buildQueryFilters(input: {
  categories?: string[];
  districts?: string[];
  search?: string;
  limit?: number;
}): NewsQueryFilters {
  const filters: NewsQueryFilters = {};

  if (input.categories && input.categories.length > 0) {
    filters.categories = input.categories;
  }
  if (input.districts && input.districts.length > 0) {
    filters.districts = input.districts;
  }
  if (input.search) {
    filters.search = input.search;
  }
  if (input.limit) {
    filters.limit = input.limit;
  }

  return filters;
}

function accumulateCategoryCounts(
  target: Record<FeedCategoryId, number>,
  category: FeedCategoryId,
  count: number,
) {
  target[category] = (target[category] || 0) + count;
}

function buildCategoryCountsFromStats(
  buckets: Array<{ key: string; count: number }>,
): Record<FeedCategoryId, number> {
  const counts = { ...EMPTY_COUNTS };

  buckets.forEach((bucket) => {
    const category = toCategoryBarCategory(bucket.key);
    if (!category) {
      return;
    }
    accumulateCategoryCounts(counts, category, bucket.count);
  });

  return counts;
}

function buildCategoryCountsFromItems(items: NewsMapItem[]): Record<FeedCategoryId, number> {
  const counts = { ...EMPTY_COUNTS };

  items.forEach((item) => {
    const category = toCategoryBarCategory(item.category);
    if (category) {
      accumulateCategoryCounts(counts, category, 1);
    }
    if (isRecentNews(item)) {
      accumulateCategoryCounts(counts, "breaking", 1);
    }
  });

  return counts;
}

function normalizeDistrict(value?: string | null): string {
  if (!value) {
    return "";
  }

  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function formatDistrictName(value?: string | null): string {
  if (!value) {
    return "Bilinmeyen";
  }

  return value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toLocaleUpperCase("tr-TR") + part.slice(1))
    .join(" ");
}

function parseDateValue(value?: string | null): number {
  if (!value) {
    return 0;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 0;
  }

  return date.getTime();
}

function formatRelativeTime(value?: string | null): string {
  const timestamp = parseDateValue(value);
  if (!timestamp) {
    return "Bilinmeyen";
  }

  const diffMinutes = Math.max(1, Math.round((Date.now() - timestamp) / 60_000));

  if (diffMinutes < 60) {
    return `${diffMinutes} dk once`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours} saat once`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays} gun once`;
}

function isLikelyLive(item: NewsMapItem): boolean {
  const timestamp = parseDateValue(item.published_at_raw);
  if (!timestamp) {
    return false;
  }

  return Date.now() - timestamp <= 6 * 60 * 60 * 1000;
}

function isRecentNews(item: NewsMapItem): boolean {
  const timestamp = parseDateValue(item.published_at_raw);
  if (!timestamp) {
    return false;
  }

  return Date.now() - timestamp <= 90 * 60 * 1000;
}

function makeLogId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function HomeFallback() {
  return (
    <div className="fixed inset-0 bg-background p-4">
      <div className="h-16 w-full rounded-2xl glass animate-shimmer" />
      <div className="mt-4 h-[calc(100%-6rem)] w-full rounded-2xl glass animate-shimmer" />
    </div>
  );
}

function HomeContent() {
  const queryClient = useQueryClient();
  const { resolvedTheme } = useTheme();
  const hasTriggeredBootstrapRef = useRef(false);
  const lastLoggedErrorRef = useRef("");

  const [selectedNews, setSelectedNews] = useState<NewsMapItem | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(ALL_CATEGORY_IDS);
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [timelineTime, setTimelineTime] = useState(new Date());
  const [searchKeyword, setSearchKeyword] = useState("");
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [activeScrapeJobId, setActiveScrapeJobId] = useState<string | null>(null);
  const [scrapeStatusMessage, setScrapeStatusMessage] = useState("");
  const [scrapeStatusTone, setScrapeStatusTone] = useState<PulseTone>("info");
  const [isRefreshPending, setIsRefreshPending] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const [timeTick, setTimeTick] = useState(() => Date.now());
  const [logs, setLogs] = useState<PulseLogEntry[]>([]);
  const deferredSearchKeyword = useDeferredValue(searchKeyword);
  const normalizedSearchKeyword = deferredSearchKeyword.trim();

  useEffect(() => {
    const timer = window.setInterval(() => {
      setTimeTick(Date.now());
    }, 60_000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  const selectedServerCategories = useMemo(() => {
    if (
      selectedCategories.length === 0 ||
      selectedCategories.length === ALL_CATEGORY_IDS.length
    ) {
      return undefined;
    }

    return selectedCategories.flatMap((category) => {
      const categoryId = category as PulseCategoryId;
      return CATEGORY_FILTER_MAP[categoryId] ?? [];
    });
  }, [selectedCategories]);

  const districtStatsFilters = useMemo(
    () =>
      buildQueryFilters({
        categories: selectedServerCategories,
        search: normalizedSearchKeyword || undefined,
      }),
    [normalizedSearchKeyword, selectedServerCategories],
  );
  const {
    data: districtStats = EMPTY_STATS,
    error: districtStatsError,
    isLoading: districtStatsLoading,
  } = useNewsStats(districtStatsFilters);

  const districtOptions = useMemo<DistrictOption[]>(
    () =>
      districtStats.districts.map((bucket) => ({
        id: normalizeDistrict(bucket.key),
        name: formatDistrictName(bucket.key),
        newsCount: bucket.count,
      })),
    [districtStats.districts],
  );

  const districtSelectionIsExplicit = selectedDistricts.length > 0;
  const selectedServerDistricts = useMemo(() => {
    if (!districtSelectionIsExplicit) {
      return undefined;
    }

    if (districtOptions.length > 0 && selectedDistricts.length >= districtOptions.length) {
      return undefined;
    }

    return selectedDistricts;
  }, [districtOptions.length, districtSelectionIsExplicit, selectedDistricts]);

  const mapFilters = useMemo(
    () =>
      buildQueryFilters({
        categories: selectedServerCategories,
        districts: selectedServerDistricts,
        search: normalizedSearchKeyword || undefined,
        limit: DEFAULT_MAP_LIMIT,
      }),
    [normalizedSearchKeyword, selectedServerCategories, selectedServerDistricts],
  );
  const categoryStatsFilters = useMemo(
    () =>
      buildQueryFilters({
        districts: selectedServerDistricts,
        search: normalizedSearchKeyword || undefined,
      }),
    [normalizedSearchKeyword, selectedServerDistricts],
  );

  const {
    data: stats = EMPTY_STATS,
    error: statsError,
    isLoading: statsLoading,
  } = useNewsStats(mapFilters);
  const {
    data: categoryStats = EMPTY_STATS,
    error: categoryStatsError,
    isLoading: categoryStatsLoading,
  } = useNewsStats(categoryStatsFilters);
  const {
    data: mapData = EMPTY_MAP_RESPONSE,
    error: mapError,
    isLoading: mapLoading,
  } = useNewsMap(mapFilters);

  const appendLog = useCallback((type: PulseLogEntry["type"], message: string, source?: string) => {
    setLogs((current) => [
      ...current.slice(-79),
      {
        id: makeLogId(),
        type,
        message,
        source,
        timestamp: new Date(),
      },
    ]);
  }, []);

  const updateScrapeStatus = useCallback(
    (tone: PulseTone, message: string, source?: string) => {
      setScrapeStatusTone(tone);
      setScrapeStatusMessage(message);
      appendLog(tone, message, source);
    },
    [appendLog],
  );

  const startQueuedScrape = useCallback(
    (result: ScrapeQueuedResponse, message: string) => {
      setActiveScrapeJobId(result.job_id);
      updateScrapeStatus("info", message, "worker");
    },
    [updateScrapeStatus],
  );

  useEffect(() => {
    if (hasTriggeredBootstrapRef.current) {
      return;
    }

    hasTriggeredBootstrapRef.current = true;
    let cancelled = false;

    const runBootstrap = async () => {
      updateScrapeStatus("info", "Ilk veri kontrolu yapiliyor...", "bootstrap");

      try {
        const result = await bootstrapScrape();
        if (cancelled) {
          return;
        }

        if ("job_id" in result) {
          startQueuedScrape(result, "Ilk veri cekimi baslatildi.");
          return;
        }

        updateScrapeStatus("success", "Veri zaten hazir.", "bootstrap");
      } catch (error) {
        if (cancelled) {
          return;
        }

        updateScrapeStatus(
          "error",
          error instanceof Error ? error.message : "Ilk veri kontrolu basarisiz oldu.",
          "bootstrap",
        );
      }
    };

    void runBootstrap();

    return () => {
      cancelled = true;
    };
  }, [startQueuedScrape, updateScrapeStatus]);

  useEffect(() => {
    if (!activeScrapeJobId) {
      return;
    }

    let cancelled = false;

    const syncJobStatus = async () => {
      try {
        const status = await fetchScrapeJobStatus(activeScrapeJobId);
        if (cancelled) {
          return;
        }

        if (status.status === "pending") {
          updateScrapeStatus("info", "Scrape isi kuyruga alindi.", "queue");
          return;
        }

        if (status.status === "running") {
          updateScrapeStatus("warning", "Scrape calisiyor.", "worker");
          return;
        }

        if (status.status === "completed") {
          setActiveScrapeJobId(null);
          setIsRefreshPending(false);
          updateScrapeStatus("success", "Scrape tamamlandi. Veriler yenileniyor.", "worker");
          await queryClient.invalidateQueries({ queryKey: newsKeys.all });
          return;
        }

        if (status.status === "failed") {
          setActiveScrapeJobId(null);
          setIsRefreshPending(false);
          updateScrapeStatus("error", status.error || "Scrape basarisiz oldu.", "worker");
        }
      } catch (error) {
        if (cancelled) {
          return;
        }

        setActiveScrapeJobId(null);
        setIsRefreshPending(false);
        updateScrapeStatus(
          "error",
          error instanceof Error ? error.message : "Scrape durumu su anda kontrol edilemiyor.",
          "worker",
        );
      }
    };

    void syncJobStatus();
    const timer = window.setInterval(() => {
      void syncJobStatus();
    }, 2_500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [activeScrapeJobId, queryClient, updateScrapeStatus]);

  const effectiveSelectedDistricts = useMemo(
    () =>
      selectedDistricts.length === 0
        ? districtOptions.map((district) => district.id)
        : selectedDistricts,
    [districtOptions, selectedDistricts],
  );

  const baseFilteredItems = useMemo(() => {
    return mapData.items
      .filter((item) => {
        const timestamp = parseDateValue(item.published_at_raw);
        if (!timestamp) {
          return true;
        }
        return timestamp <= timelineTime.getTime();
      })
      .sort((a, b) => parseDateValue(b.published_at_raw) - parseDateValue(a.published_at_raw));
  }, [mapData.items, timelineTime]);

  const categoryCounts = useMemo<Record<string, number>>(() => {
    if (mapData.total > mapData.items.length) {
      return buildCategoryCountsFromStats(categoryStats.categories);
    }

    return buildCategoryCountsFromItems(baseFilteredItems);
  }, [baseFilteredItems, categoryStats.categories, mapData.items.length, mapData.total]);

  const filteredMapItems = useMemo(() => {
    return baseFilteredItems
      .filter((item) => {
        if (selectedCategory) {
          if (selectedCategory === "breaking") {
            return isRecentNews(item);
          }
          return toCategoryBarCategory(item.category) === selectedCategory;
        }
        return true;
      })
      .sort((a, b) => parseDateValue(b.published_at_raw) - parseDateValue(a.published_at_raw));
  }, [baseFilteredItems, selectedCategory]);

  const liveFeedItems = useMemo<LiveNewsFeedItem[]>(() => {
    return filteredMapItems.slice(0, 8).map((item) => ({
      ...item,
      isRecent: isRecentNews(item),
      pulseCategory: toFeedCategory(item.category),
      timeLabel: formatRelativeTime(item.published_at_raw),
    }));
  }, [filteredMapItems]);

  const visibleSelectedNews =
    selectedNews && filteredMapItems.some((item) => item.id === selectedNews.id)
      ? selectedNews
      : null;

  const globalTotalNews = stats.total || mapData.total;
  const liveCount = useMemo(() => mapData.items.filter(isLikelyLive).length, [mapData.items]);
  const filteredLiveCount = useMemo(
    () => filteredMapItems.filter(isLikelyLive).length,
    [filteredMapItems],
  );

  const topDistrict = useMemo(() => {
    if (filteredMapItems.length === 0) {
      if (stats.districts.length === 0) {
        return "Izmit";
      }

      const top = [...stats.districts].sort((a, b) => b.count - a.count)[0];
      return formatDistrictName(top?.key || "Izmit");
    }

    const counts = new Map<string, number>();
    filteredMapItems.forEach((item) => {
      const id = normalizeDistrict(item.district);
      if (!id) {
        return;
      }
      counts.set(id, (counts.get(id) || 0) + 1);
    });

    const topEntry = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
    return formatDistrictName(topEntry?.[0] || "Izmit");
  }, [filteredMapItems, stats.districts]);

  const avgNewsPerHour = useMemo(() => {
    if (filteredMapItems.length === 0) {
      return 0;
    }

    return Math.round((filteredMapItems.length / 72) * 10) / 10;
  }, [filteredMapItems.length]);

  const refreshDisabled = isRefreshPending || activeScrapeJobId !== null;
  const mapThemeMode = resolvedTheme === "dark" ? "dark" : "light";
  const filteredGeocodeCount = useMemo(() => {
    if (selectedCategory || timelineTime.getTime() < timeTick - 60_000) {
      return filteredMapItems.length;
    }

    return stats.geocoded_total || filteredMapItems.length;
  }, [filteredMapItems.length, selectedCategory, stats.geocoded_total, timeTick, timelineTime]);
  const filteredSourceCount = useMemo(
    () =>
      new Set(
        filteredMapItems
          .map((item) => item.source_domain || item.source_name)
          .filter(Boolean),
      ).size,
    [filteredMapItems],
  );
  const dataErrorMessage = useMemo(() => {
    const currentError = mapError ?? statsError ?? districtStatsError ?? categoryStatsError;
    if (!currentError) {
      return "";
    }

    return currentError instanceof Error
      ? currentError.message
      : "Veri akisinda beklenmeyen bir hata olustu.";
  }, [categoryStatsError, districtStatsError, mapError, statsError]);

  useEffect(() => {
    if (!dataErrorMessage || lastLoggedErrorRef.current === dataErrorMessage) {
      return;
    }

    const timer = window.setTimeout(() => {
      lastLoggedErrorRef.current = dataErrorMessage;
      appendLog("error", dataErrorMessage, "api");
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [appendLog, dataErrorMessage]);

  const handleRefresh = async () => {
    setSelectedNews(null);
    setIsRefreshPending(true);
    updateScrapeStatus("warning", "Veriler sifirlaniyor ve yeni scrape baslatiliyor...", "refresh");

    try {
      const result = await refreshScrape();
      startQueuedScrape(result, "Yenileme baslatildi.");
    } catch (error) {
      setIsRefreshPending(false);
      updateScrapeStatus(
        "error",
        error instanceof Error ? error.message : "Yenileme baslatilamadi.",
        "refresh",
      );
    }
  };

  return (
    <>
      {showSplash ? <SplashScreen onComplete={() => setShowSplash(false)} /> : null}

      <main className="h-screen w-screen overflow-hidden relative bg-transparent">
      <EnterpriseHeader
        searchQuery={searchKeyword}
        onSearchChange={setSearchKeyword}
        onMenuToggle={() => setIsPanelOpen((current) => !current)}
        isMenuOpen={isPanelOpen}
        totalNews={globalTotalNews}
        liveCount={liveCount}
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
            items={filteredMapItems}
            onMarkerSelect={setSelectedNews}
          />
        </motion.div>

        {(mapLoading || statsLoading || districtStatsLoading || categoryStatsLoading) && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="glass rounded-xl px-4 py-3 inline-flex items-center gap-2 text-sm">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              Veriler yukleniyor...
            </div>
          </div>
        )}

        {!mapLoading && !statsLoading && dataErrorMessage ? (
          <div className="pointer-events-none absolute inset-x-0 top-32 flex justify-center px-4">
            <div className="glass rounded-xl border border-destructive/30 px-4 py-3 text-sm text-destructive shadow-lg">
              {dataErrorMessage}
            </div>
          </div>
        ) : null}

        {!mapLoading && !statsLoading && !dataErrorMessage && filteredMapItems.length === 0 ? (
          <div className="pointer-events-none absolute inset-x-0 top-32 flex justify-center px-4">
            <div className="glass rounded-xl px-4 py-3 text-sm text-muted-foreground shadow-lg">
              Aktif filtrelere gore gosterilecek haber bulunamadi.
            </div>
          </div>
        ) : null}
      </div>

      <LiveNewsFeed news={liveFeedItems} onNewsClick={setSelectedNews} collapsed={isPanelOpen} />

      <StatsPanel
        totalNews={filteredMapItems.length}
        liveCount={filteredLiveCount}
        topDistrict={topDistrict}
        avgNewsPerHour={avgNewsPerHour}
        hidden={isPanelOpen}
      />

      <EnhancedCategoryBar
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
        categoryCounts={categoryCounts}
      />

      <EnhancedSidebar
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        onRefresh={handleRefresh}
        refreshDisabled={refreshDisabled}
        isRefreshing={refreshDisabled}
        title="Canli Kontrol Paneli"
        subtitle={scrapeStatusMessage || "Tarama sistemi hazir."}
      >
        {dataErrorMessage ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {dataErrorMessage}
          </div>
        ) : null}

        <div className="mt-4 grid grid-cols-2 gap-3">
          <StatsCard
            title="Gorunum"
            value={filteredMapItems.length}
            icon={<Newspaper className="h-4 w-4" />}
            color="bg-primary"
            delay={0}
          />
          <StatsCard
            title="Geocode"
            value={filteredGeocodeCount}
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
            value={filteredLiveCount}
            icon={<TrendingUp className="h-4 w-4" />}
            color="bg-violet-500"
            delay={0.15}
          />
        </div>

          <div className="mt-4 space-y-3">
            <CategoryFilter
              selected={selectedCategories}
              onChange={setSelectedCategories}
              options={CATEGORY_OPTIONS}
            />
            <DistrictSelector
              districts={districtOptions}
              selected={effectiveSelectedDistricts}
              onChange={setSelectedDistricts}
            />
        </div>

        <div className="mt-4">
          <TimelineSlider onTimeChange={setTimelineTime} />
        </div>

        <div className="mt-4">
          <ScrapingLog logs={logs} isExpanded />
        </div>

        <div className="mt-4">
          <InfoCard item={visibleSelectedNews} className="border-border/60 bg-card/90" />
        </div>

          <div
            className="mt-4 rounded-xl border border-border/60 bg-secondary/40 px-3 py-2 text-xs text-muted-foreground"
            data-testid="visible-news-count"
          >
            {filteredMapItems.length} / {stats.total || mapData.total} haber gosteriliyor
            {scrapeStatusTone === "warning" && " - tarama devam ediyor"}
          </div>
      </EnhancedSidebar>
    </main>
    </>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<HomeFallback />}>
      <HomeContent />
    </Suspense>
  );
}



