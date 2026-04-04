"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import DeckGLOverlay from "@/components/map/DeckGLOverlay";
import MapDomMarkerLayer from "@/components/map/MapDomMarkerLayer";
import MapTooltip, { type MapTooltipState } from "@/components/map/MapTooltip";
import {
  adaptNewsItemsToDeckPoints,
  type DeckNewsPoint,
  type MapLayerMode,
} from "@/components/map/mapLayerUtils";

export type NewsMapItem = {
  id: string;
  title: string;
  summary?: string | null;
  source_name: string;
  source_domain: string;
  url: string;
  published_at_raw?: string | null;
  category?: string | null;
  category_confidence?: number | null;
  district?: string | null;
  geocode_status: string;
  latitude: number;
  longitude: number;
};

export type MapThemeMode = "light" | "dark";
type MapStyleDefinition = string | Record<string, unknown>;

type MapViewProps = {
  className?: string;
  styleUrl?: string;
  themeMode?: MapThemeMode;
  items?: NewsMapItem[];
  onMarkerSelect?: (item: NewsMapItem) => void;
};

const KOCAELI_CENTER: [number, number] = [29.9213, 40.7654];
const INITIAL_ZOOM = 12;
const BUILDING_SOURCE_ID = "openfreemap";
const BUILDING_LAYER_ID = "kocaeli-3d-buildings";

const DEFAULT_STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://tiles.openfreemap.org/styles/liberty";

const FALLBACK_MAP_STYLE: Record<string, unknown> = {
  version: 8,
  name: "pulse-fallback-style",
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: {
        "background-color": "#0f172a",
      },
    },
  ],
};

type DarkMapPalette = {
  background: string;
  land: string;
  water: string;
  waterEdge: string;
  roadMinor: string;
  roadMajor: string;
  roadHighway: string;
  roadHighwayStroke: string;
  boundaries: string;
  parks: string;
  buildings: string;
  extrusions: string;
  labels: string;
  labelsRoad: string;
  labelsPoi: string;
  labelsPark: string;
  labelsWater: string;
  labelHalo: string;
  transit: string;
  transitLine: string;
};

const DARK_MAP_PALETTES: Record<
  "googleBlue" | "steelBlue" | "nightTeal" | "coolSlate",
  DarkMapPalette
> = {
  // Closest baseline to Google dark map.
  googleBlue: {
    background: "#242f3e",
    land: "#1f2a37",
    water: "#17263c",
    waterEdge: "#223a5b",
    roadMinor: "#42576d",
    roadMajor: "#6682a1",
    roadHighway: "#81a7d1",
    roadHighwayStroke: "#314760",
    boundaries: "#415062",
    parks: "#294246",
    buildings: "#304052",
    extrusions: "#3a4f65",
    labels: "#c3ceda",
    labelsRoad: "#a5b9cd",
    labelsPoi: "#8fbdf0",
    labelsPark: "#80a893",
    labelsWater: "#7690a8",
    labelHalo: "rgba(36, 47, 62, 0.92)",
    transit: "#2f3d4f",
    transitLine: "#35578d",
  },
  // Slightly colder and more contrasty roads.
  steelBlue: {
    background: "#202a36",
    land: "#1b2430",
    water: "#142338",
    waterEdge: "#1d3550",
    roadMinor: "#41566d",
    roadMajor: "#6a87a8",
    roadHighway: "#92b8df",
    roadHighwayStroke: "#2f455c",
    boundaries: "#3c4b5d",
    parks: "#253c40",
    buildings: "#2c3a4b",
    extrusions: "#38506a",
    labels: "#ccd6e0",
    labelsRoad: "#adc0d4",
    labelsPoi: "#9dc8f3",
    labelsPark: "#7ea58e",
    labelsWater: "#7890a7",
    labelHalo: "rgba(32, 42, 54, 0.92)",
    transit: "#2c3a4a",
    transitLine: "#39639a",
  },
  // More teal/cyan accents while keeping gray-blue base.
  nightTeal: {
    background: "#1f2b34",
    land: "#1a232e",
    water: "#122432",
    waterEdge: "#1b3b4e",
    roadMinor: "#3f5567",
    roadMajor: "#5f8298",
    roadHighway: "#79b2c9",
    roadHighwayStroke: "#2c4354",
    boundaries: "#394a59",
    parks: "#244246",
    buildings: "#2a3c4a",
    extrusions: "#345062",
    labels: "#bfd1db",
    labelsRoad: "#9fb8c8",
    labelsPoi: "#86c5df",
    labelsPark: "#7cad98",
    labelsWater: "#6f96aa",
    labelHalo: "rgba(31, 43, 52, 0.92)",
    transit: "#2b3d47",
    transitLine: "#2f6c83",
  },
  // Softer blue-gray for lower visual noise.
  coolSlate: {
    background: "#262f3a",
    land: "#232b36",
    water: "#1a2635",
    waterEdge: "#273b54",
    roadMinor: "#4a5d70",
    roadMajor: "#444b51",
    roadHighway: "#5a6774",
    roadHighwayStroke: "#33373b",
    boundaries: "#485767",
    parks: "#2d3f45",
    buildings: "#344252",
    extrusions: "#415466",
    labels: "#c4cfdb",
    labelsRoad: "#b8c4d1",
    labelsPoi: "#72afe8",
    labelsPark: "#4d9564",
    labelsWater: "#8aa2b7",
    labelHalo: "rgba(24, 31, 40, 0.98)",
    transit: "#344351",
    transitLine: "#456e9b",
  },
};

