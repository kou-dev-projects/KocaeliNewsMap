"use client";

import {
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react";
import {
  ChevronDown,
  ChevronUp,
  LogOut,
  Play,
  Trash2,
} from "lucide-react";

import { useScrapeEventStream } from "@/hooks/useScrapeEventStream";
import {
  clearScrapeOpsCredentials,
  getScrapeOpsAuthSnapshot,
  setScrapeOpsCredentials,
  subscribeScrapeOpsAuth,
} from "@/lib/scrape-ops-client-auth";
import {
  fetchScrapeJobStatus,
  refreshScrape,
  type ScrapeQueuedResponse,
} from "@/lib/scrape-api";
import type {
  ScrapeLogEntry,
  ScrapeLogTone,
  ScrapeStreamConnectionState,
} from "@/lib/scrape/types";

const DEFAULT_USERNAME = "ops";
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
    className: "border-slate-300 bg-slate-100 text-slate-700",
  },
  connecting: {
    label: "Bağlanıyor",
    className: "border-sky-200 bg-sky-50 text-sky-700",
  },
  connected: {
    label: "Bağlı",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  reconnecting: {
    label: "Yeniden bağlanıyor",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  },
  disconnected: {
    label: "Bağlantı yok",
    className: "border-rose-200 bg-rose-50 text-rose-700",
  },
  closed: {
    label: "Kapalı",
    className: "border-slate-300 bg-slate-100 text-slate-700",
  },
};

const toneMeta: Record<ScrapeLogTone, string> = {
  info: "border-sky-200 bg-sky-50 text-sky-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  error: "border-rose-200 bg-rose-50 text-rose-700",
  muted: "border-slate-200 bg-slate-50 text-slate-600",
};

function LogRow({ entry }: { entry: ScrapeLogEntry }) {
  return (
    <article className={`rounded-2xl border px-3 py-3 ${toneMeta[entry.tone]}`}>
      <div className="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.18em]">
        <span>{entry.timestampLabel}</span>
        <span>{entry.event.replaceAll("_", " ")}</span>
      </div>
      <div className="mt-2">
        <p className="font-semibold">{entry.title}</p>
        <p className="mt-1 text-sm leading-6">{entry.message}</p>
      </div>
    </article>
  );
}

function summarizeRefreshResult(result: Record<string, unknown> | undefined): string {
  const refreshCleanup = result?.refresh_cleanup;
  if (
    refreshCleanup &&
    typeof refreshCleanup === "object" &&
    "status" in refreshCleanup &&
    refreshCleanup.status === "discarded"
  ) {
    return "Refresh kısmi kaldı. Aday veri atıldı, aktif görünüm korundu.";
  }

  return "Scrape tamamlandı.";
}

