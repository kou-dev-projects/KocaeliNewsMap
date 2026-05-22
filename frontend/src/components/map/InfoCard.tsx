"use client"

import { useState, type ReactNode } from "react"
import {
  AlertCircle,
  ArrowUpRight,
  Car,
  Clock3,
  ExternalLink,
  Flame,
  Globe2,
  HeartPulse,
  Loader2,
  MapPin,
  Music2,
  ShieldAlert,
  Sparkles,
  Star,
  Trophy,
  VenetianMask,
  Zap,
} from "lucide-react"

import type { NewsMapItem } from "@/components/map/MapView"
import { useNewsDetail } from "@/hooks/useNewsDetail"
import type { NewsDetail } from "@/lib/news-api"

type InfoCardProps = {
  item: NewsMapItem | null
  className?: string
}

const DISTRICT_LABELS: Record<string, string> = {
  basiskele: "Başiskele",
  cayirova: "Çayırova",
  darica: "Darıca",
  derince: "Derince",
  dilovasi: "Dilovası",
  gebze: "Gebze",
  golcuk: "Gölcük",
  hereke: "Hereke",
  izmit: "İzmit",
  kandira: "Kandıra",
  karamursel: "Karamürsel",
  kartepe: "Kartepe",
  korfez: "Körfez",
}

const CATEGORY_LABELS: Record<string, string> = {
  trafik_kazasi: "Trafik Kazası",
  yangin: "Yangın",
  elektrik_kesintisi: "Elektrik Kesintisi",
  hirsizlik: "Hırsızlık",
  kulturel_etkinlik: "Kültürel Etkinlik",
  unknown: "Gündem",
  spor: "Spor",
  saglik: "Sağlık",
}

const GEOCODE_STATUS_LABELS: Record<string, string> = {
  resolved: "Doğrulanmış konum",
  approximate: "Yaklaşık konum",
  pending: "Konum bekleniyor",
  failed: "Konum çözülemedi",
  not_needed: "Haritada gosterilmiyor",
  processing: "Konum işleniyor",
}

const CATEGORY_PRESENTATION: Record<
  string,
  {
    tileClass: string
    badgeClass: string
    icon: ReactNode
    ctaClass: string
    glowClass: string
    topBarClass: string
  }
> = {
  unknown: {
    tileClass: "bg-sky-500 text-white",
    badgeClass: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300",
    icon: <Star className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-economy)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-economy)]",
    topBarClass: "from-[var(--category-economy)] via-[var(--category-economy)]/70 to-transparent",
  },
  trafik_kazasi: {
    tileClass: "bg-amber-500 text-white",
    badgeClass: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    icon: <Car className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-traffic)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-traffic)]",
    topBarClass: "from-[var(--category-traffic)] via-[var(--category-traffic)]/70 to-transparent",
  },
  yangin: {
    tileClass: "bg-red-500 text-white",
    badgeClass: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300",
    icon: <Flame className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-crime)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-crime)]",
    topBarClass: "from-[var(--category-crime)] via-[var(--category-crime)]/70 to-transparent",
  },
  elektrik_kesintisi: {
    tileClass: "bg-yellow-500 text-white",
    badgeClass: "border-yellow-500/30 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300",
    icon: <Zap className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-weather)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-weather)]",
    topBarClass: "from-[var(--category-weather)] via-[var(--category-weather)]/70 to-transparent",
  },
  hirsizlik: {
    tileClass: "bg-violet-500 text-white",
    badgeClass: "border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300",
    icon: <VenetianMask className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-crime)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-crime)]",
    topBarClass: "from-[var(--category-crime)] via-[var(--category-crime)]/70 to-transparent",
  },
  kulturel_etkinlik: {
    tileClass: "bg-emerald-500 text-white",
    badgeClass: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    icon: <Music2 className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-event)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-event)]",
    topBarClass: "from-[var(--category-event)] via-[var(--category-event)]/70 to-transparent",
  },
  spor: {
    tileClass: "bg-orange-500 text-white",
    badgeClass: "border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-300",
    icon: <Trophy className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-sports)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-sports)]",
    topBarClass: "from-[var(--category-sports)] via-[var(--category-sports)]/70 to-transparent",
  },
  saglik: {
    tileClass: "bg-pink-500 text-white",
    badgeClass: "border-pink-500/30 bg-pink-500/10 text-pink-700 dark:text-pink-300",
    icon: <HeartPulse className="h-4 w-4" />,
    ctaClass: "bg-[var(--category-health)] hover:brightness-110",
    glowClass: "shadow-[0_10px_28px_-12px_var(--category-health)]",
    topBarClass: "from-[var(--category-health)] via-[var(--category-health)]/70 to-transparent",
  },
}