const HIGHWAY_LINE_OPACITY = 0.52;
const MAJOR_LINE_OPACITY = 0.4;
const MINOR_LINE_OPACITY = 0.28;
const BUILDING_FILL_OPACITY = 0.62;
const BUILDING_BOUNDARY_OPACITY = 0.09;
const BOUNDARY_LINE_OPACITY = 0.3;
const ROAD_TEXT_OPACITY = 0.86;
const POI_TEXT_OPACITY = 0.82;
const BASE_TEXT_OPACITY = 0.8;
const EXTRUSION_OPACITY = 0.2;

// Change this single key to try a different dark map palette quickly.
const ACTIVE_DARK_MAP_PALETTE: keyof typeof DARK_MAP_PALETTES = "coolSlate";

function includesAny(value: string, keywords: string[]) {
  return keywords.some((keyword) => value.includes(keyword));
}

function areTooltipsEqual(left: MapTooltipState, right: MapTooltipState) {
  if (left === right) {
    return true;
  }

  if (!left || !right || left.type !== right.type) {
    return false;
  }

  if (left.x !== right.x || left.y !== right.y) {
    return false;
  }

  if (left.type === "hex" && right.type === "hex") {
    return left.count === right.count;
  }

  if (left.type === "marker" && right.type === "marker") {
    return (
      left.title === right.title &&
      left.dateLabel === right.dateLabel &&
      left.sourceLabel === right.sourceLabel &&
      left.url === right.url &&
      left.category === right.category
    );
  }

  return false;
}

function setPaintSafely(
  map: MapLibreMap,
  layerId: string,
  paintKey: string,
  value: unknown,
) {
  try {
    map.setPaintProperty(layerId, paintKey, value as never);
  } catch {
    // Some layers do not support all paint keys.
  }
}

