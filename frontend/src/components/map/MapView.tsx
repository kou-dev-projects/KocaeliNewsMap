"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import DeckGLOverlay from "@/components/map/DeckGLOverlay";
import MapLayerToggle from "@/components/map/MapLayerToggle";
import MapTooltip, { type MapTooltipState } from "@/components/map/MapTooltip";
import { FpsTracker, type FpsMetrics } from "@/components/map/mapFpsTracker";
import {
  adaptNewsItemsToDeckPoints,
  buildBenchmarkPoints,
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

type MapViewProps = {
  className?: string;
  styleUrl?: string;
  items?: NewsMapItem[];
  onMarkerSelect?: (item: NewsMapItem) => void;
};

const KOCAELI_CENTER: [number, number] = [29.9213, 40.7654];
const INITIAL_ZOOM = 12;
const BUILDING_SOURCE_ID = "openfreemap";
const BUILDING_LAYER_ID = "kocaeli-3d-buildings";
const BENCHMARK_DURATION_MS = 2800;

const DEFAULT_STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://tiles.openfreemap.org/styles/liberty";

function waitForAnimationFrames(frameCount = 2) {
  return new Promise<void>((resolve) => {
    let remaining = frameCount;

    const step = () => {
      remaining -= 1;

      if (remaining <= 0) {
        resolve();
        return;
      }

      window.requestAnimationFrame(step);
    };

    window.requestAnimationFrame(step);
  });
}

function waitForMapEvent(map: MapLibreMap, eventName: string) {
  return new Promise<void>((resolve) => {
    map.once(eventName, () => resolve());
  });
}

export default function MapView({
  className = "h-full w-full",
  styleUrl = DEFAULT_STYLE_URL,
  items = [],
  onMarkerSelect,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const [layerMode, setLayerMode] = useState<MapLayerMode>("markers");
  const [tooltip, setTooltip] = useState<MapTooltipState>(null);
  const [benchmarkActive, setBenchmarkActive] = useState(false);
  const [benchmarkRunning, setBenchmarkRunning] = useState(false);
  const [benchmarkMetrics, setBenchmarkMetrics] = useState<FpsMetrics>();
  const deckPoints = useMemo<DeckNewsPoint[]>(
    () => adaptNewsItemsToDeckPoints(items),
    [items],
  );
  const benchmarkPointCount = useMemo(
    () => buildBenchmarkPoints(deckPoints).length,
    [deckPoints],
  );
  const benchmarkTrackerRef = useRef<{
    tracker: FpsTracker;
    previousTimestamp?: number;
  } | null>(null);
  const activeStyleUrlRef = useRef(styleUrl);
  const didRunInitialFlightRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const nextMap = new maplibregl.Map({
      container: containerRef.current,
      style: activeStyleUrlRef.current,
      center: KOCAELI_CENTER,
      zoom: INITIAL_ZOOM,
      pitch: 45,
      bearing: -8,
      canvasContextAttributes: { antialias: true },
    });

    mapRef.current = nextMap;
    nextMap.addControl(new maplibregl.NavigationControl(), "top-right");

    const ensureBaseLayers = () => {
      const labelLayerId = nextMap
        .getStyle()
        .layers?.find(
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
      ensureBaseLayers();
      setMap(nextMap);
    };

    nextMap.once("load", handleLoad);
    nextMap.on("style.load", ensureBaseLayers);

    return () => {
      nextMap.off("load", handleLoad);
      nextMap.off("style.load", ensureBaseLayers);
      nextMap.remove();
      mapRef.current = null;
      setMap(null);
      didRunInitialFlightRef.current = false;
    };
  }, []);

  useEffect(() => {
    const activeMap = mapRef.current;
    if (!activeMap || activeStyleUrlRef.current === styleUrl) {
      return;
    }

    activeStyleUrlRef.current = styleUrl;
    activeMap.setStyle(styleUrl);
  }, [styleUrl]);

  const handleBenchmarkRender = () => {
    const activeBenchmark = benchmarkTrackerRef.current;
    if (!activeBenchmark) {
      return;
    }

    const now = performance.now();
    if (activeBenchmark.previousTimestamp === undefined) {
      activeBenchmark.previousTimestamp = now;
      return;
    }

    activeBenchmark.tracker.record(now - activeBenchmark.previousTimestamp);
    activeBenchmark.previousTimestamp = now;
  };

  const handleRunBenchmark = async () => {
    const activeMap = mapRef.current;
    if (!activeMap || benchmarkRunning || benchmarkPointCount === 0) {
      return;
    }

    setBenchmarkRunning(true);
    setBenchmarkActive(true);
    setBenchmarkMetrics(undefined);
    benchmarkTrackerRef.current = {
      tracker: new FpsTracker(),
    };

    await waitForAnimationFrames(3);

    const initialBearing = activeMap.getBearing();
    const initialPitch = activeMap.getPitch();
    activeMap.easeTo({
      bearing: initialBearing + 22,
      pitch: Math.min(58, initialPitch + 8),
      duration: BENCHMARK_DURATION_MS,
      essential: true,
    });

    await waitForMapEvent(activeMap, "moveend");

    const metrics = benchmarkTrackerRef.current?.tracker.getMetrics();
    benchmarkTrackerRef.current = null;
    setBenchmarkActive(false);
    setBenchmarkMetrics(metrics);
    setBenchmarkRunning(false);

    activeMap.easeTo({
      bearing: initialBearing,
      pitch: initialPitch,
      duration: 450,
      essential: true,
    });
  };

  return (
    <div className={`relative ${className}`} data-testid="news-map-shell">
      <div ref={containerRef} className="h-full w-full" data-testid="news-map" />

      <MapLayerToggle
        layerMode={layerMode}
        onLayerModeChange={setLayerMode}
        onRunBenchmark={handleRunBenchmark}
        benchmarkRunning={benchmarkRunning}
        benchmarkMetrics={benchmarkMetrics}
        pointCount={deckPoints.length}
        benchmarkPointCount={benchmarkPointCount}
      />
      <MapTooltip tooltip={tooltip} />
      <DeckGLOverlay
        map={map}
        points={deckPoints}
        layerMode={layerMode}
        benchmarkActive={benchmarkActive}
        onMarkerSelect={onMarkerSelect}
        onTooltipChange={setTooltip}
        onBenchmarkRender={handleBenchmarkRender}
      />
    </div>
  );
}