export function ScrapeLogPanel({
  variant = "full",
}: ScrapeLogPanelProps) {
  const authSnapshot = useSyncExternalStore(
    subscribeScrapeOpsAuth,
    getScrapeOpsAuthSnapshot,
    () => null,
  );
  const authorizationHeader = authSnapshot?.authorizationHeader;
  const isEmbedded = variant === "embedded";
  const [passwordInput, setPasswordInput] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [jobStatusMessage, setJobStatusMessage] = useState("Scrape paneli hazır.");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLogOpen, setIsLogOpen] = useState(true);
  const {
    events,
    connectionState,
    lastActivityLabel,
    errorMessage,
    clearEvents,
  } = useScrapeEventStream({
    enabled: Boolean(authorizationHeader),
    authorizationHeader,
  });
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const controlsDisabled =
    !authorizationHeader || isSubmitting || activeJobId !== null;

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
    if (!activeJobId || !authorizationHeader) {
      return;
    }

    let cancelled = false;

    const syncJobStatus = async () => {
      try {
        const status = await fetchScrapeJobStatus(activeJobId, authorizationHeader);
        if (cancelled) {
          return;
        }

        if (status.status === "pending") {
          setJobStatusMessage("Scrape kuyruğa alındı.");
          return;
        }

        if (status.status === "running") {
          setJobStatusMessage("Scrape çalışıyor.");
          return;
        }

        setIsSubmitting(false);
        setActiveJobId(null);

        if (status.status === "completed") {
          setActionError(null);
          setJobStatusMessage(summarizeRefreshResult(status.result));
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
  }, [activeJobId, authorizationHeader]);

  const startQueuedJob = (result: ScrapeQueuedResponse, message: string) => {
    setActionError(null);
    setActiveJobId(result.job_id);
    setJobStatusMessage(message);
  };

  const handleAuthSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    try {
      setScrapeOpsCredentials(DEFAULT_USERNAME, passwordInput);
      setPasswordInput("");
      setActionError(null);
      setJobStatusMessage("Operasyon bağlantısı açıldı.");
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Parola kaydedilemedi.",
      );
    }
  };

  const handleAuthClear = () => {
    clearScrapeOpsCredentials();
    setPasswordInput("");
    setActionError(null);
    setActiveJobId(null);
    setIsSubmitting(false);
    setJobStatusMessage("Operasyon bağlantısı kapatıldı.");
  };

  const handleRunScrape = async () => {
    if (!authorizationHeader) {
      setActionError("Önce parola girilip bağlanılmalı.");
      return;
    }

    setIsSubmitting(true);
    setActionError(null);
    setJobStatusMessage("Scrape kuyruğa alınıyor...");

    try {
      const result = await refreshScrape(authorizationHeader);
      startQueuedJob(result, "Scrape başlatıldı.");
    } catch (error) {
      setIsSubmitting(false);
      setActionError(
        error instanceof Error ? error.message : "Scrape başlatılamadı.",
      );
      setJobStatusMessage("Scrape isteği hata verdi.");
    }
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
          <h3 className="mt-1 text-xl font-semibold text-foreground">Canlı log ve tetikleme</h3>
        </div>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${connectionMeta[connectionState].className}`}
        >
          {connectionMeta[connectionState].label}
        </span>
      </div>

      <div className="mt-4 rounded-2xl border border-border/70 bg-background/70 p-3">
        {authorizationHeader ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-foreground">Bağlı kullanıcı: {DEFAULT_USERNAME}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Son aktivite: {lastActivityLabel}
              </p>
            </div>
            <button
              type="button"
              onClick={handleAuthClear}
              className="inline-flex items-center gap-2 rounded-xl border border-border/70 bg-secondary/60 px-3 py-2 text-sm font-medium text-foreground transition hover:bg-secondary"
            >
              <LogOut className="h-4 w-4" />
              Oturumu kapat
            </button>
          </div>
        ) : (
          <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleAuthSubmit}>
            <div className="flex min-w-0 flex-1 items-center rounded-xl border border-border/70 bg-background px-3">
              <span className="shrink-0 text-sm font-medium text-muted-foreground">ops</span>
              <input
                type="password"
                value={passwordInput}
                onChange={(event) => setPasswordInput(event.target.value)}
                placeholder="Scrape şifresi"
                className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
            </div>
            <button
              type="submit"
              className="rounded-xl border border-primary/30 bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
            >
              Bağlan
            </button>
          </form>
        )}
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
          {jobStatusMessage}
        </div>
      </div>

      {actionError ? (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
          {actionError}
        </div>
      ) : null}

      {errorMessage ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-700">
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
            onClick={clearEvents}
            className="rounded-lg border border-border/70 bg-background px-2.5 py-2 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
            aria-label="Log temizle"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>

        {isLogOpen ? (
          <div className="border-t border-border/70 px-4 py-3">
            <div className="max-h-72 space-y-3 overflow-y-auto pr-1">
              {events.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border/70 bg-secondary/20 px-4 py-8 text-center">
                  <p className="text-sm font-medium text-foreground">
                    {authorizationHeader
                      ? "Henüz canlı scrape olayı yok."
                      : "Log akışı için önce bağlanın."}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Scrape başladıktan sonra olaylar burada akacak.
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