function applyMapThemePaint(map: MapLibreMap, mode: MapThemeMode) {
  // Light mode must stay exactly the original map style.
  if (mode === "light") {
    return;
  }

  if (!map.isStyleLoaded()) {
    return;
  }

  const style = map.getStyle();
  if (!style || !style.layers) {
    return;
  }

  const palette = DARK_MAP_PALETTES[ACTIVE_DARK_MAP_PALETTE];
  const layers = style.layers;

  for (const layer of layers) {
    const sourceLayer =
      "source-layer" in layer && typeof layer["source-layer"] === "string"
        ? layer["source-layer"]
        : "";
    const token = `${layer.id} ${sourceLayer}`.toLowerCase();

    if (layer.type === "background") {
      setPaintSafely(map, layer.id, "background-color", palette.background);
      continue;
    }

    if (layer.type === "fill") {
      // Some base styles use hatch textures via fill-pattern; disable them in dark mode.
      setPaintSafely(map, layer.id, "fill-pattern", null);

      if (includesAny(token, ["water", "river", "lake", "sea"])) {
        setPaintSafely(map, layer.id, "fill-color", palette.water);
        setPaintSafely(map, layer.id, "fill-outline-color", palette.waterEdge);
        setPaintSafely(map, layer.id, "fill-opacity", 0.9);
        continue;
      }

      if (includesAny(token, ["park", "forest", "grass", "green", "landuse"])) {
        setPaintSafely(map, layer.id, "fill-color", palette.parks);
        setPaintSafely(map, layer.id, "fill-opacity", 0.62);
        continue;
      }

      if (includesAny(token, ["building", "house"])) {
        setPaintSafely(map, layer.id, "fill-color", palette.buildings);
        setPaintSafely(map, layer.id, "fill-outline-color", palette.buildings);
        setPaintSafely(map, layer.id, "fill-opacity", BUILDING_FILL_OPACITY);
        continue;
      }

      setPaintSafely(map, layer.id, "fill-color", palette.land);
      setPaintSafely(map, layer.id, "fill-opacity", 0.8);
      continue;
    }

    if (layer.type === "line") {
      if (
        includesAny(token, [
          "building",
          "house",
          "footprint",
          "parcel",
          "lot",
          "plot",
          "cadastre",
        ])
      ) {
        setPaintSafely(map, layer.id, "line-color", palette.buildings);
        setPaintSafely(map, layer.id, "line-opacity", BUILDING_BOUNDARY_OPACITY);
        setPaintSafely(map, layer.id, "line-blur", 0.2);
        continue;
      }

      if (includesAny(token, ["highway", "motorway", "trunk"])) {
        if (includesAny(token, ["casing", "outline", "stroke"])) {
          setPaintSafely(map, layer.id, "line-color", palette.roadHighwayStroke);
          setPaintSafely(map, layer.id, "line-opacity", HIGHWAY_LINE_OPACITY);
        } else {
          setPaintSafely(map, layer.id, "line-color", palette.roadHighway);
          setPaintSafely(map, layer.id, "line-opacity", HIGHWAY_LINE_OPACITY);
        }
        continue;
      }

      if (includesAny(token, ["primary", "secondary", "tertiary", "arterial", "major"])) {
        setPaintSafely(map, layer.id, "line-color", palette.roadMajor);
        setPaintSafely(map, layer.id, "line-opacity", MAJOR_LINE_OPACITY);
        continue;
      }

      if (includesAny(token, ["road", "street", "residential", "service"])) {
        setPaintSafely(map, layer.id, "line-color", palette.roadMinor);
        setPaintSafely(map, layer.id, "line-opacity", MINOR_LINE_OPACITY);
        continue;
      }

      if (includesAny(token, ["rail", "transit", "subway", "tram"])) {
        setPaintSafely(map, layer.id, "line-color", palette.transitLine);
        setPaintSafely(map, layer.id, "line-opacity", 0.74);
        continue;
      }

      if (includesAny(token, ["water", "river", "coast", "boundary", "admin"])) {
        setPaintSafely(map, layer.id, "line-color", palette.boundaries);
        setPaintSafely(map, layer.id, "line-opacity", BOUNDARY_LINE_OPACITY);
        continue;
      }

      setPaintSafely(map, layer.id, "line-color", palette.boundaries);
      setPaintSafely(map, layer.id, "line-opacity", 0.34);
      continue;
    }

    if (layer.type === "symbol") {
      if (includesAny(token, ["water", "river", "lake", "sea"])) {
        setPaintSafely(map, layer.id, "text-color", palette.labelsWater);
        setPaintSafely(map, layer.id, "icon-color", palette.labelsWater);
        setPaintSafely(map, layer.id, "text-opacity", BASE_TEXT_OPACITY);
        setPaintSafely(map, layer.id, "icon-opacity", BASE_TEXT_OPACITY);
      } else if (includesAny(token, ["road", "street", "highway", "motorway", "route"])) {
        setPaintSafely(map, layer.id, "text-color", palette.labelsRoad);
        setPaintSafely(map, layer.id, "icon-color", palette.labelsRoad);
        setPaintSafely(map, layer.id, "text-opacity", ROAD_TEXT_OPACITY);
        setPaintSafely(map, layer.id, "icon-opacity", ROAD_TEXT_OPACITY);
      } else if (includesAny(token, ["park", "forest", "green", "nature"])) {
        setPaintSafely(map, layer.id, "text-color", palette.labelsPark);
        setPaintSafely(map, layer.id, "icon-color", palette.labelsPark);
        setPaintSafely(map, layer.id, "text-opacity", BASE_TEXT_OPACITY);
        setPaintSafely(map, layer.id, "icon-opacity", BASE_TEXT_OPACITY);
      } else if (
        includesAny(token, [
          "poi",
          "place",
          "locality",
          "district",
          "village",
          "town",
          "city",
          "administrative",
        ])
      ) {
        setPaintSafely(map, layer.id, "text-color", palette.labelsPoi);
        setPaintSafely(map, layer.id, "icon-color", palette.labelsPoi);
        setPaintSafely(map, layer.id, "text-opacity", POI_TEXT_OPACITY);
        setPaintSafely(map, layer.id, "icon-opacity", POI_TEXT_OPACITY);
      } else {
        setPaintSafely(map, layer.id, "text-color", palette.labels);
        setPaintSafely(map, layer.id, "icon-color", palette.labels);
        setPaintSafely(map, layer.id, "text-opacity", BASE_TEXT_OPACITY);
        setPaintSafely(map, layer.id, "icon-opacity", BASE_TEXT_OPACITY);
      }

      setPaintSafely(map, layer.id, "text-halo-color", palette.labelHalo);
      setPaintSafely(map, layer.id, "text-halo-width", 1.8);
      setPaintSafely(map, layer.id, "text-halo-blur", 0.35);
      continue;
    }

    if (layer.type === "fill-extrusion") {
      setPaintSafely(map, layer.id, "fill-extrusion-color", palette.extrusions);
      setPaintSafely(map, layer.id, "fill-extrusion-opacity", EXTRUSION_OPACITY);
      continue;
    }

    if (layer.type === "raster") {
      setPaintSafely(map, layer.id, "raster-saturation", -0.2);
      setPaintSafely(map, layer.id, "raster-brightness-min", 0.24);
      setPaintSafely(map, layer.id, "raster-brightness-max", 0.8);
      setPaintSafely(map, layer.id, "raster-contrast", -0.05);
      continue;
    }

    if (layer.type === "circle") {
      if (includesAny(token, ["transit", "station", "stop"])) {
        setPaintSafely(map, layer.id, "circle-color", palette.transit);
        setPaintSafely(map, layer.id, "circle-stroke-color", palette.labelsPoi);
      } else {
        setPaintSafely(map, layer.id, "circle-color", palette.roadMajor);
      }
      setPaintSafely(map, layer.id, "circle-opacity", 0.82);
    }
  }

}

