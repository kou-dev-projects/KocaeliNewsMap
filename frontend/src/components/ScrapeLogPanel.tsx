"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Play, RotateCcw } from "lucide-react";

import { useScrapeEventStream } from "@/hooks/useScrapeEventStream";
import { EMPTY_DASHBOARD_RESPONSE } from "@/lib/news-api";
import { newsKeys } from "@/lib/news-query-keys";
import { adaptScrapeEvent } from "@/lib/scrape/scrapeEventAdapter";
import {
  bootstrapScrape,
  fetchLatestScrapeRun,
  fetchScrapeJobStatus,
  type LatestScrapeRunResponse,
  type ScrapeBootstrapResponse,
  type ScrapeQueuedResponse,
} from "@/lib/scrape-api";
import type {
  ScrapeLogEntry,
  ScrapeLogTone,
  ScrapeStreamConnectionState,
} from "@/lib/scrape/types";

const NEAR_BOTTOM_THRESHOLD_PX = 80;

type ScrapeLogPanelProps = {
  variant?: "full" | "embedded";
};

const connectionMeta: Record<
  ScrapeStreamConnectionState,
  { label: string; className: string }
> = {
  idle: {
    label: "Hazır",
    className: "border-border/70 bg-secondary/70 text-foreground",
  },
  connecting: {
    label: "Bağlanıyor",
    className: "border-sky-500/25 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  },
  connected: {
    label: "Bağlı",
    className: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  },
  reconnecting: {
    label: "Yeniden bağlanıyor",
    className: "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  },
  disconnected: {
    label: "Bağlantı yok",
    className: "border-rose-500/25 bg-rose-500/10 text-rose-700 dark:text-rose-300",
  },
  closed: {
    label: "Kapalı",
    className: "border-border/70 bg-secondary/70 text-foreground",
  },
};

const toneMeta: Record<ScrapeLogTone, string> = {
  info: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  warning: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  error: "border-rose-500/20 bg-rose-500/10 text-rose-700 dark:text-rose-300",
  muted: "border-border/70 bg-secondary/45 text-muted-foreground",
};

function LogRow({ entry }: { entry: ScrapeLogEntry }) {
  return (
    <article className={`rounded-2xl border px-3 py-3 ${toneMeta[entry.tone]}`}>
      <div className="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.18em]">
        <span>{entry.timestampLabel}</span>
        <span>{entry.title}</span>
      </div>

      <div className="mt-2">
        <p className="font-semibold">{entry.message}</p>

        {entry.metadata.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {entry.metadata.map((item) => (
              <span
                key={`${entry.id}-${item}`}
                className="rounded-full border border-current/15 bg-background/70 px-2 py-1 text-[11px] font-medium"
              >
                {item}
              </span>
            ))}
          </div>
        ) : null}

        {entry.details.length > 0 ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {entry.details.map((detail) => (
              <div
                key={`${entry.id}-${detail.label}`}
                className="rounded-xl border border-current/10 bg-background/60 px-2.5 py-2"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-current/70">
                  {detail.label}
                </p>
                <p className="mt-1 text-xs leading-5 text-current">{detail.value}</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function summarizeRefreshResult(result: Record<string, unknown> | undefined): string {
  const refreshCleanup =
    result?.refresh_cleanup && typeof result.refresh_cleanup === "object"
      ? result.refresh_cleanup
      : null;

  if (
    refreshCleanup &&
    "status" in refreshCleanup &&
    refreshCleanup.status === "discarded"
  ) {
    return "Refresh kısmi kaldı. Aday veri atıldı, aktif görünüm korundu.";
  }

  if (
    refreshCleanup &&
    "status" in refreshCleanup &&
    refreshCleanup.status === "failed"
  ) {
    return "Refresh cutover aşamasında hata verdi. Aktif görünüm korunuyor.";
  }

  if (
    refreshCleanup &&
    "status" in refreshCleanup &&
    refreshCleanup.status === "completed"
  ) {
    return "Refresh tamamlandı. Yeni dataset aktive edildi.";
  }

  return "Scrape tamamlandı.";
}

function buildLiveJobMessage(
  latestEvent: ScrapeLogEntry | null,
  fallback: string,
): string {
  if (!latestEvent) {
    return fallback;
  }

  const sourceLabel = latestEvent.source ?? "kaynak";
  const listingCount = latestEvent.details.find((item) => item.label === "Bulunan URL")?.value;
  const parsedCount = latestEvent.details.find((item) => item.label === "Yazılan")?.value;

  switch (latestEvent.event) {
    case "refresh_preserving_active_dataset":
      return "Aktif veri korunuyor. Yeni dataset arka planda hazırlanıyor.";
    case "refresh_generation_started":
      return "Yeni dataset jenerasyonu açıldı. Kaynak taraması başlıyor.";
    case "source_crawl_started":
      return `${sourceLabel} taranıyor.`;
    case "source_listing_collected":
      return listingCount
        ? `${sourceLabel}: ${listingCount} URL bulundu, detaylar işleniyor.`
        : `${sourceLabel}: liste toplandı, detaylar işleniyor.`;
    case "source_crawl_completed":
      return parsedCount
        ? `${sourceLabel} tamamlandı. ${parsedCount} kayıt işlendi.`
        : `${sourceLabel} tamamlandı.`;
    case "source_crawl_failed":
      return `${sourceLabel} hata verdi. Detaylar logda.`;
    case "source_crawl_skipped":
      return `${sourceLabel} atlandı. Neden logda görünüyor.`;
    case "refresh_cutover_started":
      return "Kaynak taraması bitti. Yeni dataset aktive ediliyor.";
    case "refresh_cleanup_completed":
      return "Yeni dataset aktive edildi. Görünüm yenileniyor.";
    case "refresh_cleanup_skipped":
      return "Refresh kısmi kaldı. Aktif görünüm korunuyor.";
    case "refresh_cleanup_failed":
      return "Cutover hata verdi. Aktif görünüm korunuyor.";
    default:
      return fallback;
  }
}

function isActiveScrapeStatus(status: string | null | undefined): boolean {
  return status === "pending" || status === "running";
}

function buildLatestRunMessage(
  latestRun: LatestScrapeRunResponse,
  latestEvent: ScrapeLogEntry | null,
): string {
  if (latestRun.event_count === 0) {
    return "Henuz scrape gecmisi yok.";
  }

  const fallback =
    latestRun.status === "pending"
      ? "Son scrape kuyrukta bekliyor."
      : latestRun.status === "running"
        ? "Son scrape calisiyor. Adimlar canli logda akiyor."
        : latestRun.status === "failed"
          ? "Son scrape hata ile bitti."
          : "Son scrape tamamlandi.";

  return buildLiveJobMessage(latestEvent, fallback);
}

function isQueuedScrapeResponse(
  result: ScrapeBootstrapResponse,
): result is ScrapeQueuedResponse {
  return "job_id" in result;
}

export function ScrapeLogPanel({
  variant = "full",
}: ScrapeLogPanelProps) {
  const queryClient = useQueryClient();
  const isEmbedded = variant === "embedded";
  const [actionError, setActionError] = useState<string | null>(null);
  const [jobStatusMessage, setJobStatusMessage] = useState("Scrape paneli hazır.");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLogOpen, setIsLogOpen] = useState(true);
  const [isLatestRunHydrated, setIsLatestRunHydrated] = useState(false);
  const [latestRunReloadCount, setLatestRunReloadCount] = useState(0);
  const [isReloadingLatestRun, setIsReloadingLatestRun] = useState(false);
  const {
    events,
    connectionState,
    lastActivityLabel,
    errorMessage,
    clearEvents,
    replaceEvents,
  } = useScrapeEventStream({
    enabled: isLatestRunHydrated && activeJobId !== null,
    jobId: activeJobId ?? undefined,
  });
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hasAutoStartedRef = useRef(false);
  const lastInvalidatedEventIdRef = useRef<string | null>(null);
  const controlsDisabled =
    !isLatestRunHydrated ||
    isSubmitting;
  const latestEvent = useMemo(
    () => events.at(-1) ?? null,
    [events],
  );
  const liveJobMessage = useMemo(
    () => buildLiveJobMessage(latestEvent, jobStatusMessage),
    [jobStatusMessage, latestEvent],
  );

  useEffect(() => {
    if (!latestEvent || latestEvent.event !== "refresh_cleanup_completed") {
      return;
    }

    if (lastInvalidatedEventIdRef.current === latestEvent.id) {
      return;
    }

    lastInvalidatedEventIdRef.current = latestEvent.id;
    void queryClient.invalidateQueries({ queryKey: newsKeys.all });
  }, [latestEvent, queryClient]);

  useEffect(() => {
    let cancelled = false;
    setIsLatestRunHydrated(false);
    setIsReloadingLatestRun(true);

    const loadLatestRun = async () => {
      try {
        const latestRun = await fetchLatestScrapeRun();
        if (cancelled) {
          return;
        }

        const nextHydratedEvents = latestRun.events.map((event, index) =>
          adaptScrapeEvent(
            event,
            `persisted-${latestRun.job_id ?? "latest"}-${index}`,
          ),
        );

        replaceEvents(nextHydratedEvents);

        if (isActiveScrapeStatus(latestRun.status) && latestRun.job_id) {
          setActiveJobId(latestRun.job_id);
          setIsSubmitting(true);
        } else {
          setActiveJobId(null);
          setIsSubmitting(false);
        }

        setActionError(
          latestRun.status === "failed"
            ? nextHydratedEvents.at(-1)?.message ?? "Son scrape hata ile bitti."
            : null,
        );
        setJobStatusMessage(
          buildLatestRunMessage(latestRun, nextHydratedEvents.at(-1) ?? null),
        );
      } catch (error) {
        if (cancelled) {
          return;
        }

        replaceEvents([]);
        setActiveJobId(null);
        setIsSubmitting(false);
        setActionError(
          error instanceof Error
            ? error.message
            : "Son scrape loglari yuklenemedi.",
        );
        setJobStatusMessage("Son scrape loglari okunamadi.");
      } finally {
        if (!cancelled) {
          setIsLatestRunHydrated(true);
          setIsReloadingLatestRun(false);
        }
      }
    };

    void loadLatestRun();

    return () => {
      cancelled = true;
    };
  }, [latestRunReloadCount, replaceEvents]);

  useEffect(() => {
    if (!isLatestRunHydrated || hasAutoStartedRef.current) {
      return;
    }

    hasAutoStartedRef.current = true;
    void triggerFreshScrape("Sayfa açılışında veritabanı temizleniyor ve scrape başlatılıyor...");
  }, [isLatestRunHydrated]);

  useEffect(() => {
    if (!isLogOpen) {
      return;
    }

    const bottomElement = bottomRef.current;
    if (!bottomElement) {
      return;
    }

    const scrollContainer = bottomElement.parentElement;
    if (!scrollContainer) {
      return;
    }

    const distanceFromBottom =
      scrollContainer.scrollHeight -
      scrollContainer.scrollTop -
      scrollContainer.clientHeight;

    if (distanceFromBottom > NEAR_BOTTOM_THRESHOLD_PX) {
      return;
    }

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    bottomElement.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "end",
    });
  }, [events.length, isLogOpen]);

  useEffect(() => {
    if (!activeJobId) {
      return;
    }

    let cancelled = false;

    const syncJobStatus = async () => {
      try {
        const status = await fetchScrapeJobStatus(activeJobId);
        if (cancelled) {
          return;
        }

        if (status.status === "pending") {
          setJobStatusMessage("İş kuyruğa alındı. Worker bekleniyor.");
          return;
        }

        if (status.status === "running") {
          setJobStatusMessage("Scrape çalışıyor. Adımlar canlı logda akıyor.");
          return;
        }

        setIsSubmitting(false);
        setActiveJobId(null);

        if (status.status === "completed") {
          setActionError(null);
          setJobStatusMessage(summarizeRefreshResult(status.result));
          void queryClient.invalidateQueries({ queryKey: newsKeys.all });
          return;
        }

        setActionError(status.error || "Scrape başarısız oldu.");
        setJobStatusMessage("Scrape hata ile bitti.");
      } catch (error) {
        if (cancelled) {
          return;
        }

        setIsSubmitting(false);
        setActiveJobId(null);
        setActionError(
          error instanceof Error
            ? error.message
            : "Scrape durumu kontrol edilemiyor.",
        );
        setJobStatusMessage("Scrape durumu alınamadı.");
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
  }, [activeJobId, queryClient]);

  const startQueuedJob = (result: ScrapeQueuedResponse, message: string) => {
    replaceEvents([]);
    clearEvents();
    setActionError(null);
    setActiveJobId(result.job_id);
    setJobStatusMessage(message);
    queryClient.removeQueries({ queryKey: newsKeys.all });
    queryClient.setQueryData(newsKeys.dashboard({}), EMPTY_DASHBOARD_RESPONSE);
  };

  const triggerFreshScrape = async (message: string) => {
    setIsSubmitting(true);
    setActionError(null);
    setJobStatusMessage(message);

    try {
      const result = await bootstrapScrape({ reset: true });
      if (!isQueuedScrapeResponse(result)) {
        setIsSubmitting(false);
        setActionError(null);
        setActiveJobId(null);
        setJobStatusMessage(
          "Veritabanı temizlendi ancak yeni scrape kuyruğa alınmadı. Son durum yeniden yükleniyor.",
        );
        setLatestRunReloadCount((current) => current + 1);
        return;
      }

      startQueuedJob(result, "Veritabanı temizlendi. Yeni scrape başlatıldı.");
    } catch (error) {
      setIsSubmitting(false);
      setActionError(
        error instanceof Error ? error.message : "Scrape başlatılamadı.",
      );
      setJobStatusMessage("Scrape isteği hata verdi.");
    }
  };

  const handleRunScrape = async () => {
    await triggerFreshScrape("Veritabanı temizleniyor ve scrape kuyruğa alınıyor...");
  };

  const handleReloadLatestRun = () => {
    setLatestRunReloadCount((current) => current + 1);
  };

  const containerClassName = isEmbedded
    ? "rounded-2xl border border-border/70 bg-card/85 p-4 shadow-sm"
    : "rounded-[28px] border border-border/70 bg-card/90 p-5 shadow-[0_20px_60px_rgba(15,23,42,0.12)]";

  return (
    <section className={containerClassName}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary/70">
            Scrape kontrolü
          </p>
          <h3 className="mt-1 text-xl font-semibold text-foreground">
            Canlı log ve tetikleme
          </h3>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${connectionMeta[connectionState].className}`}
        >
          {connectionMeta[connectionState].label}
        </span>
      </div>

      <div className="mt-4 rounded-2xl border border-border/70 bg-background/70 p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-foreground">
              Her tetiklemede haber verisi temizlenir ve tarama sıfırdan başlar.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Son aktivite: {lastActivityLabel}. Scrape logları korunur, haber kayıtları yenilenir.
            </p>
          </div>
          <span className="rounded-full border border-border/70 bg-secondary/60 px-3 py-2 text-xs font-medium text-foreground">
            Otomatik reset açık
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={handleRunScrape}
          disabled={controlsDisabled}
          className="inline-flex items-center gap-2 rounded-xl border border-primary/30 bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Play className="h-4 w-4" />
          Scrape Başlat
        </button>
        <div className="min-w-0 flex-1 rounded-xl border border-border/70 bg-secondary/35 px-3 py-3 text-sm text-foreground">
          {liveJobMessage}
        </div>
      </div>

      {activeJobId ? (
        <div className="mt-3 rounded-xl border border-sky-500/25 bg-sky-500/10 px-3 py-3 text-sm text-sky-800 dark:text-sky-200">
          Haber kayıtları temizlendi. Yeni scrape tamamlandıkça liste ve harita yeniden dolacak.
        </div>
      ) : null}

      {actionError ? (
        <div className="mt-4 rounded-xl border border-rose-500/25 bg-rose-500/10 px-3 py-3 text-sm text-rose-700 dark:text-rose-300">
          {actionError}
        </div>
      ) : null}

      {errorMessage ? (
        <div className="mt-4 rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-3 text-sm text-amber-700 dark:text-amber-300">
          {errorMessage}
        </div>
      ) : null}

      <div className="mt-4 rounded-2xl border border-border/70 bg-background/75">
        <div className="flex items-center gap-3 px-4 py-3">
          <button
            type="button"
            onClick={() => setIsLogOpen((current) => !current)}
            className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
            aria-expanded={isLogOpen}
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">Canlı log</p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {events.length} olay, son aktivite {lastActivityLabel}
              </p>
            </div>
            {isLogOpen ? (
              <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
          </button>
          <button
            type="button"
            onClick={handleReloadLatestRun}
            disabled={isReloadingLatestRun}
            className="rounded-lg border border-border/70 bg-background px-2.5 py-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
            aria-label="Son scrape loglarini yenile"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>

        {isLogOpen ? (
          <div className="border-t border-border/70 px-4 py-3">
            <div className="max-h-72 space-y-3 overflow-y-auto pr-1">
              {events.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border/70 bg-secondary/20 px-4 py-8 text-center">
                  <p className="text-sm font-medium text-foreground">Henüz canlı scrape olayı yok.</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Scrape başladıktan sonra kaynak bazlı olaylar burada akacak.
                  </p>
                </div>
              ) : (
                events.map((entry) => <LogRow key={entry.id} entry={entry} />)
              )}
              <div ref={bottomRef} />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
