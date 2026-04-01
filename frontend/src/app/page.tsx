"use client";

import { useState } from "react";

import FilterSidebar, {
  type FilterState,
} from "@/components/filters/FilterSidebar";
import MapView from "@/components/map/MapView";

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

export default function Home() {
  const [draftFilters, setDraftFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterState>(EMPTY_FILTERS);

  const handleDraftChange = (field: keyof FilterState, value: string) => {
    setDraftFilters((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleApplyFilters = () => {
    setAppliedFilters(draftFilters);
  };

  const handleResetFilters = () => {
    setDraftFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
            PULSE
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Kocaeli Haber Haritasi
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Ilce ve mahalle odakli haberleri tek akista izlemek icin kontrol
            paneli.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Toplam Haber
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Aktif Kaynak
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">Son Crawl</h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
        </section>

        <section className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <FilterSidebar
            values={draftFilters}
            onChange={handleDraftChange}
            onApply={handleApplyFilters}
            onReset={handleResetFilters}
          />

          <article className="flex min-h-[560px] flex-col rounded-2xl bg-white p-6 shadow-sm">
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
            </div>

            <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200">
              <MapView className="h-full min-h-[460px] w-full" />
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}
