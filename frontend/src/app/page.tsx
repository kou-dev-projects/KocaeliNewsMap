"use client";

import { Suspense, useDeferredValue, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
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
import { EnhancedCategoryBar } from "@/components/pulse/enhanced-category-bar";
import { EnhancedSidebar } from "@/components/pulse/enhanced-sidebar";
import { EnterpriseHeader } from "@/components/pulse/enterprise-header";
import { LiveNewsFeed, type LiveNewsFeedItem } from "@/components/pulse/live-news-feed";
import { SplashScreen } from "@/components/pulse/splash-screen";
import { StatsCard } from "@/components/pulse/stats-card";
import { StatsPanel } from "@/components/pulse/stats-panel";
import { TimelineSlider } from "@/components/pulse/timeline-slider";
import { useNewsDashboard } from "@/hooks/useNewsDashboard";
import type { NewsQueryFilters } from "@/lib/filter-state";
import { EMPTY_DASHBOARD_RESPONSE } from "@/lib/news-api";

type PulseCategoryId = "traffic" | "crime" | "weather" | "event" | "economy";
type FeedCategoryId = LiveNewsFeedItem["pulseCategory"];

const CATEGORY_OPTIONS: PulseCategoryOption[] = [
  { id: "traffic", label: "Trafik", icon: <Car className="h-3.5 w-3.5" />, color: "bg-amber-500" },
  { id: "crime", label: "Asayis", icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "bg-red-500" },
  { id: "weather", label: "Hava", icon: <CloudRain className="h-3.5 w-3.5" />, color: "bg-blue-500" },
  { id: "event", label: "Etkinlik", icon: <CalendarDays className="h-3.5 w-3.5" />, color: "bg-emerald-500" },
  { id: "economy", label: "Gundem", icon: <BriefcaseBusiness className="h-3.5 w-3.5" />, color: "bg-purple-500" },
];

const ALL_CATEGORY_IDS = CATEGORY_OPTIONS.map((option) => option.id);
const DEFAULT_MAP_LIMIT = Number(process.env.NEXT_PUBLIC_MAP_LIMIT || "1000");
const EMPTY_COUNTS: Record<FeedCategoryId, number> = {
  breaking: 0,
  traffic: 0,
  crime: 0,
  weather: 0,
  event: 0,
  economy: 0,
  sports: 0,
  health: 0,
};
const CATEGORY_FILTER_MAP: Record<PulseCategoryId, string[]> = {
  traffic: ["trafik_kazasi"],
  crime: ["hirsizlik", "yangin"],
  weather: ["elektrik_kesintisi"],
  event: ["kulturel_etkinlik"],
  economy: ["unknown"],
};

function toPulseCategory(raw?: string | null): PulseCategoryId {
  switch (raw) {
    case "trafik_kazasi":
      return "traffic";
    case "hirsizlik":
      return "crime";
    case "yangin":
      return "crime";
    case "elektrik_kesintisi":
      return "weather";
    case "kulturel_etkinlik":
      return "event";
    default:
      return "economy";
  }
}

function toFeedCategory(raw?: string | null): LiveNewsFeedItem["pulseCategory"] {
  if (raw === "yangin") {
    return "breaking";
  }

  return toPulseCategory(raw);
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
    accumulateCategoryCounts(counts, toFeedCategory(bucket.key), bucket.count);
  });

  return counts;
}

function buildCategoryCountsFromItems(items: NewsMapItem[]): Record<FeedCategoryId, number> {
  const counts = { ...EMPTY_COUNTS };

  items.forEach((item) => {
    accumulateCategoryCounts(counts, toFeedCategory(item.category), 1);
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

function HomeFallback() {
  return (
    <div className="fixed inset-0 bg-background p-4">
      <div className="h-16 w-full rounded-2xl glass animate-shimmer" />
      <div className="mt-4 h-[calc(100%-6rem)] w-full rounded-2xl glass animate-shimmer" />
    </div>
  );
}

function HomeContent() {
  const { resolvedTheme } = useTheme();
  const [selectedNews, setSelectedNews] = useState<NewsMapItem | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(ALL_CATEGORY_IDS);
  const [selectedDistricts, setSelectedDistricts] = useState<string[]>([]);
  const [timelineTime, setTimelineTime] = useState(new Date());
  const [searchKeyword, setSearchKeyword] = useState("");
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const [timeTick, setTimeTick] = useState(() => Date.now());
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

  const districtSelectionIsExplicit = selectedDistricts.length > 0;
  const dashboardFilters = useMemo(
    () =>
      buildQueryFilters({
        categories: selectedServerCategories,
        districts: districtSelectionIsExplicit ? selectedDistricts : undefined,
        search: normalizedSearchKeyword || undefined,
        limit: DEFAULT_MAP_LIMIT,
      }),
    [
      districtSelectionIsExplicit,
      normalizedSearchKeyword,
      selectedDistricts,
      selectedServerCategories,
    ],
  );

  const {
    data: dashboardData = EMPTY_DASHBOARD_RESPONSE,
    error: dashboardError,
    isLoading: dashboardLoading,
  } = useNewsDashboard(dashboardFilters);

  const stats = dashboardData.stats;
  const mapData = dashboardData.map;

  const districtOptions = useMemo<DistrictOption[]>(
    () =>
      dashboardData.district_facets.map((bucket) => ({
        id: normalizeDistrict(bucket.key),
        name: formatDistrictName(bucket.key),
        newsCount: bucket.count,
      })),
    [dashboardData.district_facets],
  );

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
      return buildCategoryCountsFromStats(dashboardData.category_facets);
    }

    return buildCategoryCountsFromItems(baseFilteredItems);
  }, [baseFilteredItems, dashboardData.category_facets, mapData.items.length, mapData.total]);

  const filteredMapItems = useMemo(() => {
    return baseFilteredItems
      .filter((item) => {
        if (selectedCategory) {
          return toFeedCategory(item.category) === selectedCategory;
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
    if (!dashboardError) {
      return "";
    }

    return dashboardError instanceof Error
      ? dashboardError.message
      : "Veri akisinda beklenmeyen bir hata olustu.";
  }, [dashboardError]);

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

          {dashboardLoading && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="glass inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Veriler yukleniyor...
              </div>
            </div>
          )}

          {!dashboardLoading && dataErrorMessage ? (
            <div className="pointer-events-none absolute inset-x-0 top-32 flex justify-center px-4">
              <div className="glass rounded-xl border border-destructive/30 px-4 py-3 text-sm text-destructive shadow-lg">
                {dataErrorMessage}
              </div>
            </div>
          ) : null}

          {!dashboardLoading && !dataErrorMessage && filteredMapItems.length === 0 ? (
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
          title="Harita Filtreleri"
          subtitle="Kategori, ilce ve zaman filtreleri ile haber gorunumunu daralt."
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
            <InfoCard item={visibleSelectedNews} className="border-border/60 bg-card/90" />
          </div>

          <div
            className="mt-4 rounded-xl border border-border/60 bg-secondary/40 px-3 py-2 text-xs text-muted-foreground"
            data-testid="visible-news-count"
          >
            {filteredMapItems.length} / {stats.total || mapData.total} haber gosteriliyor
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
