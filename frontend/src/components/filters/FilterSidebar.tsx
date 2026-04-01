export default function FilterSidebar() {
  return (
    <aside className="rounded-2xl bg-white p-6 shadow-sm lg:sticky lg:top-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
            Filtreler
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
            Harita Kontrolleri
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Haritadaki haberleri tur, ilce ve tarih araligina gore daraltmak
            icin filtreleri kullanin.
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-5">
        <section className="rounded-xl border border-slate-200 p-4">
          <label
            htmlFor="category"
            className="text-sm font-semibold text-slate-800"
          >
            Haber Turu
          </label>
          <select
            id="category"
            className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-500"
            defaultValue=""
          >
            <option value="">Tum kategoriler</option>
            <option value="trafik_kazasi">Trafik Kazasi</option>
            <option value="yangin">Yangin</option>
            <option value="elektrik_kesintisi">Elektrik Kesintisi</option>
            <option value="hirsizlik">Hirsizlik</option>
            <option value="kulturel_etkinlik">Kulturel Etkinlik</option>
          </select>
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <label
            htmlFor="district"
            className="text-sm font-semibold text-slate-800"
          >
            Ilce
          </label>
          <select
            id="district"
            className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-500"
            defaultValue=""
          >
            <option value="">Tum ilceler</option>
            <option value="izmit">Izmit</option>
            <option value="gebze">Gebze</option>
            <option value="darica">Darica</option>
            <option value="golcuk">Golcuk</option>
            <option value="hereke">Hereke</option>
            <option value="korfez">Korfez</option>
            <option value="kartepe">Kartepe</option>
            <option value="basiskele">Basiskele</option>
            <option value="cayirova">Cayirova</option>
            <option value="dilovasi">Dilovasi</option>
            <option value="kandira">Kandira</option>
            <option value="karamursel">Karamursel</option>
            <option value="derince">Derince</option>
          </select>
        </section>

        <section className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm font-semibold text-slate-800">Tarih Araligi</p>

          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <div>
              <label
                htmlFor="date-from"
                className="text-xs font-medium uppercase tracking-wide text-slate-500"
              >
                Baslangic
              </label>
              <input
                id="date-from"
                type="date"
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-500"
              />
            </div>

            <div>
              <label
                htmlFor="date-to"
                className="text-xs font-medium uppercase tracking-wide text-slate-500"
              >
                Bitis
              </label>
              <input
                id="date-to"
                type="date"
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-500"
              />
            </div>
          </div>
        </section>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row lg:flex-col xl:flex-row">
        <button className="inline-flex items-center justify-center rounded-lg bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-800">
          Uygula
        </button>
        <button className="inline-flex items-center justify-center rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
          Temizle
        </button>
      </div>
    </aside>
  );
}
