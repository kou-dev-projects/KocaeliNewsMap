"use client";

import { Suspense, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import FilterSidebar, {
  type FilterState,
} from "@/components/filters/FilterSidebar";
import InfoCard from "@/components/map/InfoCard";
import MapView, { type NewsMapItem } from "@/components/map/MapView";
import { useNewsMap } from "@/hooks/useNewsMap";
import { useNewsStats } from "@/hooks/useNewsStats";
import { EMPTY_MAP_RESPONSE, EMPTY_STATS } from "@/lib/news-api";

const EMPTY_FILTERS: FilterState = {
  category: "",
  district: "",
  dateFrom: "",
  dateTo: "",
};

const CATEGORY_LABELS: Record<string, string> = {
  trafik_kazasi: "Trafik Kazasi",
  yangin: "Yangin",
  elektrik_kesintisi: "Elektrik Kesintisi",
  hirsizlik: "Hirsizlik",
  kulturel_etkinlik: "Kulturel Etkinlik",
};

const DISTRICT_LABELS: Record<string, string> = {
  izmit: "Izmit",
  gebze: "Gebze",
  darica: "Darica",
  golcuk: "Golcuk",
  hereke: "Hereke",
  korfez: "Korfez",
  kartepe: "Kartepe",
  basiskele: "Basiskele",
  cayirova: "Cayirova",
  dilovasi: "Dilovasi",
  kandira: "Kandira",
  karamursel: "Karamursel",
  derince: "Derince",
};

type SearchParamsLike = {
  get(name: string): string | null;
};

function filtersFromSearchParams(searchParams: SearchParamsLike) {
  return {
    category: searchParams.get("category") ?? "",
    district: searchParams.get("district") ?? "",
    dateFrom: searchParams.get("date_from") ?? "",
    dateTo: searchParams.get("date_to") ?? "",
  };
}

function formatFilterSummary(filters: FilterState) {
  const parts: string[] = [];

  if (filters.category) {
    parts.push(`Tur: ${CATEGORY_LABELS[filters.category] ?? filters.category}`);
  }

  if (filters.district) {
    parts.push(`Ilce: ${DISTRICT_LABELS[filters.district] ?? filters.district}`);
  }

  if (filters.dateFrom || filters.dateTo) {
    const from = filters.dateFrom || "baslangic yok";
    const to = filters.dateTo || "bugune kadar";
    parts.push(`Tarih: ${from} - ${to}`);
  }

  if (parts.length === 0) {
    return "Aktif filtre yok. Tum haberler gosterilecek.";
  }

  return parts.join(" | ");
}

function HomeFallback() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:px-5 lg:max-w-[1500px] lg:px-6">
        <header className="rounded-2xl bg-white px-5 py-4 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
            PULSE
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            Kocaeli Haber Haritasi
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Harita ve filtreler hazirlaniyor.
          </p>
        </header>

        <section className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((key) => (
            <article
              key={key}
              className="rounded-xl bg-white px-4 py-3 shadow-sm"
            >
              <div className="h-4 w-20 rounded bg-slate-200" />
              <div className="mt-3 h-8 w-14 rounded bg-slate-200" />
            </article>
          ))}
        </section>

        <section className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[280px_minmax(0,1fr)]">
          <div className="min-h-[320px] rounded-2xl bg-white shadow-sm" />
          <div className="min-h-[560px] rounded-2xl bg-white shadow-sm" />
        </section>
      </main>
    </div>
  );
}

function HomeContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const initialFilters = filtersFromSearchParams(searchParams);

  const [draftFilters, setDraftFilters] = useState<FilterState>(initialFilters);
  const [appliedFilters, setAppliedFilters] =
    useState<FilterState>(initialFilters);
  const [selectedNews, setSelectedNews] = useState<NewsMapItem | null>(null);

  const {
    data: stats = EMPTY_STATS,
    isLoading: statsLoading,
    isError: statsIsError,
  } = useNewsStats(appliedFilters);

  const {
    data: mapData = EMPTY_MAP_RESPONSE,
    isLoading: mapLoading,
    isError: mapIsError,
  } = useNewsMap(appliedFilters);

  const statsError = statsIsError ? "Istatistikler su anda yuklenemedi." : "";
  const mapError = mapIsError ? "Harita verileri su anda yuklenemedi." : "";
  const visibleSelectedNews =
    selectedNews && mapData.items.some((item) => item.id === selectedNews.id)
      ? selectedNews
      : null;

  const handleDraftChange = (field: keyof FilterState, value: string) => {
    setDraftFilters((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleApplyFilters = () => {
    setAppliedFilters(draftFilters);

    const nextParams = new URLSearchParams(searchParams.toString());

    if (draftFilters.category) {
      nextParams.set("category", draftFilters.category);
    } else {
      nextParams.delete("category");
    }

    if (draftFilters.district) {
      nextParams.set("district", draftFilters.district);
    } else {
      nextParams.delete("district");
    }

    if (draftFilters.dateFrom) {
      nextParams.set("date_from", draftFilters.dateFrom);
    } else {
      nextParams.delete("date_from");
    }

    if (draftFilters.dateTo) {
      nextParams.set("date_to", draftFilters.dateTo);
    } else {
      nextParams.delete("date_to");
    }

    const nextQuery = nextParams.toString();
    const nextUrl = nextQuery ? `${pathname}?${nextQuery}` : pathname;
    router.replace(nextUrl, { scroll: false });
  };

  const handleResetFilters = () => {
    setDraftFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    router.replace(pathname, { scroll: false });
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:px-5 lg:max-w-[1500px] lg:px-6">
        <header className="rounded-2xl bg-white px-5 py-4 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
            PULSE
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            Kocaeli Haber Haritasi
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Ilce ve mahalle odakli haberleri tek akista izlemek icin kontrol
            paneli.
          </p>
        </header>

        <section className="grid grid-cols-3 gap-3">
          <article className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Toplam Haber
            </h2>
            <p className="mt-1 text-xl font-bold sm:text-2xl">
              {statsLoading ? "--" : stats.total}
            </p>
          </article>
          <article className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Aktif Kaynak
            </h2>
            <p className="mt-1 text-xl font-bold sm:text-2xl">
              {statsLoading ? "--" : stats.active_sources}
            </p>
          </article>
          <article className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">Son 24 Saat</h2>
            <p className="mt-1 text-xl font-bold sm:text-2xl">
              {statsLoading ? "--" : stats.last_24h_total}
            </p>
          </article>
        </section>

        {statsError ? (
          <section className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {statsError}
          </section>
        ) : null}

        <section className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[280px_minmax(0,1fr)]">
          <FilterSidebar
            values={draftFilters}
            onChange={handleDraftChange}
            onApply={handleApplyFilters}
            onReset={handleResetFilters}
          />

          <article className="flex min-h-[560px] flex-col rounded-2xl bg-white p-4 shadow-sm lg:min-h-0 lg:overflow-hidden">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Harita Gorunumu</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Filtre sonuclari burada harita uzerinde goruntulenecek.
                </p>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-sky-100 bg-sky-50/70 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                Aktif Filtreler
              </p>
              <p className="mt-2 text-sm text-slate-700">
                {formatFilterSummary(appliedFilters)}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                {mapLoading
                  ? "Harita haberleri yukleniyor..."
                  : `${mapData.total} geocoded haber haritada gosteriliyor.`}
              </p>
            </div>

            {mapError ? (
              <section className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {mapError}
              </section>
            ) : null}

            <div className="mt-4 grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="min-h-0 overflow-hidden rounded-xl border border-slate-200">
                <MapView
                  className="h-[360px] w-full sm:h-[420px] lg:h-full"
                  items={mapData.items}
                  onMarkerSelect={setSelectedNews}
                />
              </div>

              <InfoCard
                item={visibleSelectedNews}
                className="lg:min-h-0 lg:overflow-auto"
              />
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<HomeFallback />}>
      <HomeContent />
    </Suspense>
  );
}
