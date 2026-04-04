import type { FpsMetrics } from "@/components/map/mapFpsTracker";
import {
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
  showBenchmark?: boolean;
};

const LAYER_OPTIONS: Array<{ value: MapLayerMode; label: string }> = [
  { value: "markers", label: "Markerlar" },
  { value: "heatmap", label: "Yoğunluk" },
  { value: "combined", label: "Birlikte" },
];

const CATEGORY_DOT_CLASSES: Record<string, string> = {
  trafik_kazasi: "bg-orange-500",
  yangin: "bg-red-500",
  elektrik_kesintisi: "bg-amber-500",
  hirsizlik: "bg-violet-500",
  kulturel_etkinlik: "bg-sky-500",
};

export default function MapLayerToggle({
  layerMode,
  onLayerModeChange,
  onRunBenchmark,
  benchmarkRunning,
  benchmarkMetrics,
  pointCount,
  benchmarkPointCount,
  showBenchmark = false,
}: MapLayerToggleProps) {
  const benchmarkPassed =
    benchmarkMetrics !== undefined && benchmarkMetrics.averageFps >= 60;

  return (
    <div className="absolute left-3 top-3 z-10 flex max-w-[320px] flex-col gap-3 rounded-2xl border border-border/80 bg-card/90 p-3 shadow-xl backdrop-blur">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
          Harita Katmanları
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {pointCount} haber noktası aktif görünümde.
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
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <div className="rounded-xl border border-border bg-secondary/50 px-3 py-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Renk Lejantı
        </p>
        <div className="mt-2 grid gap-2">
          {CATEGORY_LEGEND.map((item) => {
            const colorClass = CATEGORY_DOT_CLASSES[item.key] ?? "bg-slate-500";

            return (
              <div key={item.key} className="flex items-center gap-2 text-xs text-card-foreground">
                <span
                  className={`h-3 w-3 rounded-full border border-white/80 shadow-sm ${colorClass}`}
                />
                <span>{item.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {showBenchmark ? (
        <div className="rounded-xl border border-border bg-secondary/50 px-3 py-2">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                QA Benchmark
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {benchmarkPointCount} nokta ile ortalama ve low-1% FPS ölçümü.
                {pointCount === 0 ? " Veri yoksa sentetik benchmark kullanılır." : ""}
              </p>
            </div>
            <button
              type="button"
              onClick={onRunBenchmark}
              disabled={benchmarkRunning || benchmarkPointCount === 0}
              className="rounded-full bg-card-foreground px-3 py-1.5 text-xs font-semibold text-card transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {benchmarkRunning ? "Ölçülüyor..." : "Çalıştır"}
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
                  ? "60 FPS hedefi karşılandı."
                  : "60 FPS hedefi henüz karşılanmadı."}
              </div>

              <div className="mt-2 grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-card px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Ortalama FPS
                  </p>
                  <p className="mt-1 text-lg font-bold text-card-foreground">
                    {benchmarkMetrics.averageFps}
                  </p>
                </div>
                <div className="rounded-lg bg-card px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Low 1%
                  </p>
                  <p className="mt-1 text-lg font-bold text-card-foreground">
                    {benchmarkMetrics.low1PctFps}
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
