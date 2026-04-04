"use client";

import { useEffect, type CSSProperties } from "react";
import { createRoot, type Root } from "react-dom/client";
import {
  Car,
  Flame,
  Music2,
  Star,
  VenetianMask,
  Zap,
  type LucideIcon,
} from "lucide-react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";

import type { NewsMapItem } from "@/components/map/MapView";
import type { MapTooltipState } from "@/components/map/MapTooltip";
import type { DeckNewsPoint, MapLayerMode } from "@/components/map/mapLayerUtils";

type TooltipHoverHandlers = {
  hold: () => void;
  release: () => void;
};

type MapDomMarkerLayerProps = {
  map: MapLibreMap | null;
  points: DeckNewsPoint[];
  layerMode: MapLayerMode;
  onMarkerSelect?: (item: NewsMapItem) => void;
  onTooltipChange: (tooltip: MapTooltipState) => void;
  registerTooltipHoverHandlers?: (handlers: TooltipHoverHandlers) => void;
};

type MarkerVisual = {
  icon: LucideIcon;
  shape: MarkerShapeId;
  gradientFrom: string;
  gradientTo: string;
  glow: string;
  animationClass: string;
};

type MarkerShapeId = "pin" | "shield" | "badge" | "ticket" | "crest" | "starpin";

type MarkerShapeDefinition = {
  bodyPath: string;
  highlightPath: string;
  centerX: number;
  centerY: number;
  iconScale: number;
  haloWidth: number;
  haloHeight: number;
  haloTop: number;
};

type MarkerRegistration = {
  marker: maplibregl.Marker;
  root: Root;
  element: HTMLButtonElement;
  point: DeckNewsPoint;
  currentOffset: [number, number];
  cleanup: () => void;
};

const DEFAULT_VISUAL: MarkerVisual = {
  icon: Star,
  shape: "starpin",
  gradientFrom: "#3b82f6",
  gradientTo: "#1d4ed8",
  glow: "59 130 246",
  animationClass: "animate-marker-drop",
};

