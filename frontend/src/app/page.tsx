import { ScrapeLogPanel } from "@/components/ScrapeLogPanel";

const overviewCards = [
  {
    label: "Primary goal",
    value: "Live scrape visibility",
    detail: "Track queue, retries, failures, and completions in one place.",
  },
  {
    label: "Transport",
    value: "Fetch-based SSE",
    detail: "Uses a resumable stream client instead of browser-only EventSource.",
  },
  {
    label: "Reconnect policy",
    value: "3 attempts",
    detail: "Automatic reconnect with backoff keeps the monitor resilient.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen text-slate-50">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
        <header className="rounded-[32px] border border-white/10 bg-white/[0.06] p-6 shadow-[0_20px_70px_rgba(2,8,20,0.35)] backdrop-blur">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-cyan-200/[0.70]">
                PULSE operations
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Live scrape logging for the Kocaeli news pipeline
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                This branch focuses on one thing only: making crawler activity
                observable in real time. The map work stays separate; this view
                is the operations console.
              </p>
            </div>

            <div className="rounded-[24px] border border-cyan-400/20 bg-cyan-400/[0.08] px-5 py-4 text-sm text-cyan-50">
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-cyan-200/[0.70]">
                Issue focus
              </p>
              <p className="mt-2 font-medium">S2-B2 - SSE live scraping log</p>
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-3">
          {overviewCards.map((card) => (
            <article
              key={card.label}
              className="rounded-[24px] border border-white/10 bg-white/5 p-5 shadow-[0_14px_40px_rgba(2,8,20,0.2)]"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
                {card.label}
              </p>
              <p className="mt-3 text-2xl font-semibold text-white">
                {card.value}
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                {card.detail}
              </p>
            </article>
          ))}
        </section>

        <ScrapeLogPanel />

        <section className="rounded-[28px] border border-dashed border-white/12 bg-black/10 p-6 text-slate-300">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
            Next integration step
          </p>
          <h2 className="mt-2 text-xl font-semibold text-white">
            Map and marker work stays on the DEV-A branch
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-7">
            This page intentionally avoids pulling map features into the scrape
            log issue. Once the log panel is merged, the map branch can consume
            the same backend stream without changing the crawler workflow.
          </p>
        </section>
      </main>
    </div>
  );
}
