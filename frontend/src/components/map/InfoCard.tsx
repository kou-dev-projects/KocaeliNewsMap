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

function formatDistrict(district?: string | null) {
  switch (district) {
    case "izmit":
      return "Izmit";
    case "gebze":
      return "Gebze";
    case "darica":
      return "Darica";
    case "golcuk":
      return "Golcuk";
    case "hereke":
      return "Hereke";
    case "korfez":
      return "Korfez";
    case "kartepe":
      return "Kartepe";
    case "basiskele":
      return "Basiskele";
    case "cayirova":
      return "Cayirova";
    case "dilovasi":
      return "Dilovasi";
    case "kandira":
      return "Kandira";
    case "karamursel":
      return "Karamursel";
    case "derince":
      return "Derince";
    default:
      return "--";
  }
}

function formatGeocodeStatus(status: string) {
  switch (status) {
    case "resolved":
      return "Dogrulanmis konum";
    case "approximate":
      return "Yaklasik konum";
    case "pending":
      return "Konum bekleniyor";
    case "failed":
      return "Konum cozulmedi";
    default:
      return status || "--";
  }
}

function formatPublishedAt(value?: string | null) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatSummary(summary?: string | null) {
  if (!summary || !summary.trim()) {
    return "Bu haber icin henuz ozet alani gelmedi.";
  }

  return summary.trim();
}

export default function InfoCard({
  item,
  className = "",
}: InfoCardProps) {
  if (!item) {
    return (
      <section
        data-testid="news-info-card"
        className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
            Haber Detayi
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            Haritadan bir haber secin
          </h3>
          <p className="mt-2 text-sm text-slate-600">
            Bir marker secildiginde kontrol icin gereken temel detaylar burada
            gosterilecek.
          </p>
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
            Konum Bilgisi
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Haritadaki bir haber secildiginde kontrol icin gereken bilgiler bu
            alanda gosterilecek.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      data-testid="news-info-card"
      className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
        Haber Detayi
      </p>
      <h3
        className="mt-2 text-lg font-semibold leading-7 text-slate-900"
        data-testid="news-info-title"
      >
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
            {formatDistrict(item.district)}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Tarih
          </p>
          <p className="mt-2 text-sm font-medium text-slate-900">
            {formatPublishedAt(item.published_at_raw)}
          </p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Konum Bilgisi
        </p>
        <p
          className="mt-2 text-sm leading-6 text-slate-600"
          data-testid="news-info-status"
        >
          Bu haber haritada{" "}
          <span className="font-medium">{formatGeocodeStatus(item.geocode_status)}</span>{" "}
          durumunda gosteriliyor.
        </p>
      </div>

      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Ozet
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {formatSummary(item.summary)}
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