const MARKER_SHAPES: Record<MarkerShapeId, MarkerShapeDefinition> = {
  pin: {
    bodyPath:
      "M32 4C18.2 4 7 15 7 28.8c0 18.5 20.3 37.3 23.2 39.9a2.6 2.6 0 0 0 3.6 0C36.7 66.1 57 47.3 57 28.8 57 15 45.8 4 32 4Z",
    highlightPath:
      "M32 10c-10.3 0-18.6 8.3-18.6 18.5 0 4.4 1.8 9.2 4.7 14.1C13.9 38 11.6 33.1 11.6 28c0-10.9 8.8-19.6 19.6-19.6 8.1 0 15 4.8 18.1 11.8C46.4 14 39.8 10 32 10Z",
    centerX: 32,
    centerY: 28,
    iconScale: 0.34,
    haloWidth: 0.92,
    haloHeight: 0.7,
    haloTop: 0.08,
  },
  shield: {
    bodyPath:
      "M18 6h28c7.7 0 14 6.3 14 14v13c0 15.5-10.9 27.6-25.6 39.8a3.8 3.8 0 0 1-4.8 0C15 60.6 4 48.5 4 33V20C4 12.3 10.3 6 18 6Z",
    highlightPath:
      "M19 12h26c4.8 0 8.7 3.9 8.7 8.7v7.1c-4.7-5.5-11.7-8.8-19.4-8.8-8.9 0-16.9 4.4-21.8 11.1v-9.4C13.2 15.9 14.8 12 19 12Z",
    centerX: 32,
    centerY: 31,
    iconScale: 0.33,
    haloWidth: 1.04,
    haloHeight: 0.58,
    haloTop: 0.11,
  },
  badge: {
    bodyPath:
      "M32 6c14.4 0 26 11.6 26 26 0 12.2-8.4 22.4-19.8 25.2L32 78l-6.2-20.8C14.4 54.4 6 44.2 6 32 6 17.6 17.6 6 32 6Z",
    highlightPath:
      "M32 11c-10.5 0-19.1 8.6-19.1 19.1 0 3.1.8 6.1 2.1 8.8-1.9-3.2-3-6.9-3-10.9C12 17 21 8 32 8c7.7 0 14.5 4.3 17.8 10.7C46.5 13.9 39.7 11 32 11Z",
    centerX: 32,
    centerY: 30,
    iconScale: 0.33,
    haloWidth: 0.98,
    haloHeight: 0.62,
    haloTop: 0.11,
  },
  ticket: {
    bodyPath:
      "M16 8h32c7.7 0 14 6.3 14 14v18c0 7.7-6.3 14-14 14H39L32 79 25 54H16C8.3 54 2 47.7 2 40V22C2 14.3 8.3 8 16 8Z",
    highlightPath:
      "M17.5 14h28.8c4.5 0 8.2 3.7 8.2 8.2v6.1c-4.8-4.4-11.3-7.1-18.5-7.1-7.8 0-14.9 3.1-20.1 8.3v-7.3c0-4.5 3.7-8.2 8.2-8.2Z",
    centerX: 32,
    centerY: 30,
    iconScale: 0.32,
    haloWidth: 1.02,
    haloHeight: 0.56,
    haloTop: 0.11,
  },
  crest: {
    bodyPath:
      "M18 6h28l10 10v17c0 18.5-11.8 31.5-22.2 40.5a3.4 3.4 0 0 1-3.6 0C19.8 64.5 8 51.5 8 33V16L18 6Z",
    highlightPath:
      "M20 12h24l6 6v6c-4.5-4.9-10.9-7.9-18-7.9-7.7 0-14.7 3.5-19.4 9.2v-7.4l7.4-5.9Z",
    centerX: 32,
    centerY: 30,
    iconScale: 0.32,
    haloWidth: 1,
    haloHeight: 0.6,
    haloTop: 0.11,
  },
  starpin: {
    bodyPath:
      "M18 8h28c8.9 0 16 7.1 16 16v7c0 18.4-12.2 31.7-26.2 42.9a6 6 0 0 1-7.6 0C14.2 62.7 2 49.4 2 31v-7C2 15.1 9.1 8 18 8Z",
    highlightPath:
      "M19 13h26c6 0 10.9 4.9 10.9 10.9v5.4c-5-4.9-11.8-7.9-19.4-7.9-8.7 0-16.3 3.9-21.5 10v-7.5C15 17.9 16.8 13 19 13Z",
    centerX: 32,
    centerY: 31,
    iconScale: 0.31,
    haloWidth: 1.06,
    haloHeight: 0.62,
    haloTop: 0.1,
  },
};

const CATEGORY_VISUALS: Record<string, MarkerVisual> = {
  trafik_kazasi: {
    icon: Car,
    shape: "shield",
    gradientFrom: "#f59e0b",
    gradientTo: "#d97706",
    glow: "245 158 11",
    animationClass: "animate-traffic-drop",
  },
  yangin: {
    icon: Flame,
    shape: "pin",
    gradientFrom: "#ef4444",
    gradientTo: "#dc2626",
    glow: "239 68 68",
    animationClass: "animate-breaking-drop",
  },
  elektrik_kesintisi: {
    icon: Zap,
    shape: "badge",
    gradientFrom: "#eab308",
    gradientTo: "#ca8a04",
    glow: "234 179 8",
    animationClass: "animate-marker-drop",
  },
  hirsizlik: {
    icon: VenetianMask,
    shape: "crest",
    gradientFrom: "#8b5cf6",
    gradientTo: "#7c3aed",
    glow: "139 92 246",
    animationClass: "animate-crime-drop",
  },
  kulturel_etkinlik: {
    icon: Music2,
    shape: "ticket",
    gradientFrom: "#10b981",
    gradientTo: "#059669",
    glow: "16 185 129",
    animationClass: "animate-event-drop",
  },
};