const GEOCODE_STATUS_PILL_CLASSES: Record<string, string> = {
  resolved: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  approximate: "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  pending: "border-sky-500/25 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  processing: "border-sky-500/25 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  failed: "border-destructive/30 bg-destructive/10 text-destructive",
  not_needed: "border-border bg-secondary/60 text-muted-foreground",
}

const HERO_SUMMARY_MAX = 240
const CONTENT_PREVIEW_MAX = 820

function normalizeText(value?: string | null) {
  return (value || "").replace(/\s+/g, " ").trim()
}

function titleCaseToken(token: string) {
  return token.charAt(0).toLocaleUpperCase("tr-TR") + token.slice(1)
}

function formatTokenLabel(value?: string | null) {
  const cleanValue = normalizeText(value)
  if (!cleanValue) {
    return "--"
  }

  const normalizedKey = cleanValue.toLocaleLowerCase("tr-TR").replace(/[_-]+/g, "_")
  if (DISTRICT_LABELS[normalizedKey]) {
    return DISTRICT_LABELS[normalizedKey]
  }
  if (CATEGORY_LABELS[normalizedKey]) {
    return CATEGORY_LABELS[normalizedKey]
  }
  if (GEOCODE_STATUS_LABELS[normalizedKey]) {
    return GEOCODE_STATUS_LABELS[normalizedKey]
  }

  return cleanValue
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map(titleCaseToken)
    .join(" ")
}

function formatCategory(category?: string | null) {
  return formatTokenLabel(category)
}

function formatDistrict(district?: string | null) {
  return formatTokenLabel(district)
}

function formatGeocodeStatus(status?: string | null) {
  return formatTokenLabel(status)
}

function formatPublishedAt(value?: string | null) {
  if (!value) {
    return "--"
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function splitIntoSentences(value?: string | null) {
  const cleanValue = normalizeText(value)
  if (!cleanValue) {
    return []
  }

  const matches = cleanValue.match(/[^.!?…]+(?:[.!?…]+|$)/g)
  return (matches || [cleanValue]).map((part) => part.trim()).filter(Boolean)
}

function trimBySentence(value: string, maxLength: number) {
  if (value.length <= maxLength) {
    return value
  }

  const sentences = splitIntoSentences(value)
  if (sentences.length <= 1) {
    const sliced = value.slice(0, maxLength)
    const lastWhitespace = sliced.lastIndexOf(" ")
    return `${(lastWhitespace > 0 ? sliced.slice(0, lastWhitespace) : sliced).trim()}...`
  }

  let result = ""
  for (const sentence of sentences) {
    const candidate = result ? `${result} ${sentence}` : sentence
    if (candidate.length > maxLength) {
      break
    }
    result = candidate
  }

  if (!result) {
    return trimBySentence(value.slice(0, maxLength), maxLength)
  }

  return result.trim()
}

function buildExecutiveSummary(summary?: string | null, contentText?: string | null) {
  const cleanSummary = normalizeText(summary)
  const cleanContent = normalizeText(contentText)

  if (cleanContent) {
    if (!cleanSummary) {
      return trimBySentence(cleanContent, HERO_SUMMARY_MAX)
    }

    const normalizedSummary = cleanSummary.toLocaleLowerCase("tr-TR")
    const normalizedContent = cleanContent.toLocaleLowerCase("tr-TR")
    const summaryLead = normalizedSummary.slice(0, Math.min(normalizedSummary.length, 96))

    if (
      cleanSummary.length < 180 ||
      normalizedContent.startsWith(summaryLead) ||
      cleanContent.length > cleanSummary.length + 180
    ) {
      return trimBySentence(cleanContent, HERO_SUMMARY_MAX)
    }
  }

  if (cleanSummary) {
    return trimBySentence(cleanSummary, HERO_SUMMARY_MAX)
  }

  return "Bu haber için özet oluşturulamadı."
}

function buildContentPreview(contentText?: string | null, expanded = false) {
  const cleanContent = normalizeText(contentText)
  if (!cleanContent) {
    return "Bu haberin tam metni henüz gelmedi."
  }

  return expanded ? cleanContent : trimBySentence(cleanContent, CONTENT_PREVIEW_MAX)
}

function buildFallbackSourceSites(item: NewsMapItem, detail?: NewsDetail): NewsDetail["source_sites"] {
  const seen = new Set<string>()
  const domains = [
    detail?.source_domain,
    ...(detail?.source_domains || []),
    item.source_domain,
  ].filter(Boolean) as string[]

  return domains
    .map((domain, index) => {
      const cleanDomain = normalizeText(domain)
      if (!cleanDomain) {
        return null
      }

      const key = cleanDomain.toLocaleLowerCase("tr-TR").replace(/^www\./, "")
      if (seen.has(key)) {
        return null
      }
      seen.add(key)

      const isPrimary = index === 0
      const url = isPrimary && normalizeText(detail?.url || item.url)
        ? normalizeText(detail?.url || item.url)
        : isPrimary && detail?.source_base_url
          ? detail.source_base_url
        : cleanDomain.startsWith("http")
          ? cleanDomain
          : `https://${cleanDomain}`

      return {
        domain: cleanDomain,
        url,
        is_primary: isPrimary,
      }
    })
    .filter(Boolean) as NewsDetail["source_sites"]
}

function formatCoordinates(latitude?: number | null, longitude?: number | null) {
  if (typeof latitude !== "number" || typeof longitude !== "number") {
    return null
  }

  return `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`
}

function simplifyForCompare(value: string) {
  return value
    .toLocaleLowerCase("tr-TR")
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
}

function resolveDisplayedLocation(locationText: string, district?: string | null) {
  const districtLabel = formatDistrict(district)
  if (!locationText) {
    return districtLabel
  }

  if (!district || districtLabel === "--") {
    return locationText
  }

  const normalizedLocation = simplifyForCompare(locationText)
  const normalizedDistrict = simplifyForCompare(districtLabel)

  if (!normalizedDistrict || normalizedLocation.includes(normalizedDistrict)) {
    return locationText
  }

  return districtLabel
}

function getCategoryPresentation(category?: string | null) {
  const normalizedKey = normalizeText(category).toLocaleLowerCase("tr-TR").replace(/[_-]+/g, "_")
  return CATEGORY_PRESENTATION[normalizedKey] || CATEGORY_PRESENTATION.unknown
}

function getGeocodePillClass(status?: string | null) {
  const normalizedKey = normalizeText(status).toLocaleLowerCase("tr-TR").replace(/[_-]+/g, "_")
  return GEOCODE_STATUS_PILL_CLASSES[normalizedKey] || GEOCODE_STATUS_PILL_CLASSES.not_needed
}

function DetailStatusBadge({ isFetching, hasError }: { isFetching: boolean; hasError: boolean }) {
  if (hasError) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
        <AlertCircle className="h-3 w-3" />
        Detay sınırlı
      </span>
    )
  }

  if (!isFetching) {
    return null
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-secondary/70 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
      <Loader2 className="h-3 w-3 animate-spin" />
      Güncelleniyor
    </span>
  )
}

