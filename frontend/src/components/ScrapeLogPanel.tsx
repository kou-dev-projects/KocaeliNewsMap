"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Play, RotateCcw, Square, Trash2 } from "lucide-react";

import { useScrapeEventStream } from "@/hooks/useScrapeEventStream";
import { EMPTY_DASHBOARD_RESPONSE } from "@/lib/news-api";
import { newsKeys } from "@/lib/news-query-keys";
import { adaptScrapeEvent } from "@/lib/scrape/scrapeEventAdapter";
import {
  bootstrapScrape,
  fetchLatestScrapeRun,
  fetchScrapeJobStatus,
  resetScrapeWorkspace,
  stopScrape,
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
  reloadSignal?: number;
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
            {entry.metadata.map((item, index) => (
              <span
                key={`${entry.id}-meta-${index}-${item}`}
                className="rounded-full border border-current/15 bg-background/70 px-2 py-1 text-[11px] font-medium"
              >
                {item}
              </span>
            ))}
          </div>
        ) : null}

        {entry.details.length > 0 ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {entry.details.map((detail, index) => (
              <div
                key={`${entry.id}-detail-${index}-${detail.label}`}
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
  const progress = latestEvent.details.find((item) => item.label === "İlerleme")?.value;
  const outcome = latestEvent.details.find((item) => item.label === "Sonuç")?.value;
  const fetchedCount = latestEvent.details.find((item) => item.label === "Detay çekilen")?.value;
  const listingCount = latestEvent.details.find((item) => item.label === "Bulunan URL")?.value;
  const insertedCount = latestEvent.details.find((item) => item.label === "Yeni kayıt")?.value;
  const duplicateCount = latestEvent.details.find((item) => item.label === "Birleşen tekrar")?.value;
  const failedCount = latestEvent.details.find((item) => item.label === "Hatalı kayıt")?.value;
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
    case "source_progress_checkpoint":
      if (progress || outcome) {
        const summaryBits = [
          progress ? `${progress} işlendi` : null,
          insertedCount ? `${insertedCount} yeni` : null,
          duplicateCount ? `${duplicateCount} tekrar` : null,
          failedCount ? `${failedCount} hatalı` : null,
        ].filter(Boolean);

        if (summaryBits.length > 0) {
          return `${sourceLabel}: ${summaryBits.join(", ")}.`;
        }

        return outcome ? `${sourceLabel}: ${outcome}.` : `${sourceLabel}: URL'ler işleniyor.`;
      }
      return `${sourceLabel}: URL'ler işleniyor.`;
    case "source_crawl_completed":
      return parsedCount
        ? `${sourceLabel} tamamlandı. ${parsedCount} kayıt işlendi, ${insertedCount ?? "0"} yeni haber yazıldı.`
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
    case "job_cancelling":
      return "Scrape durdurma isteği alındı. Worker güvenli noktada işi kapatacak.";
    case "job_cancelled":
      return "Scrape durduruldu.";
    case "workspace_reset_manual":
      return "Veritabanı temizlendi. Yeni scrape için hazır.";
    case "job_heartbeat":
      if (fetchedCount) {
        return `Scrape sürüyor. Şu ana kadar ${fetchedCount} detay URL çekildi.`;
      }
      return "Scrape sürüyor. Worker hâlâ aktif.";
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
        : latestRun.status === "cancelled"
          ? "Son scrape durduruldu."
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

function isExistingActiveJobResponse(result: ScrapeQueuedResponse): boolean {
  return result.reason === "job_already_running";
}

export function ScrapeLogPanel({
  variant = "full",
  reloadSignal = 0,
}: ScrapeLogPanelProps) {
  const queryClient = useQueryClient();
  const isEmbedded = variant === "embedded";
  const [actionError, setActionError] = useState<string | null>(null);
  const [jobStatusMessage, setJobStatusMessage] = useState("Scrape paneli hazır.");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isCancelPending, setIsCancelPending] = useState(false);
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
  const lastInvalidatedEventIdRef = useRef<string | null>(null);
  const latestRunUpdatedAtRef = useRef<number | null>(null);
  const latestRunPollCounterRef = useRef(0);
  const controlsDisabled =
    !isLatestRunHydrated ||
    isSubmitting ||
    isStopping ||
    isResetting;
  const hasActiveJob = activeJobId !== null;
  const runButtonDisabled = controlsDisabled || hasActiveJob;
  const stopButtonDisabled =
    !hasActiveJob || !isLatestRunHydrated || isStopping || isCancelPending;
  const resetButtonDisabled = controlsDisabled || hasActiveJob;
  const latestEvent = useMemo(
    () => events.at(-1) ?? null,
    [events],
  );
  const latestNarrativeEvent = useMemo(
    () =>
      [...events]
        .reverse()
        .find((entry) => entry.event !== "job_heartbeat") ?? latestEvent,
    [events, latestEvent],
  );
  const liveJobMessage = useMemo(
    () => buildLiveJobMessage(latestNarrativeEvent, jobStatusMessage),
    [jobStatusMessage, latestNarrativeEvent],
  );

  const clearVisibleNewsData = () => {
    queryClient.removeQueries({ queryKey: newsKeys.all });
    queryClient.setQueryData(newsKeys.dashboard({}), EMPTY_DASHBOARD_RESPONSE);
  };

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
        latestRunUpdatedAtRef.current = latestRun.updated_at ?? null;
        latestRunPollCounterRef.current = 0;

        if (isActiveScrapeStatus(latestRun.status) && latestRun.job_id) {
          setActiveJobId(latestRun.job_id);
          setIsSubmitting(true);
          setIsCancelPending(false);
        } else {
          setActiveJobId(null);
          setIsSubmitting(false);
          setIsStopping(false);
          setIsCancelPending(false);
        }

        setActionError(
          latestRun.status === "failed"
            ? nextHydratedEvents.at(-1)?.message ?? "Son scrape hata ile bitti."
            : null,
        );
        setJobStatusMessage(
          buildLatestRunMessage(
            latestRun,
            [...nextHydratedEvents]
              .reverse()
              .find((entry) => entry.event !== "job_heartbeat") ??
              nextHydratedEvents.at(-1) ??
              null,
          ),
        );
      } catch (error) {
        if (cancelled) {
          return;
        }

        replaceEvents([]);
        setActiveJobId(null);
        setIsSubmitting(false);
        setIsStopping(false);
        setIsCancelPending(false);
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
  }, [latestRunReloadCount, reloadSignal, replaceEvents]);

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
    const refreshLatestRunSnapshot = async () => {
      latestRunPollCounterRef.current += 1;
      if (latestRunPollCounterRef.current < 4) {
        return;
      }

      latestRunPollCounterRef.current = 0;

      try {
        const latestRun = await fetchLatestScrapeRun();
        if (cancelled || latestRun.job_id !== activeJobId) {
          return;
        }

        const nextUpdatedAt = latestRun.updated_at ?? null;
        if (nextUpdatedAt === latestRunUpdatedAtRef.current) {
          return;
        }

        latestRunUpdatedAtRef.current = nextUpdatedAt;
        const nextHydratedEvents = latestRun.events.map((event, index) =>
          adaptScrapeEvent(
            event,
            `persisted-${latestRun.job_id ?? "latest"}-${index}`,
          ),
        );
        replaceEvents(nextHydratedEvents);
      } catch {
        // SSE is the primary transport; polling fallback should fail quietly.
      }
    };

    const syncJobStatus = async () => {
      try {
        const status = await fetchScrapeJobStatus(activeJobId);
        if (cancelled) {
          return;
        }

        if (status.status === "pending") {
          await refreshLatestRunSnapshot();
          setIsCancelPending(Boolean(status.cancel_requested));
          setJobStatusMessage(
            status.cancel_requested
              ? "Scrape durdurma isteği alındı. Worker mevcut adımı bekliyor."
              : "İş kuyruğa alındı. Worker bekleniyor.",
          );
          return;
        }

        if (status.status === "running") {
          await refreshLatestRunSnapshot();
          setIsCancelPending(Boolean(status.cancel_requested));
          setJobStatusMessage(
            status.cancel_requested
              ? "Scrape durduruluyor. Worker güvenli noktada işi kapatacak."
              : "Scrape çalışıyor. Adımlar canlı logda akıyor.",
          );
          return;
        }

        setIsSubmitting(false);
        setIsStopping(false);
        setIsCancelPending(false);
        setActiveJobId(null);

        if (status.status === "completed") {
          setActionError(null);
          setJobStatusMessage(summarizeRefreshResult(status.result));
          void queryClient.invalidateQueries({ queryKey: newsKeys.all });
          return;
        }

        if (status.status === "cancelled") {
          setActionError(null);
          setJobStatusMessage("Scrape durduruldu.");
          return;
        }

        setActionError(status.error || "Scrape başarısız oldu.");
        setJobStatusMessage("Scrape hata ile bitti.");
      } catch (error) {
        if (cancelled) {
          return;
        }

        setIsSubmitting(false);
        setIsStopping(false);
        setIsCancelPending(false);
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
    latestRunUpdatedAtRef.current = null;
    latestRunPollCounterRef.current = 0;
    setActionError(null);
    setActiveJobId(result.job_id);
    setIsCancelPending(false);
    setJobStatusMessage(message);
    clearVisibleNewsData();
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

      if (isExistingActiveJobResponse(result)) {
        setIsSubmitting(false);
        setActionError(null);
        setActiveJobId(result.job_id);
        setIsCancelPending(false);
        setJobStatusMessage("Devam eden scrape sürüyor. Mevcut iş izleniyor.");
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

  const handleStopScrape = async () => {
    if (!activeJobId) {
      return;
    }

    setIsStopping(true);
    setActionError(null);
    setJobStatusMessage("Scrape durdurma isteği gönderiliyor...");

    try {
      const result = await stopScrape({ jobId: activeJobId });
      setActiveJobId(result.job_id);
      setIsCancelPending(true);
      setJobStatusMessage("Scrape durdurma isteği alındı. Worker güvenli noktada işi kapatacak.");
      setLatestRunReloadCount((current) => current + 1);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Scrape durdurulamadı.",
      );
      setJobStatusMessage("Scrape durdurma isteği hata verdi.");
    } finally {
      setIsStopping(false);
    }
  };

  const handleResetWorkspace = async () => {
    setIsResetting(true);
    setActionError(null);
    setJobStatusMessage("Veritabanı temizleniyor...");

    try {
      await resetScrapeWorkspace();
      clearVisibleNewsData();
      setActiveJobId(null);
      setIsCancelPending(false);
      setJobStatusMessage("Veritabanı temizlendi. Yeni scrape için hazır.");
      setLatestRunReloadCount((current) => current + 1);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Veritabanı temizlenemedi.",
      );
      setJobStatusMessage("Veritabanı temizleme isteği hata verdi.");
    } finally {
      setIsResetting(false);
    }
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

        <div className="mt-4 flex flex-col gap-3">
          <div className="grid max-w-sm grid-cols-1 gap-3">
            <button
              type="button"
              onClick={handleRunScrape}
              disabled={runButtonDisabled}
              className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-primary/30 bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            Scrape Başlat
          </button>
          <button
            type="button"
            onClick={handleStopScrape}
            disabled={stopButtonDisabled}
            className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-800 transition hover:bg-amber-500/15 disabled:cursor-not-allowed disabled:opacity-50 dark:text-amber-200"
          >
            <Square className="h-4 w-4" />
            Scrape Durdur
          </button>
          <button
            type="button"
            onClick={handleResetWorkspace}
            disabled={resetButtonDisabled}
            className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-border/70 bg-background px-4 py-3 text-sm font-semibold text-foreground transition hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
              Veri Tabanı Temizle
            </button>
          </div>
          <div className="w-full rounded-xl border border-border/70 bg-secondary/35 px-4 py-3 text-sm text-foreground">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Canlı Durum
            </p>
            <p className="mt-2 whitespace-normal break-words leading-6">
              {liveJobMessage}
            </p>
          </div>
        </div>

      {activeJobId ? (
        <div className="mt-3 rounded-xl border border-sky-500/25 bg-sky-500/10 px-3 py-3 text-sm text-sky-800 dark:text-sky-200">
          {isCancelPending
            ? "Durdurma isteği alındı. Worker mevcut kaynağı güvenli şekilde kapatıyor."
            : "Haber kayıtları temizlendi. Yeni scrape tamamlandıkça liste ve harita yeniden dolacak."}
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