const PIN_VIEWBOX_WIDTH = 64;
const PIN_VIEWBOX_HEIGHT = 84;
const PIN_CENTER_X = 32;
const PIN_CENTER_Y = 28;

function getMarkerVisual(category?: string): MarkerVisual {
  if (!category) {
    return DEFAULT_VISUAL;
  }

  return CATEGORY_VISUALS[category] ?? DEFAULT_VISUAL;
}

function buildFanOffsets(total: number): Array<[number, number]> {
  if (total <= 1) {
    return Array.from({ length: total }, () => [0, 0] as [number, number]);
  }

  if (total === 2) {
    return [
      [-30, -6],
      [30, -6],
    ];
  }

  if (total === 3) {
    return [
      [-34, -10],
      [0, -30],
      [34, -10],
    ];
  }

  const radius = total <= 5 ? 46 : Math.min(78, 44 + (total - 5) * 4);
  const startAngle = (-5 * Math.PI) / 6;
  const endAngle = -Math.PI / 6;

  return Array.from({ length: total }, (_, index) => {
    const t = total === 1 ? 0.5 : index / (total - 1);
    const angle = startAngle + (endAngle - startAngle) * t;

    return [
      Math.round(Math.cos(angle) * radius),
      Math.round(Math.sin(angle) * radius - Math.max(0, total - 4) * 2),
    ] as [number, number];
  });
}

function sameGroupMembers(
  firstGroup: MarkerRegistration[],
  secondGroup: MarkerRegistration[],
) {
  return (
    firstGroup.length === secondGroup.length &&
    firstGroup.every((registration) => secondGroup.includes(registration))
  );
}

function sortGroupForSpread(group: MarkerRegistration[]) {
  return [...group].sort((left, right) => {
    if (left.point.position[1] !== right.point.position[1]) {
      return right.point.position[1] - left.point.position[1];
    }

    if (left.point.position[0] !== right.point.position[0]) {
      return left.point.position[0] - right.point.position[0];
    }

    return (
      left.point.title.localeCompare(right.point.title, "tr") ||
      left.point.id.localeCompare(right.point.id, "tr")
    );
  });
}

function getTooltipAnchorFromElement(element: HTMLElement) {
  const rect = element.getBoundingClientRect();

  return {
    x: Math.round(rect.left + rect.width * (PIN_CENTER_X / PIN_VIEWBOX_WIDTH)),
    y: Math.round(rect.top + rect.height * (PIN_CENTER_Y / PIN_VIEWBOX_HEIGHT)),
  };
}

function MarkerGlyph({
  pointId,
  category,
  radius,
  title,
}: {
  pointId: string;
  category: string;
  radius: number;
  title: string;
}) {
  const visual = getMarkerVisual(category);
  const shape = MARKER_SHAPES[visual.shape];
  const Icon = visual.icon;
  const size = Math.max(48, Math.min(64, Math.round(radius * 3.2)));
  const gradientId = `pulse-marker-gradient-${pointId}`;
  const highlightId = `pulse-marker-highlight-${pointId}`;
  const style = {
    "--pulse-marker-glow": visual.glow,
    "--pulse-marker-size": `${size}px`,
    "--pulse-marker-center-x": `${(shape.centerX / PIN_VIEWBOX_WIDTH) * 100}%`,
    "--pulse-marker-center-y": `${(shape.centerY / PIN_VIEWBOX_HEIGHT) * 100}%`,
    "--pulse-marker-icon-size": `${Math.round(size * shape.iconScale)}px`,
    "--pulse-marker-halo-width": `${shape.haloWidth * 100}%`,
    "--pulse-marker-halo-height": `${shape.haloHeight * 100}%`,
    "--pulse-marker-halo-top": `${shape.haloTop * 100}%`,
  } as CSSProperties;

  return (
    <div
      className={`pulse-map-marker pulse-map-marker--${visual.shape} ${visual.animationClass}`}
      style={style}
      aria-label={title}
    >
      <span className="pulse-map-marker__halo" />
      <svg
        viewBox="0 0 64 84"
        className="pulse-map-marker__svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient
            id={gradientId}
            x1="16"
            y1="8"
            x2="48"
            y2="74"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor={visual.gradientFrom} />
            <stop offset="100%" stopColor={visual.gradientTo} />
          </linearGradient>
          <linearGradient
            id={highlightId}
            x1="22"
            y1="10"
            x2="38"
            y2="40"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="rgba(255,255,255,0.7)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        <path
          d={shape.bodyPath}
          fill={`url(#${gradientId})`}
          stroke="rgba(255,255,255,0.88)"
          strokeWidth="1.8"
        />
        <path
          d={shape.highlightPath}
          fill={`url(#${highlightId})`}
          opacity="0.55"
        />
      </svg>
      <span className="pulse-map-marker__icon">
        <Icon
          className="pulse-map-marker__icon-svg"
          strokeWidth={2.35}
          absoluteStrokeWidth
        />
      </span>
    </div>
  );
}

