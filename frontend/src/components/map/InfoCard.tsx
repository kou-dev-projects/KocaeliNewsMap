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
    case "spor":
      return "Spor";
    case "saglik":
      return "Saglik";
    default:
      return formatTokenLabel(category);
  }
}

function formatTokenLabel(value?: string | null) {
  if (!value) {
    return "--";
  }

  return value
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toLocaleUpperCase("tr-TR") + part.slice(1))
    .join(" ");
}

function formatDistrict(district?: string | null) {
  return formatTokenLabel(district);
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
    case "not_needed":
      return "Harita disi kayit";
    case "processing":
      return "Konum isleniyor";
    default:
      return formatTokenLabel(status || "--");
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
        className={`rounded-2xl border border-border bg-card/75 p-4 shadow-sm ${className}`}
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
            Haber Detayi
          </p>
          <h3 className="mt-2 text-lg font-semibold text-card-foreground">
            Haritadan bir haber secin
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Bir marker secildiginde kontrol icin gereken temel detaylar burada
            gosterilecek.
          </p>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Kaynak
            </p>
            <p className="mt-2 text-sm font-medium text-card-foreground">--</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Kategori
            </p>
            <p className="mt-2 text-sm font-medium text-card-foreground">--</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Ilce
            </p>
            <p className="mt-2 text-sm font-medium text-card-foreground">--</p>
          </div>
          <div className="rounded-lg border border-border bg-card px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Tarih
            </p>
            <p className="mt-2 text-sm font-medium text-card-foreground">--</p>
          </div>
        </div>

        <div className="mt-3 rounded-lg border border-dashed border-border bg-secondary/40 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Konum Bilgisi
          </p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
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
      className={`rounded-2xl border border-border bg-card/75 p-4 shadow-sm ${className}`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
        Haber Detayi
      </p>
      <h3
        className="mt-2 text-lg font-semibold leading-7 text-card-foreground"
        data-testid="news-info-title"
      >
        {item.title}
      </h3>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Kaynak
          </p>
          <p className="mt-2 text-sm font-medium text-card-foreground">
            {item.source_name || item.source_domain || "--"}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Kategori
          </p>
          <p className="mt-2 text-sm font-medium text-card-foreground">
            {formatCategory(item.category)}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Ilce
          </p>
          <p className="mt-2 text-sm font-medium text-card-foreground">
            {formatDistrict(item.district)}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Tarih
          </p>
          <p className="mt-2 text-sm font-medium text-card-foreground">
            {formatPublishedAt(item.published_at_raw)}
          </p>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-border bg-secondary/40 px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Konum Bilgisi
        </p>
        <p
          className="mt-2 text-sm leading-6 text-muted-foreground"
          data-testid="news-info-status"
        >
          Bu haber haritada{" "}
          <span className="font-medium">{formatGeocodeStatus(item.geocode_status)}</span>{" "}
          durumunda gosteriliyor.
        </p>
      </div>

      <div className="mt-3 rounded-lg border border-border bg-secondary/40 px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Ozet
        </p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {formatSummary(item.summary)}
        </p>
      </div>

      <div className="mt-4">
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
        >
          Haberi ac
        </a>
      </div>
    </section>
  );
}
