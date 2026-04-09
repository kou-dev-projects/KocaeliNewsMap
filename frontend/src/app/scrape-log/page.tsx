import type { Metadata } from "next";

import { ScrapeLogPanel } from "@/components/ScrapeLogPanel";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const overviewCards = [
  {
    label: "Ana hedef",
    value: "Canlı scrape görünürlüğü",
    detail: "Kuyruk, yeniden denemeler, hatalar ve tamamlanan işler tek yerde izlenir.",
  },
  {
    label: "Taşıma katmanı",
    value: "Fetch tabanlı SSE",
    detail: "Tarayıcıya özel EventSource yerine devam edebilen bir akış istemcisi kullanılır.",
  },
  {
    label: "Yeniden bağlanma politikası",
    value: "3 deneme",
    detail: "Gecikmeli otomatik yeniden bağlanma izleme ekranını dayanıklı tutar.",
  },
];

export const metadata: Metadata = {
  title: "PULSE | Canlı Scrape İzleyici",
  description: "PULSE için gerçek zamanlı scrape etkinliği ve operasyon panosu.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function ScrapeLogPage() {
  return (
    <div
      className="min-h-screen text-slate-50"
      style={{
        backgroundImage:
          "radial-gradient(circle at top, rgba(74, 222, 128, 0.08), transparent 28%), radial-gradient(circle at 20% 20%, rgba(56, 189, 248, 0.14), transparent 30%), linear-gradient(180deg, #06101a 0%, #09131f 45%, #030812 100%)",
      }}
    >
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8">
        <header className="rounded-[32px] border border-white/10 bg-white/[0.06] p-6 shadow-[0_20px_70px_rgba(2,8,20,0.35)] backdrop-blur">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.34em] text-cyan-200/[0.70]">
                PULSE operasyonları
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Kocaeli haber hattı için canlı scrape günlüğü
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                Bu sayfa tek bir işe odaklanır: tarayıcı etkinliğini gerçek
                zamanlı olarak görünür kılmak. Harita akışı ayrı kalır; bu
                görünüm operasyon konsoludur.
              </p>
            </div>

            <div className="rounded-[24px] border border-cyan-400/20 bg-cyan-400/[0.08] px-5 py-4 text-sm text-cyan-50">
              <p className="text-xs font-semibold uppercase tracking-[0.26em] text-cyan-200/[0.70]">
                Odak
              </p>
              <p className="mt-2 font-medium">S2-B2 - SSE canlı scrape günlüğü</p>
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
      </main>
    </div>
  );
}
