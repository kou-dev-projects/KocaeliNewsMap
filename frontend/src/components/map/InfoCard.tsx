"use client"

import { useEffect, useMemo, useState, type ReactNode } from "react"
import {
  AlertCircle,
  ArrowUpRight,
  Car,
  Clock3,
  ExternalLink,
  FileText,
  Fingerprint,
  Flame,
  Globe2,
  HeartPulse,
  Loader2,
  MapPin,
  Music2,
  Radar,
  ScanSearch,
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
  not_needed: "Haritada gösterilmiyor",
  processing: "Konum işleniyor",
}

const CATEGORY_PRESENTATION: Record<
  string,
  { tileClass: string; badgeClass: string; icon: ReactNode }
> = {
  unknown: {
    tileClass: "bg-sky-600 text-white shadow-[0_10px_24px_rgba(2,132,199,0.28)]",
    badgeClass: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
    icon: <Star className="h-5 w-5" />,
  },
  trafik_kazasi: {
    tileClass: "bg-amber-500 text-white shadow-[0_10px_24px_rgba(245,158,11,0.28)]",
    badgeClass: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    icon: <Car className="h-5 w-5" />,
  },
  yangin: {
    tileClass: "bg-red-500 text-white shadow-[0_10px_24px_rgba(239,68,68,0.28)]",
    badgeClass: "border-red-500/20 bg-red-500/10 text-red-700 dark:text-red-300",
    icon: <Flame className="h-5 w-5" />,
  },
  elektrik_kesintisi: {
    tileClass: "bg-yellow-500 text-white shadow-[0_10px_24px_rgba(234,179,8,0.28)]",
    badgeClass: "border-yellow-500/20 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300",
    icon: <Zap className="h-5 w-5" />,
  },
  hirsizlik: {
    tileClass: "bg-violet-500 text-white shadow-[0_10px_24px_rgba(139,92,246,0.28)]",
    badgeClass: "border-violet-500/20 bg-violet-500/10 text-violet-700 dark:text-violet-300",
    icon: <VenetianMask className="h-5 w-5" />,
  },
  kulturel_etkinlik: {
    tileClass: "bg-emerald-500 text-white shadow-[0_10px_24px_rgba(16,185,129,0.28)]",
    badgeClass: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    icon: <Music2 className="h-5 w-5" />,
  },
  spor: {
    tileClass: "bg-orange-500 text-white shadow-[0_10px_24px_rgba(249,115,22,0.28)]",
    badgeClass: "border-orange-500/20 bg-orange-500/10 text-orange-700 dark:text-orange-300",
    icon: <Trophy className="h-5 w-5" />,
  },
  saglik: {
    tileClass: "bg-pink-500 text-white shadow-[0_10px_24px_rgba(236,72,153,0.28)]",
    badgeClass: "border-pink-500/20 bg-pink-500/10 text-pink-700 dark:text-pink-300",
    icon: <HeartPulse className="h-5 w-5" />,
  },
}

const GEOCODE_STATUS_PILL_CLASSES: Record<string, string> = {
  resolved: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  approximate: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  pending: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  processing: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  failed: "border-destructive/25 bg-destructive/10 text-destructive",
  not_needed: "border-border/70 bg-background/70 text-muted-foreground",
}

const HERO_SUMMARY_MAX = 520
const CONTENT_PREVIEW_MAX = 1900

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
      cleanSummary.length < 220 ||
      normalizedContent.startsWith(summaryLead) ||
      cleanContent.length > cleanSummary.length + 180
    ) {
      return trimBySentence(cleanContent, HERO_SUMMARY_MAX)
    }
  }

  if (cleanSummary) {
    return trimBySentence(cleanSummary, HERO_SUMMARY_MAX)
  }

  return "Bu haber için henüz gösterilebilir bir özet oluşturulamadı."
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
      const url = isPrimary && detail?.source_base_url
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

function getCategoryPresentation(category?: string | null) {
  const normalizedKey = normalizeText(category).toLocaleLowerCase("tr-TR").replace(/[_-]+/g, "_")
  return CATEGORY_PRESENTATION[normalizedKey] || CATEGORY_PRESENTATION.unknown
}

function getGeocodePillClass(status?: string | null) {
  const normalizedKey = normalizeText(status).toLocaleLowerCase("tr-TR").replace(/[_-]+/g, "_")
  return GEOCODE_STATUS_PILL_CLASSES[normalizedKey] || GEOCODE_STATUS_PILL_CLASSES.not_needed
}

