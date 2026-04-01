type MarkerTooltip = {
  type: "marker";
  x: number;
  y: number;
  title: string;
  dateLabel: string;
};

type HexTooltip = {
  type: "hex";
  x: number;
  y: number;
  count: number;
};

export type MapTooltipState = MarkerTooltip | HexTooltip | null;

type MapTooltipProps = {
  tooltip: MapTooltipState;
};

export default function MapTooltip({ tooltip }: MapTooltipProps) {
  if (!tooltip) {
    return null;
  }

  const style = {
    left: tooltip.x,
    top: tooltip.y,
  };

  return (
    <div
      className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+14px)]"
      style={style}
    >
      <div className="min-w-[220px] rounded-xl border border-slate-800/80 bg-slate-950/95 px-3 py-2 text-white shadow-2xl backdrop-blur">
        {tooltip.type === "marker" ? (
          <>
            <p className="text-sm font-semibold leading-5">{tooltip.title}</p>
            <p className="mt-1 text-xs text-slate-300">{tooltip.dateLabel}</p>
          </>
        ) : (
          <>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">
              Yogunluk
            </p>
            <p className="mt-1 text-sm font-semibold">
              {tooltip.count} haber
            </p>
          </>
        )}
      </div>
    </div>
  );
}
