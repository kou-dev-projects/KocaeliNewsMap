type FilterState = {
  category: string;
  district: string;
  dateFrom: string;
  dateTo: string;
};

type FilterSidebarProps = {
  values: FilterState;
  onChange: (field: keyof FilterState, value: string) => void;
  onApply: () => void;
  onReset: () => void;
  onRefresh: () => void;
  refreshDisabled?: boolean;
  refreshLabel?: string;
  scrapeStatusMessage?: string;
  scrapeStatusTone?: "info" | "success" | "warning" | "error";
};

export type { FilterState };

export default function FilterSidebar({
  values,
  onChange,
  onApply,
  onReset,
  onRefresh,
  refreshDisabled = false,
  refreshLabel = "Yenile",
  scrapeStatusMessage,
  scrapeStatusTone = "info",
}: FilterSidebarProps) {
  const statusToneClasses = {
    info: "border-sky-200 bg-sky-50 text-sky-800",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    error: "border-rose-200 bg-rose-50 text-rose-800",
  } as const;

  return (
    <aside className="rounded-2xl bg-white p-4 shadow-sm lg:sticky lg:top-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-700">
            Filtreler
          </p>
          <h2 className="mt-2 text-xl font-bold tracking-tight text-slate-900">
            Harita Kontrolleri
          </h2>
          <p className="mt-2 text-xs leading-5 text-slate-600">
            Haritadaki haberleri tur, ilce ve tarih araligina gore daraltmak
            icin filtreleri kullanin.
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <section className="rounded-xl border border-slate-200 p-3">
          <label
            htmlFor="category"
            className="text-sm font-semibold text-slate-800"
          >
            Haber Turu
          </label>
          <select
            id="category"
            className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-500"
            value={values.category}
            onChange={(event) => onChange("category", event.target.value)}
          >
            <option value="">Tum kategoriler</option>
            <option value="trafik_kazasi">Trafik Kazasi</option>
            <option value="yangin">Yangin</option>
            <option value="elektrik_kesintisi">Elektrik Kesintisi</option>
            <option value="hirsizlik">Hirsizlik</option>
            <option value="kulturel_etkinlik">Kulturel Etkinlik</option>
          </select>
        </section>

        <section className="rounded-xl border border-slate-200 p-3">
          <label
            htmlFor="district"
            className="text-sm font-semibold text-slate-800"
          >
            Ilce
          </label>
          <select
            id="district"
            className="mt-3 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-sky-500"
            value={values.district}
            onChange={(event) => onChange("district", event.target.value)}
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

        <section className="rounded-xl border border-slate-200 p-3">
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
                value={values.dateFrom}
                onChange={(event) => onChange("dateFrom", event.target.value)}
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
                value={values.dateTo}
                onChange={(event) => onChange("dateTo", event.target.value)}
              />
            </div>
          </div>
        </section>
      </div>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row lg:flex-col">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-lg bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-800"
          onClick={onApply}
        >
          Uygula
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          onClick={onReset}
        >
          Temizle
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-lg border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm font-semibold text-sky-800 transition hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={onRefresh}
          disabled={refreshDisabled}
        >
          {refreshLabel}
        </button>
      </div>

      {scrapeStatusMessage ? (
        <section
          className={`mt-4 rounded-xl border px-3 py-3 text-sm ${statusToneClasses[scrapeStatusTone]}`}
        >
          {scrapeStatusMessage}
        </section>
      ) : null}
    </aside>
  );
}