function PlaceholderCard({ className }: { className: string }) {
  return (
    <section
      data-testid="news-info-card"
      className={`glass-strong flex max-h-[calc(100vh-8.5rem)] flex-col overflow-hidden rounded-[32px] border border-border/70 p-3 shadow-[0_28px_80px_rgba(15,23,42,0.18)] ${className}`}
    >
      <div className="glass relative overflow-hidden rounded-[28px] border border-border/70 p-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.14),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(16,185,129,0.1),transparent_32%)]" />
        <div className="relative">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                Haber Detayı
              </span>
              <h3 className="mt-4 text-[2rem] font-bold tracking-tight text-card-foreground">
                Haritadan bir kayıt seçin
              </h3>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
                Özet, kaynak ağacı, konum kararı ve tam metin burada açılır.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function DetailStatusBadge({
  isFetching,
  hasError,
}: {
  isFetching: boolean
  hasError: boolean
}) {
  if (hasError) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[11px] font-semibold text-amber-700">
        <AlertCircle className="h-3.5 w-3.5" />
        Detay sınırlı
      </span>
    )
  }

  if (!isFetching) {
    return null
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background/70 px-3 py-1.5 text-[11px] font-semibold text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      Güncelleniyor
    </span>
  )
}

function SignalCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-secondary/35 px-4 py-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold tracking-tight text-card-foreground">{value}</p>
      {hint ? (
        <p className="mt-1.5 text-xs leading-5 text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  )
}

function SectionCard({
  icon,
  iconClassName,
  eyebrow,
  title,
  description,
  children,
}: {
  icon: ReactNode
  iconClassName?: string
  eyebrow: string
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="rounded-[26px] border border-border/70 bg-card/80 p-5 shadow-[0_12px_32px_rgba(15,23,42,0.08)]">
      <div className="flex items-start gap-4">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary ${iconClassName || ""}`}
        >
          {icon}
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            {eyebrow}
          </p>
          <h4 className="text-xl font-semibold tracking-tight text-card-foreground">{title}</h4>
          {description ? (
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
          ) : null}
        </div>
      </div>
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  )
}

export default function InfoCard({ item, className = "" }: InfoCardProps) {
  const [showFullContent, setShowFullContent] = useState(false)
  const { data: detail, error, isFetching } = useNewsDetail(item?.id ?? null)

  useEffect(() => {
    setShowFullContent(false)
  }, [item?.id])

  if (!item) {
    return <PlaceholderCard className={className} />
  }

  const activeItem = detail ?? item
  const hasDetailError = Boolean(error)
  const publishedAt = formatPublishedAt(activeItem.published_at_raw)
  const locationText = normalizeText(detail?.location_text_extracted)
  const sourceSites = detail?.source_sites?.length
    ? detail.source_sites
    : buildFallbackSourceSites(item, detail)
  const sourceCount = sourceSites.length
  const sourceDisplayName = normalizeText(activeItem.source_name) || normalizeText(activeItem.source_domain) || "--"
  const summaryText = buildExecutiveSummary(activeItem.summary, detail?.content_text)
  const fullContentText = normalizeText(detail?.content_text)
  const contentPreview = buildContentPreview(detail?.content_text, showFullContent)
  const contentIsTrimmed = Boolean(fullContentText) && contentPreview.length < fullContentText.length
  const coordinates = formatCoordinates(activeItem.latitude, activeItem.longitude)
  const primarySourceUrl = detail?.source_base_url || item.url
  const sourceButtonLabel = sourceCount > 1 ? "Çok kaynağa git" : "Kaynak siteye git"
  const categoryPresentation = getCategoryPresentation(activeItem.category)
  const geocodePillClass = getGeocodePillClass(activeItem.geocode_status)
  const sourceNetworkText =
    sourceCount > 1
      ? "Aynı haber birden fazla yayın alanı üzerinden izleniyor."
      : "Şu an tek yayın alanı görünüyor; yeni eşleşmeler geldikçe burada çoğalır."

  const locationNarrative = useMemo(() => {
    const statusLabel = formatGeocodeStatus(activeItem.geocode_status)
    if (locationText) {
      return `Bu kayıt haritada ${statusLabel.toLocaleLowerCase("tr-TR")} olarak işleniyor. Algılanan ana konum metni "${locationText}" üzerinden çözüldü.`
    }
    if (activeItem.district) {
      return `Bu kayıt haritada ${statusLabel.toLocaleLowerCase("tr-TR")} olarak işleniyor. İlçe kararı ${formatDistrict(activeItem.district)} üzerinden verildi.`
    }
    return `Bu kayıt için konum kararı ${statusLabel.toLocaleLowerCase("tr-TR")} seviyesinde tutuluyor.`
  }, [activeItem.district, activeItem.geocode_status, locationText])

  return (
    <section
      data-testid="news-info-card"
      className={`glass-strong flex max-h-[calc(100vh-8.5rem)] flex-col overflow-hidden rounded-[32px] border border-border/70 p-3 shadow-[0_28px_80px_rgba(15,23,42,0.18)] ${className}`}
    >
      <div className="glass relative overflow-hidden rounded-[28px] border border-border/70 p-5">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.16),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(16,185,129,0.12),transparent_30%)]" />
        <div className="relative">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                <Fingerprint className="h-3.5 w-3.5" />
                Haber Detayı
              </span>
              <span
                className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold ${categoryPresentation.badgeClass}`}
              >
                {formatCategory(activeItem.category)}
              </span>
              <span className="inline-flex items-center rounded-full border border-border/70 bg-background/75 px-3 py-1 text-[11px] font-semibold text-foreground">
                {sourceCount} site
              </span>
            </div>
            <DetailStatusBadge isFetching={isFetching} hasError={hasDetailError} />
          </div>

          <div className="mt-5">
            <div className="flex items-start gap-4">
              <div
                className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl ${categoryPresentation.tileClass}`}
              >
                {categoryPresentation.icon}
              </div>
              <div className="min-w-0 flex-1">
                <h3
                  className="text-[2.15rem] font-bold leading-[1.08] tracking-[-0.04em] text-card-foreground"
                  data-testid="news-info-title"
                >
                  {normalizeText(activeItem.title)}
                </h3>

                <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-2">
                    <Globe2 className="h-4 w-4 text-primary" />
                    {sourceDisplayName}
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <Clock3 className="h-4 w-4 text-primary" />
                    {publishedAt}
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-primary" />
                    {formatDistrict(activeItem.district)}
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto pr-1">
        {hasDetailError ? (
          <div className="mb-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-800">
            Detay servisi şu anda tüm alanları döndüremedi. Panel, harita verisiyle güvenli modda
            gösteriliyor.
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-4">
            <SectionCard
              icon={<Sparkles className="h-5 w-5" />}
              eyebrow="Özet"
              title="Yönetici görünümü"
              description="Kırpma kelime ortasında değil, cümle akışında yapılıyor."
            >
              <div className="rounded-2xl border border-border/70 bg-secondary/35 px-5 py-5">
                <p className="text-[1rem] leading-8 text-card-foreground/86">{summaryText}</p>
              </div>
            </SectionCard>

            <SectionCard
              icon={<FileText className="h-5 w-5" />}
              eyebrow="Tam Metin"
              title="Haber akışı"
              description="Kısa özet yerine haber gövdesinin kendisi baz alınıyor."
            >
              <div className="rounded-2xl border border-border/70 bg-secondary/35 px-5 py-5">
                <p className="text-[0.98rem] leading-8 text-card-foreground/82">{contentPreview}</p>
                {contentIsTrimmed ? (
                  <button
                    type="button"
                    onClick={() => setShowFullContent((current) => !current)}
                    className="mt-4 inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/80 px-4 py-2 text-sm font-semibold text-card-foreground transition hover:border-primary/40 hover:text-primary"
                  >
                    <ArrowUpRight className="h-4 w-4" />
                    {showFullContent ? "Metni daralt" : "Tam metni aç"}
                  </button>
                ) : null}
              </div>
            </SectionCard>
          </div>

          <div className="space-y-4">
            <SectionCard
              icon={<Radar className="h-5 w-5" />}
              eyebrow="Konum Bilgisi"
              title="Harita kararı"
              description={locationNarrative}
            >
              <div
                className="rounded-2xl border border-border/70 bg-secondary/35 px-4 py-4"
                data-testid="news-info-status"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      Durum
                    </p>
                    <p className="mt-2 text-lg font-semibold text-card-foreground">
                      {formatGeocodeStatus(activeItem.geocode_status)}
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${geocodePillClass}`}
                  >
                    <ShieldAlert className="h-4 w-4" />
                    {formatGeocodeStatus(activeItem.geocode_status)}
                  </span>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <SignalCard
                  label="Algılanan Konum"
                  value={locationText || formatDistrict(activeItem.district)}
                  hint={locationText ? "Metinden seçilen ana konum ifadesi." : "Şu an yalnızca ilçe seviyesi bilgi var."}
                />
                <SignalCard
                  label="Harita Noktası"
                  value={coordinates || "Koordinat yok"}
                  hint={coordinates ? "Aktif görselleştirme koordinatı." : "Bu kayıt için nokta üretilmedi."}
                />
              </div>
            </SectionCard>

            <SectionCard
              icon={<ScanSearch className="h-5 w-5" />}
              eyebrow="Kaynak Siteler"
              title="Yayın ağı"
              description={sourceNetworkText}
            >
              <div className="rounded-2xl border border-border/70 bg-secondary/35 px-4 py-4">
                <div className="flex flex-wrap gap-2">
                  {sourceSites.map((site) => (
                    <a
                      key={`${site.domain}-${site.url}`}
                      href={site.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/80 px-3.5 py-2 text-sm font-semibold text-card-foreground transition hover:border-primary/45 hover:bg-primary/5 hover:text-primary"
                    >
                      <Globe2 className="h-4 w-4" />
                      {site.domain}
                      {site.is_primary ? (
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-primary">
                          Ana
                        </span>
                      ) : null}
                    </a>
                  ))}
                </div>
              </div>
            </SectionCard>

          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-border/60 pt-4">
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-[20px] bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/92"
        >
          <ExternalLink className="h-4 w-4" />
          Haberin orijinalini aç
        </a>
        <a
          href={primarySourceUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-[20px] border border-border/70 bg-background/70 px-4 py-3 text-sm font-semibold text-card-foreground transition hover:border-primary/45 hover:text-primary"
        >
          <FileText className="h-4 w-4" />
          {sourceButtonLabel}
        </a>
      </div>
    </section>
  )
}
