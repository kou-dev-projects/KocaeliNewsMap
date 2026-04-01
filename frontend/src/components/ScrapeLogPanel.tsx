"use client";

import { useEffect, useRef } from "react";

import { useScrapeEventStream } from "@/hooks/useScrapeEventStream";
import type {
  ScrapeLogEntry,
  ScrapeLogTone,
  ScrapeStreamConnectionState,
} from "@/lib/scrape/types";

const NEAR_BOTTOM_THRESHOLD_PX = 80;

const connectionMeta: Record<
  ScrapeStreamConnectionState,
  { label: string; className: string }
> = {
  idle: {
    label: "Idle",
    className: "border-slate-500/40 bg-slate-500/10 text-slate-200",
  },
  connecting: {
    label: "Connecting",
    className: "border-sky-500/40 bg-sky-500/10 text-sky-200",
  },
  connected: {
    label: "Connected",
    className: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
  },
  reconnecting: {
    label: "Reconnecting",
    className: "border-amber-500/40 bg-amber-500/10 text-amber-200",
  },
  disconnected: {
    label: "Disconnected",
    className: "border-rose-500/40 bg-rose-500/10 text-rose-200",
  },
  closed: {
    label: "Closed",
    className: "border-slate-500/40 bg-slate-500/10 text-slate-200",
  },
};

const toneMeta: Record<ScrapeLogTone, string> = {
  info: "border-sky-500/25 bg-sky-500/[0.08] text-sky-50",
  success: "border-emerald-500/25 bg-emerald-500/[0.08] text-emerald-50",
  warning: "border-amber-500/25 bg-amber-500/[0.08] text-amber-50",
  error: "border-rose-500/25 bg-rose-500/[0.08] text-rose-50",
  muted: "border-slate-500/20 bg-slate-500/[0.08] text-slate-300",
};

function LogRow({ entry }: { entry: ScrapeLogEntry }) {
  return (
    <article
      className={`rounded-xl border px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)] ${toneMeta[entry.tone]}`}
    >
      <div className="flex items-center justify-between gap-4 text-xs uppercase tracking-[0.22em] text-white/[0.55]">
        <span>{entry.timestampLabel}</span>
        <span>{entry.event.replaceAll("_", " ")}</span>
      </div>
      <div className="mt-2 flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold text-white">{entry.title}</p>
          {entry.metadata.map((item) => (
            <span
              key={`${entry.id}-${item}`}
              className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[11px] text-white/[0.60]"
            >
              {item}
            </span>
          ))}
        </div>
        <p className="text-sm text-white/[0.75]">{entry.message}</p>
      </div>
    </article>
  );
}

export function ScrapeLogPanel() {
  const {
    events,
    connectionState,
    reconnectAttempt,
    lastActivityLabel,
    errorMessage,
    clearEvents,
  } = useScrapeEventStream();
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
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
  }, [events.length]);

  return (
    <section className="rounded-[28px] border border-white/10 bg-[#06111d]/90 p-5 text-white shadow-[0_24px_80px_rgba(3,8,20,0.45)] backdrop-blur">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200/[0.70]">
            Live scrape monitor
          </p>
          <h2 className="text-2xl font-semibold tracking-tight">
            Real-time crawler activity
          </h2>
          <p className="max-w-2xl text-sm text-slate-300">
            This panel follows the backend scrape event stream and shows queue,
            retry, failure, and completion updates as they happen.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] ${connectionMeta[connectionState].className}`}
          >
            {connectionMeta[connectionState].label}
          </span>
          <button
            type="button"
            onClick={clearEvents}
            className="rounded-full border border-white/12 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200 transition hover:bg-white/10"
          >
            Clear log
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Reconnect policy
          </p>
          <p className="mt-2 text-lg font-semibold text-white">
            {reconnectAttempt > 0 ? `Attempt ${reconnectAttempt} of 3` : "Standing by"}
          </p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Last activity
          </p>
          <p className="mt-2 text-lg font-semibold text-white">{lastActivityLabel}</p>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
            Stream buffer
          </p>
          <p className="mt-2 text-lg font-semibold text-white">
            {events.length} events in memory
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-[24px] border border-white/10 bg-[#02060c] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
        <div className="mb-4 flex items-center justify-between gap-4 border-b border-white/8 pb-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              Terminal feed
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Errors stay red, completions stay green, and retries stay amber.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-rose-400/90" />
            <span className="h-3 w-3 rounded-full bg-amber-400/90" />
            <span className="h-3 w-3 rounded-full bg-emerald-400/90" />
          </div>
        </div>

        {errorMessage ? (
          <div className="mb-4 rounded-xl border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {errorMessage}
          </div>
        ) : null}

        <div className="flex max-h-[32rem] flex-col gap-3 overflow-y-auto pr-1 font-mono">
          {events.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-10 text-center">
              <p className="text-sm text-slate-300">Waiting for live scrape events.</p>
              <p className="mt-2 text-xs uppercase tracking-[0.24em] text-slate-500">
                The first queued or running job will appear here.
              </p>
            </div>
          ) : (
            events.map((entry) => <LogRow key={entry.id} entry={entry} />)
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </section>
  );
}