function PlaceholderCard({ className }: { className: string }) {
  return (
    <section
      data-testid="news-info-card"
      className={`mx-auto w-full max-w-[23.75rem] overflow-hidden rounded-3xl glass-strong ${className}`}
    >
      <div className="relative border-b border-border/70 p-4">
        <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:28px_28px]" />
        <div className="relative flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">Haber Detayı</p>
            <h3 className="mt-1 text-base font-semibold text-foreground">Haritadan bir kayıt seçin</h3>
            <p className="mt-1.5 text-xs text-muted-foreground">
              Seçilen habere ait özet, konum ve kaynak bilgisi burada açılır.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

export default function InfoCard({ item, className = "" }: InfoCardProps) {
  const [expandedItemId, setExpandedItemId] = useState<string | null>(null)
  const { data: detail, error, isFetching } = useNewsDetail(item?.id ?? null)

  if (!item) {
    return <PlaceholderCard className={className} />
  }

  const showFullContent = expandedItemId === item.id
  const activeItem = detail ?? item
  const hasDetailError = Boolean(error)
  const publishedAt = formatPublishedAt(activeItem.published_at_raw)
  const locationText = normalizeText(detail?.location_text_extracted)
  const sourceSites = detail?.source_sites?.length
    ? detail.source_sites
    : buildFallbackSourceSites(item, detail)
  const sourceDisplayName = normalizeText(activeItem.source_name) || normalizeText(activeItem.source_domain) || "--"
  const summaryText = buildExecutiveSummary(activeItem.summary, detail?.content_text)
  const fullContentText = normalizeText(detail?.content_text)
  const contentPreview = buildContentPreview(detail?.content_text, showFullContent)
  const contentIsTrimmed = Boolean(fullContentText) && contentPreview.length < fullContentText.length
  const coordinates = formatCoordinates(activeItem.latitude, activeItem.longitude)
  const categoryPresentation = getCategoryPresentation(activeItem.category)
  const geocodePillClass = getGeocodePillClass(activeItem.geocode_status)
  const displayedLocation = resolveDisplayedLocation(locationText, activeItem.district)
  const hasRawLocationMismatch = Boolean(locationText) && displayedLocation !== locationText

  const locationNarrative = (() => {
    const statusLabel = formatGeocodeStatus(activeItem.geocode_status)
    if (locationText && !hasRawLocationMismatch) {
      return `Algılanan konum ifadesi "${locationText}". Harita kararı: ${statusLabel.toLocaleLowerCase("tr-TR")}.`
    }
    if (locationText && hasRawLocationMismatch) {
      return `Harita işaretçisi ${displayedLocation} konumunda. Metinden gelen ifade "${locationText}" olduğu için marker konumu esas alındı.`
    }
    if (activeItem.district) {
      return `Konum kararı ${formatDistrict(activeItem.district)} ilçesi üzerinden üretildi.`
    }
    return `Bu kayıt için konum kararı ${statusLabel.toLocaleLowerCase("tr-TR")} seviyesinde.`
  })()

  return (
    <section
      data-testid="news-info-card"
      className={`mx-auto max-h-[calc(100vh-10.5rem)] w-full max-w-[23.75rem] overflow-y-auto rounded-3xl glass-strong ${className}`}
    >
      <div className="relative p-4">
        <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${categoryPresentation.topBarClass}`} />
        <div className="absolute inset-0 opacity-15 [background-image:linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] [background-size:30px_30px]" />

        <div className="relative grid gap-3">
          <div className="rounded-xl border border-border/70 bg-secondary/35 p-3">
            <div className="grid grid-cols-[auto_1fr] items-start gap-3">
              <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${categoryPresentation.tileClass}`}>
                {categoryPresentation.icon}
              </div>

              <div className="min-w-0 space-y-2 text-left">
                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${categoryPresentation.badgeClass}`}>
                    {formatCategory(activeItem.category)}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-md bg-background/70 px-2 py-0.5">
                    <MapPin className="h-3 w-3" />
                    {formatDistrict(activeItem.district)}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-md bg-background/70 px-2 py-0.5">
                    <Clock3 className="h-3 w-3" />
                    {publishedAt}
                  </span>
                </div>

                <h3
                  data-testid="news-info-title"
                  className="text-left text-[1.4rem] font-semibold leading-tight tracking-[-0.02em] text-foreground"
                >
                  {normalizeText(activeItem.title)}
                </h3>

                <p className="text-sm leading-6 text-muted-foreground">{summaryText}</p>

                <p className="text-xs text-muted-foreground">
                  Kaynak: <span className="font-semibold text-foreground">{sourceDisplayName}</span>
                </p>
              </div>
            </div>

            <div className="mt-2 flex justify-end">
              <DetailStatusBadge isFetching={isFetching} hasError={hasDetailError} />
            </div>
          </div>

        <div
          data-testid="news-info-status"
          className="rounded-xl border border-border/70 bg-secondary/35 p-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-foreground">{formatGeocodeStatus(activeItem.geocode_status)}</p>
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${geocodePillClass}`}>
              <ShieldAlert className="h-3 w-3" />
              {formatGeocodeStatus(activeItem.geocode_status)}
            </span>
          </div>
          <p className="mt-1.5 text-xs leading-5 text-muted-foreground">{locationNarrative}</p>

          <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-border/70 bg-background/55 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Algılanan konum</p>
              <p className="mt-1 text-xs font-semibold text-foreground">{displayedLocation}</p>
              {hasRawLocationMismatch ? (
                <p className="mt-1 text-[11px] text-muted-foreground">Metinden: {locationText}</p>
              ) : null}
            </div>
            <div className="rounded-lg border border-border/70 bg-background/55 px-2.5 py-2">
              <p className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Koordinat</p>
              <p className="mt-1 text-xs font-semibold text-foreground">{coordinates || "Koordinat yok"}</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border/70 bg-secondary/35 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Tam metin</p>
          <p className="mt-2 text-sm leading-6 text-foreground/85">{contentPreview}</p>
          {contentIsTrimmed ? (
            <button
              type="button"
              onClick={() => setExpandedItemId((current) => (current === item.id ? null : item.id))}
              className="mt-2.5 inline-flex items-center gap-1 rounded-md border border-border bg-background/70 px-2.5 py-1 text-xs font-semibold text-foreground transition hover:border-primary/45 hover:text-primary"
            >
              <ArrowUpRight className="h-3.5 w-3.5" />
              {showFullContent ? "Metni daralt" : "Tam metni aç"}
            </button>
          ) : null}
        </div>

        {sourceSites.length > 0 ? (
          <div className="rounded-xl border border-border/70 bg-secondary/35 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Kaynaklar</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {sourceSites.map((site) => (
                <a
                  key={`${site.domain}-${site.url}`}
                  href={site.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-background/65 px-2 py-1 text-[11px] font-semibold text-foreground transition hover:border-primary/40 hover:text-primary"
                >
                  <Globe2 className="h-3 w-3" />
                  {site.domain}
                </a>
              ))}
            </div>
          </div>
        ) : null}

        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className={`inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold text-white transition ${categoryPresentation.ctaClass} ${categoryPresentation.glowClass}`}
        >
          <ExternalLink className="h-4 w-4" />
          Haberin tamamını oku
        </a>
      </div>
      </div>
    </section>
  )
}
