import { useEffect, useRef } from "react";

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
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = tooltipRef.current;
    if (!node || !tooltip) {
      return;
    }

    node.style.left = `${tooltip.x}px`;
    node.style.top = `${tooltip.y}px`;
  }, [tooltip]);

  if (!tooltip) {
    return null;
  }

  return (
    <div
      ref={tooltipRef}
      className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+14px)]"
    >
      <div className="min-w-[220px] rounded-xl border border-border/80 bg-card/95 px-3 py-2 text-card-foreground shadow-2xl backdrop-blur">
        {tooltip.type === "marker" ? (
          <>
            <p className="text-sm font-semibold leading-5">{tooltip.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{tooltip.dateLabel}</p>
          </>
        ) : (
          <>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              Yoğunluk
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
