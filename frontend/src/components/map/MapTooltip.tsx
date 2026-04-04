import { createPortal } from "react-dom";
import {
  CalendarDays,
  Car,
  ChevronRight,
  Flame,
  Globe2,
  Music2,
  Star,
  VenetianMask,
  Zap,
  type LucideIcon,
} from "lucide-react";

type MarkerTooltip = {
  type: "marker";
  x: number;
  y: number;
  title: string;
  dateLabel: string;
  sourceLabel: string;
  url: string;
  category?: string | null;
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
  onMarkerTooltipEnter?: () => void;
  onMarkerTooltipLeave?: () => void;
};

type MarkerTooltipVisual = {
  icon: LucideIcon;
  accentClass: string;
  tintClass: string;
};

const DEFAULT_MARKER_VISUAL: MarkerTooltipVisual = {
  icon: Star,
  accentClass: "text-sky-600",
  tintClass: "bg-sky-500/12",
};

const MARKER_VISUALS: Record<string, MarkerTooltipVisual> = {
  trafik_kazasi: {
    icon: Car,
    accentClass: "text-amber-600",
    tintClass: "bg-amber-500/12",
  },
  yangin: {
    icon: Flame,
    accentClass: "text-red-600",
    tintClass: "bg-red-500/12",
  },
  elektrik_kesintisi: {
    icon: Zap,
    accentClass: "text-yellow-600",
    tintClass: "bg-yellow-500/12",
  },
  hirsizlik: {
    icon: VenetianMask,
    accentClass: "text-violet-600",
    tintClass: "bg-violet-500/12",
  },
  kulturel_etkinlik: {
    icon: Music2,
    accentClass: "text-emerald-600",
    tintClass: "bg-emerald-500/12",
  },
  unknown: DEFAULT_MARKER_VISUAL,
};

function getMarkerTooltipVisual(category?: string | null): MarkerTooltipVisual {
  if (!category) {
    return DEFAULT_MARKER_VISUAL;
  }

  return MARKER_VISUALS[category] ?? DEFAULT_MARKER_VISUAL;
}

export default function MapTooltip({
  tooltip,
  onMarkerTooltipEnter,
  onMarkerTooltipLeave,
}: MapTooltipProps) {
  if (!tooltip) {
    return null;
  }

  if (tooltip.type === "marker") {
    const visual = getMarkerTooltipVisual(tooltip.category);
    const Icon = visual.icon;

    if (typeof document === "undefined") {
      return null;
    }

    return createPortal(
      <div
        className="pointer-events-none fixed left-0 top-0 z-[1000]"
        style={{ transform: `translate(${tooltip.x}px, ${tooltip.y}px)` }}
      >
        <div
          className="-translate-x-[calc(100%+18px)] -translate-y-[calc(100%+24px)]"
          onMouseEnter={onMarkerTooltipEnter}
          onMouseLeave={onMarkerTooltipLeave}
        >
          <div className="pointer-events-auto relative min-w-[284px] max-w-[300px] rounded-[24px] border border-border/80 bg-card/98 p-3 text-card-foreground shadow-[0_28px_90px_rgba(15,23,42,0.24)] backdrop-blur-xl">
            <div className="flex gap-3">
              <div
                className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${visual.tintClass} ${visual.accentClass}`}
              >
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="line-clamp-2 text-[15px] font-bold leading-5 text-card-foreground">
                  {tooltip.title}
                </p>
                <div className="mt-2 space-y-1.5 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                    <span>{tooltip.dateLabel}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Globe2 className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{tooltip.sourceLabel}</span>
                  </div>
                </div>
              </div>
            </div>

            <a
              href={tooltip.url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-primary to-blue-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:brightness-105"
            >
              Habere Git
              <ChevronRight className="ml-1 h-4 w-4" />
            </a>

            <svg
              aria-hidden="true"
              viewBox="0 0 34 28"
              className="pointer-events-none absolute -bottom-[24px] -right-[18px] h-7 w-[34px] text-card drop-shadow-[0_12px_18px_rgba(15,23,42,0.14)]"
            >
              <path
                d="M2 2c8 1.2 13.8 4.7 18.5 10.8L32 26c-7.5-4.2-13.7-6.6-21.8-7.8C6.8 17.7 4 16 2.4 13.5 1 11.2 1.2 8 2 2Z"
                fill="currentColor"
              />
            </svg>
          </div>
        </div>
      </div>,
      document.body,
    );
  }

  return (
    <div
      className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+14px)]"
      style={{
        left: `${tooltip.x}px`,
        top: `${tooltip.y}px`,
      }}
    >
      <div className="min-w-[220px] rounded-xl border border-border/80 bg-card/95 px-3 py-2 text-card-foreground shadow-2xl backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
          Yogunluk
        </p>
        <p className="mt-1 text-sm font-semibold">
          {tooltip.count} haber
        </p>
      </div>
    </div>
  );
}