export default function MapDomMarkerLayer({
  map,
  points,
  layerMode,
  onMarkerSelect,
  onTooltipChange,
  registerTooltipHoverHandlers,
}: MapDomMarkerLayerProps) {
  useEffect(() => {
    if (!map || (layerMode !== "markers" && layerMode !== "combined")) {
      onTooltipChange(null);
      registerTooltipHoverHandlers?.({
        hold: () => {},
        release: () => {},
      });
      return;
    }

    const registrations: MarkerRegistration[] = [];
    let activeGroup: MarkerRegistration[] = [];
    let activeRegistration: MarkerRegistration | null = null;
    let collapseTimer: ReturnType<typeof setTimeout> | null = null;
    let collapseSuppressedUntil = 0;

    const clearCollapseTimer = () => {
      if (!collapseTimer) {
        return;
      }

      window.clearTimeout(collapseTimer);
      collapseTimer = null;
    };

    const setRegistrationVisualState = (
      registration: MarkerRegistration,
      offset: [number, number],
      options: { active: boolean; spread: boolean },
    ) => {
      registration.currentOffset = offset;
      registration.marker.setOffset(offset);
      registration.element.dataset.active = options.active ? "true" : "false";
      registration.element.dataset.spread = options.spread ? "true" : "false";
      registration.element.style.zIndex = options.active ? "80" : options.spread ? "36" : "10";
    };

    const syncTooltipWithRegistration = (registration: MarkerRegistration | null) => {
      if (!registration) {
        onTooltipChange(null);
        return;
      }

      const anchor = getTooltipAnchorFromElement(registration.element);
      onTooltipChange({
        type: "marker",
        x: anchor.x,
        y: anchor.y,
        title: registration.point.title,
        dateLabel: registration.point.publishedLabel,
        sourceLabel:
          registration.point.sourceItem.source_name ||
          registration.point.sourceItem.source_domain ||
          "Bilinmeyen kaynak",
        url: registration.point.sourceItem.url,
        category: registration.point.sourceItem.category ?? registration.point.category,
      });
    };

    const collapseGroup = (group: MarkerRegistration[]) => {
      if (group.length === 0) {
        return;
      }

      group.forEach((registration) => {
        setRegistrationVisualState(registration, [0, 0], {
          active: false,
          spread: false,
        });
      });
    };

    const findOverlapGroup = (registration: MarkerRegistration) => {
      const activePixel = map.project(registration.point.position);
      const threshold = 56;

      return sortGroupForSpread(
        registrations.filter((candidate) => {
        const candidatePixel = map.project(candidate.point.position);
        return (
          Math.hypot(candidatePixel.x - activePixel.x, candidatePixel.y - activePixel.y) <=
          threshold
        );
        }),
      );
    };

    const activateRegistration = (registration: MarkerRegistration) => {
      clearCollapseTimer();

      const group = findOverlapGroup(registration);
      const isSameGroup = sameGroupMembers(activeGroup, group);

      if (activeGroup.length > 0 && !isSameGroup) {
        collapseGroup(activeGroup);
      }

      const offsets = buildFanOffsets(group.length);

      group.forEach((groupRegistration, index) => {
        setRegistrationVisualState(groupRegistration, offsets[index] ?? [0, 0], {
          active: groupRegistration === registration,
          spread: group.length > 1,
        });
      });

      activeGroup = group;
      activeRegistration = registration;
      collapseSuppressedUntil =
        group.length > 1 ? performance.now() + 180 : 0;
      syncTooltipWithRegistration(registration);
    };

    const releaseActiveGroup = () => {
      clearCollapseTimer();
      const group = [...activeGroup];
      const registration = activeRegistration;
      const suppressionDelay = Math.max(0, collapseSuppressedUntil - performance.now());

      collapseTimer = setTimeout(() => {
        collapseGroup(group);
        if (sameGroupMembers(activeGroup, group)) {
          activeGroup = [];
        }
        if (activeRegistration === registration) {
          activeRegistration = null;
          onTooltipChange(null);
        }
      }, suppressionDelay + 420);
    };

    registerTooltipHoverHandlers?.({
      hold: clearCollapseTimer,
      release: releaseActiveGroup,
    });

    const handleMapMotion = () => {
      if (!activeRegistration) {
        return;
      }

      syncTooltipWithRegistration(activeRegistration);
    };

    map.on("move", handleMapMotion);
    map.on("zoom", handleMapMotion);
    map.on("rotate", handleMapMotion);
    map.on("pitch", handleMapMotion);

    for (const point of points) {
      const markerElement = document.createElement("button");
      markerElement.type = "button";
      markerElement.className = "pulse-map-marker-button";
      markerElement.setAttribute("aria-label", point.title);
      markerElement.dataset.active = "false";
      markerElement.dataset.spread = "false";

      const root = createRoot(markerElement);
      root.render(
        <MarkerGlyph
          pointId={point.id}
          category={point.category}
          radius={point.radius}
          title={point.title}
        />,
      );

      const marker = new maplibregl.Marker({
        element: markerElement,
        anchor: "bottom",
        subpixelPositioning: true,
      })
        .setLngLat(point.position)
        .addTo(map);

      const registration: MarkerRegistration = {
        marker,
        root,
        element: markerElement,
        point,
        currentOffset: [0, 0],
        cleanup: () => {},
      };

      const handleMouseEnter = () => {
        activateRegistration(registration);
      };

      const handleMouseLeave = () => {
        releaseActiveGroup();
      };

      const handleFocus = () => {
        activateRegistration(registration);
      };

      const handleBlur = () => {
        releaseActiveGroup();
      };

      const handleClick = () => {
        onMarkerSelect?.(registration.point.sourceItem);
      };

      markerElement.addEventListener("pointerenter", handleMouseEnter);
      markerElement.addEventListener("pointerleave", handleMouseLeave);
      markerElement.addEventListener("focus", handleFocus);
      markerElement.addEventListener("blur", handleBlur);
      markerElement.addEventListener("click", handleClick);

      registration.cleanup = () => {
        markerElement.removeEventListener("pointerenter", handleMouseEnter);
        markerElement.removeEventListener("pointerleave", handleMouseLeave);
        markerElement.removeEventListener("focus", handleFocus);
        markerElement.removeEventListener("blur", handleBlur);
        markerElement.removeEventListener("click", handleClick);
      };

      registrations.push(registration);
    }

    return () => {
      clearCollapseTimer();
      registerTooltipHoverHandlers?.({
        hold: () => {},
        release: () => {},
      });
      onTooltipChange(null);
      map.off("move", handleMapMotion);
      map.off("zoom", handleMapMotion);
      map.off("rotate", handleMapMotion);
      map.off("pitch", handleMapMotion);
      registrations.forEach((registration) => {
        registration.cleanup();
        registration.root.unmount();
        registration.marker.remove();
      });
    };
  }, [
    layerMode,
    map,
    onMarkerSelect,
    onTooltipChange,
    points,
    registerTooltipHoverHandlers,
  ]);

  return null;
}
