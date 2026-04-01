import MapView from "@/components/map/MapView";

export default function Home() {
  return (
    <div className="h-dvh overflow-hidden bg-slate-100 text-slate-900">
      <main className="mx-auto flex h-full w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <header className="rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
            PULSE
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Kocaeli Haber Haritası
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            İlçe ve mahalle odaklı haberleri tek akışta izlemek için kontrol
            paneli.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Toplam Haber
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Aktif Kaynak
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
          <article className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">Son Crawl</h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
        </section>

        <section className="flex min-h-0 flex-1 flex-col rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Harita Görünümü</h2>
          <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200">
            <MapView className="h-full w-full" />
          </div>
        </section>
      </main>
    </div>
  );
}
