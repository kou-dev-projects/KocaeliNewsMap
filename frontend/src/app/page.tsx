import MapView from "@/components/map/MapView";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 lg:h-dvh lg:overflow-hidden">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:px-5 lg:h-full lg:max-w-[1500px] lg:overflow-hidden lg:px-6">
        <header className="rounded-2xl bg-white px-5 py-4 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
            PULSE
          </p>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
            Kocaeli Haber Haritasi
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Ilce ve mahalle odakli haberleri tek akista izlemek icin kontrol
            paneli.
          </p>
        </header>

        <section className="grid grid-cols-3 gap-3">
          <article className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Toplam Haber
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
          <article className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Aktif Kaynak
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
          <article className="rounded-xl bg-white px-4 py-3 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">
              Son Tarama
            </h2>
            <p className="mt-2 text-2xl font-bold">--</p>
          </article>
        </section>

        <section className="flex min-h-0 flex-1 flex-col rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Harita Gorunumu</h2>
          <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded-xl border border-slate-200">
            <MapView className="h-full w-full" />
          </div>
        </section>
      </main>
    </div>
  );
}