function isRemoteStyleUrl(value: string) {
  return value.startsWith("https://") || value.startsWith("http://");
}

function sanitizeResolvedStyle(styleDocument: unknown): MapStyleDefinition | null {
  if (!styleDocument || typeof styleDocument !== "object" || Array.isArray(styleDocument)) {
    return null;
  }

  const rest = { ...(styleDocument as Record<string, unknown>) };
  delete rest.projection;
  return rest;
}

export default function MapView({
  className = "h-full w-full",
  styleUrl = DEFAULT_STYLE_URL,
  themeMode = "light",
  items = [],
  onMarkerSelect,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerTooltipBridgeRef = useRef<{
    hold: () => void;
    release: () => void;
  }>({
    hold: () => {},
    release: () => {},
  });
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const layerMode: MapLayerMode = "markers";
  const [tooltip, setTooltip] = useState<MapTooltipState>(null);
  const deckPoints = useMemo<DeckNewsPoint[]>(
    () => adaptNewsItemsToDeckPoints(items),
    [items],
  );
  const resolvedStyleRef = useRef<MapStyleDefinition | null>(null);
  const appliedStyleRef = useRef<MapStyleDefinition | null>(null);
  const activeThemeModeRef = useRef<MapThemeMode>(themeMode);
  const previousThemeModeRef = useRef<MapThemeMode>(themeMode);
  const didRunInitialFlightRef = useRef(false);
  const [resolvedStyle, setResolvedStyle] = useState<MapStyleDefinition | null>(null);

  useEffect(() => {
    let cancelled = false;

    const commitResolvedStyle = (nextStyle: MapStyleDefinition) => {
      if (cancelled) {
        return;
      }

      resolvedStyleRef.current = nextStyle;
      setResolvedStyle(nextStyle);
    };

    if (!styleUrl) {
      commitResolvedStyle(FALLBACK_MAP_STYLE);
      return () => {
        cancelled = true;
      };
    }

    if (!isRemoteStyleUrl(styleUrl)) {
      commitResolvedStyle(styleUrl);
      return () => {
        cancelled = true;
      };
    }

    void fetch(styleUrl, {
      redirect: "follow",
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Map style request failed with status ${response.status}`);
        }

        const styleDocument = await response.json();
        const sanitizedStyle = sanitizeResolvedStyle(styleDocument);
        commitResolvedStyle(sanitizedStyle ?? FALLBACK_MAP_STYLE);
      })
      .catch(() => {
        commitResolvedStyle(FALLBACK_MAP_STYLE);
      });

    return () => {
      cancelled = true;
    };
  }, [styleUrl]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current || !resolvedStyle) {
      return;
    }

    let disposed = false;

    const nextMap = new maplibregl.Map({
      container: containerRef.current,
      style: resolvedStyle as never,
      center: KOCAELI_CENTER,
      zoom: INITIAL_ZOOM,
      pitch: 45,
      bearing: -8,
      canvasContextAttributes: { antialias: true },
    });

    mapRef.current = nextMap;
    appliedStyleRef.current = resolvedStyle;
    nextMap.addControl(new maplibregl.NavigationControl(), "bottom-right");

    const ensureBaseLayers = () => {
      if (disposed || !nextMap.isStyleLoaded()) {
        return;
      }

      const currentStyle = nextMap.getStyle();
      if (!currentStyle || !Array.isArray(currentStyle.layers)) {
        return;
      }

      const labelLayerId = currentStyle.layers.find(
          (layer) =>
            layer.type === "symbol" &&
            typeof layer.layout?.["text-field"] !== "undefined",
        )?.id;

      if (!didRunInitialFlightRef.current) {
        didRunInitialFlightRef.current = true;
        nextMap.flyTo({
          center: KOCAELI_CENTER,
          zoom: INITIAL_ZOOM,
          pitch: 45,
          bearing: -8,
          duration: 2500,
          essential: true,
        });
      }

      if (!nextMap.getSource(BUILDING_SOURCE_ID)) {
        nextMap.addSource(BUILDING_SOURCE_ID, {
          type: "vector",
          url: "https://tiles.openfreemap.org/planet",
        });
      }

      if (!nextMap.getLayer(BUILDING_LAYER_ID)) {
        nextMap.addLayer(
          {
            id: BUILDING_LAYER_ID,
            type: "fill-extrusion",
            source: BUILDING_SOURCE_ID,
            "source-layer": "building",
            minzoom: 15,
            filter: ["!=", ["get", "hide_3d"], true],
            paint: {
              "fill-extrusion-color": [
                "interpolate",
                ["linear"],
                ["coalesce", ["get", "render_height"], 0],
                0,
                "#334155",
                120,
                "#475569",
                250,
                "#94a3b8",
                500,
                "#cbd5e1",
              ],
              "fill-extrusion-opacity": 0.82,
              "fill-extrusion-height": [
                "interpolate",
                ["linear"],
                ["zoom"],
                15,
                0,
                16,
                ["coalesce", ["get", "render_height"], 0],
              ],
              "fill-extrusion-base": [
                "interpolate",
                ["linear"],
                ["zoom"],
                15,
                0,
                16,
                ["coalesce", ["get", "render_min_height"], 0],
              ],
            },
          },
          labelLayerId,
        );
      }
    };

    const handleLoad = () => {
      if (disposed) {
        return;
      }

      ensureBaseLayers();
      applyMapThemePaint(nextMap, activeThemeModeRef.current);
      setMap(nextMap);
    };

    const handleStyleLoad = () => {
      if (disposed) {
        return;
      }

      ensureBaseLayers();
      applyMapThemePaint(nextMap, activeThemeModeRef.current);
    };

    nextMap.once("load", handleLoad);
    nextMap.on("style.load", handleStyleLoad);

    return () => {
      disposed = true;
      nextMap.off("load", handleLoad);
      nextMap.off("style.load", handleStyleLoad);
      nextMap.remove();
      mapRef.current = null;
      setMap(null);
      didRunInitialFlightRef.current = false;
    };
  }, [resolvedStyle]);

  useEffect(() => {
    activeThemeModeRef.current = themeMode;
    const activeMap = mapRef.current;
    if (!activeMap) {
      previousThemeModeRef.current = themeMode;
      return;
    }

    if (previousThemeModeRef.current === themeMode) {
      return;
    }

    // Returning to light mode should restore the untouched original style.
    if (themeMode === "light") {
      activeMap.setStyle((resolvedStyleRef.current ?? FALLBACK_MAP_STYLE) as never);
      previousThemeModeRef.current = themeMode;
      return;
    }

    applyMapThemePaint(activeMap, themeMode);
    previousThemeModeRef.current = themeMode;
  }, [themeMode]);

  useEffect(() => {
    const activeMap = mapRef.current;
    if (!activeMap || !resolvedStyle || appliedStyleRef.current === resolvedStyle) {
      return;
    }

    appliedStyleRef.current = resolvedStyle;
    activeMap.setStyle(resolvedStyle as never);
  }, [resolvedStyle]);

  const handleTooltipHoverHandlersRegistration = useCallback(
    (handlers: { hold: () => void; release: () => void }) => {
      markerTooltipBridgeRef.current = handlers;
    },
    [],
  );
  const handleTooltipChange = useCallback((nextTooltip: MapTooltipState) => {
    setTooltip((currentTooltip) =>
      areTooltipsEqual(currentTooltip, nextTooltip) ? currentTooltip : nextTooltip,
    );
  }, []);

  return (
    <div className={`pulse-map-shell relative ${className}`} data-testid="news-map-shell">
      <div ref={containerRef} className="h-full w-full" data-testid="news-map" />
      <MapTooltip
        tooltip={tooltip}
        onMarkerTooltipEnter={() => markerTooltipBridgeRef.current.hold()}
        onMarkerTooltipLeave={() => markerTooltipBridgeRef.current.release()}
      />
      <MapDomMarkerLayer
        map={map}
        points={deckPoints}
        layerMode={layerMode}
        onMarkerSelect={onMarkerSelect}
        onTooltipChange={handleTooltipChange}
        registerTooltipHoverHandlers={handleTooltipHoverHandlersRegistration}
      />
      <DeckGLOverlay
        map={map}
        points={deckPoints}
        layerMode={layerMode}
        benchmarkActive={false}
        onMarkerSelect={onMarkerSelect}
        onTooltipChange={handleTooltipChange}
      />
    </div>
  );
}
