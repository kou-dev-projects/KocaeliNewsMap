import type { FpsMetrics } from "@/components/map/mapFpsTracker";
import {
  CATEGORY_COLORS,
  CATEGORY_LEGEND,
  type MapLayerMode,
} from "@/components/map/mapLayerUtils";

type MapLayerToggleProps = {
  layerMode: MapLayerMode;
  onLayerModeChange: (nextMode: MapLayerMode) => void;
  onRunBenchmark: () => void;
  benchmarkRunning: boolean;
  benchmarkMetrics?: FpsMetrics;
  pointCount: number;
  benchmarkPointCount: number;
};

const LAYER_OPTIONS: Array<{ value: MapLayerMode; label: string }> = [
  { value: "markers", label: "Markerlar" },
  { value: "heatmap", label: "Yogunluk" },
  { value: "combined", label: "Birlikte" },
];

export default function MapLayerToggle({
  layerMode,
  onLayerModeChange,
  onRunBenchmark,
  benchmarkRunning,
  benchmarkMetrics,
  pointCount,
  benchmarkPointCount,
}: MapLayerToggleProps) {
  const benchmarkPassed =
    benchmarkMetrics !== undefined && benchmarkMetrics.averageFps >= 60;

  return (
    <div className="absolute left-3 top-3 z-10 flex max-w-[320px] flex-col gap-3 rounded-2xl border border-slate-200 bg-white/92 p-3 shadow-xl backdrop-blur">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-700">
          Deck Katmanlari
        </p>
        <p className="mt-1 text-xs text-slate-500">
          {pointCount} nokta aktif veri setinde gosteriliyor.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {LAYER_OPTIONS.map((option) => {
          const selected = option.value === layerMode;

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onLayerModeChange(option.value)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                selected
                  ? "bg-sky-700 text-white shadow-sm"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          Renk Lejandi
        </p>
        <div className="mt-2 grid gap-2">
          {CATEGORY_LEGEND.map((item) => {
            const color = CATEGORY_COLORS[item.key];

            return (
              <div key={item.key} className="flex items-center gap-2 text-xs text-slate-700">
                <span
                  className="h-3 w-3 rounded-full border border-white/80 shadow-sm"
                  style={{
                    backgroundColor: `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3] / 255})`,
                  }}
                />
                <span>{item.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              1000+ Profil
            </p>
            <p className="mt-1 text-xs text-slate-600">
              {benchmarkPointCount} nokta ile ortalama ve low-1% FPS olcumu.
              {pointCount === 0 ? " Veri yoksa sentetik benchmark kullanilir." : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onRunBenchmark}
            disabled={benchmarkRunning || benchmarkPointCount === 0}
            className="rounded-full bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {benchmarkRunning ? "Olculuyor..." : "Calistir"}
          </button>
        </div>

        {benchmarkMetrics ? (
          <div className="mt-3">
            <div
              className={`rounded-lg border px-3 py-2 text-xs font-semibold ${
                benchmarkPassed
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
            >
              {benchmarkPassed
                ? "60 FPS hedefi karsilandi."
                : "60 FPS hedefi henuz karsilanmadi."}
            </div>

            <div className="mt-2 grid grid-cols-2 gap-2">
              <div className="rounded-lg bg-white px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Ortalama FPS
                </p>
                <p className="mt-1 text-lg font-bold text-slate-900">
                  {benchmarkMetrics.averageFps}
                </p>
              </div>
              <div className="rounded-lg bg-white px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Low 1%
                </p>
                <p className="mt-1 text-lg font-bold text-slate-900">
                  {benchmarkMetrics.low1PctFps}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
