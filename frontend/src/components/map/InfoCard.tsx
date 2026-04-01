"use client";

import type { NewsMapItem } from "@/components/map/MapView";

type InfoCardProps = {
  item: NewsMapItem | null;
  className?: string;
};

function formatCategory(category?: string | null) {
  switch (category) {
    case "trafik_kazasi":
      return "Trafik Kazasi";
    case "yangin":
      return "Yangin";
    case "elektrik_kesintisi":
      return "Elektrik Kesintisi";
    case "hirsizlik":
      return "Hirsizlik";
    case "kulturel_etkinlik":
      return "Kulturel Etkinlik";
    case "unknown":
      return "Bilinmiyor";
    default:
      return "--";
  }
}

export default function InfoCard({
  item,
  className = "",
}: InfoCardProps) {
  if (!item) {
    return (
      <section
        className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
              Haber Detayi
            </p>
            <h3 className="mt-2 text-lg font-semibold text-slate-900">
              Haritadan bir haber secin
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              Bir marker secildiginde basit detaylar burada gosterilecek ve
              haberi kaynak sitesinde acabileceksin.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Kaynak
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">--</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Kategori
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">--</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Ilce
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">--</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Tarih
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">--</p>
          </div>
        </div>

        <div className="mt-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Ozet
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Haritadaki bir haber secildiginde, temel detaylar bu alanda
            gosterilecek.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
        Haber Detayi
      </p>
      <h3 className="mt-2 text-lg font-semibold leading-7 text-slate-900">
        {item.title}
      </h3>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Kaynak
          </p>
          <p className="mt-2 text-sm font-medium text-slate-900">
            {item.source_name || item.source_domain || "--"}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Kategori
          </p>
          <p className="mt-2 text-sm font-medium text-slate-900">
            {formatCategory(item.category)}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Ilce
          </p>
          <p className="mt-2 text-sm font-medium text-slate-900">
            {item.district || "--"}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Tarih
          </p>
          <p className="mt-2 text-sm font-medium text-slate-900">
            {item.published_at_raw || "--"}
          </p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Konum Bilgisi
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Bu haber haritada <span className="font-medium">{item.geocode_status}</span>{" "}
          durumunda gosteriliyor.
        </p>
      </div>

      <div className="mt-4">
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex w-full items-center justify-center rounded-lg bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-800"
        >
          Haberi ac
        </a>
      </div>
    </section>
  );
}
