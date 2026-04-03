"use client";

import { useEffect, useMemo, useRef } from "react";
import { HexagonLayer } from "@deck.gl/aggregation-layers";
import type { Layer, LayersList } from "@deck.gl/core";
import { IconLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { IControl, Map as MapLibreMap } from "maplibre-gl";

import type { NewsMapItem } from "@/components/map/MapView";
import type { MapTooltipState } from "@/components/map/MapTooltip";
import {
  buildBenchmarkPoints,
  type DeckNewsPoint,
  type MapLayerMode,
} from "@/components/map/mapLayerUtils";

type DeckGLOverlayProps = {
  map: MapLibreMap | null;
  points: DeckNewsPoint[];
  layerMode: MapLayerMode;
  benchmarkActive: boolean;
  onMarkerSelect?: (item: NewsMapItem) => void;
  onTooltipChange: (tooltip: MapTooltipState) => void;
  onBenchmarkRender?: () => void;
};

type PickingInfo<T> = {
  object?: T;
  x?: number;
  y?: number;
};

function createLayers(
  points: DeckNewsPoint[],
  layerMode: MapLayerMode,
  handleScatterHover: (info: PickingInfo<DeckNewsPoint>) => void,
  handleScatterClick: (info: PickingInfo<DeckNewsPoint>) => void,
  handleHexHover: (info: PickingInfo<{ points?: DeckNewsPoint[] }>) => boolean,
): LayersList {
  const layers: Array<Layer | null> = [];
  const HexagonLayerCtor = HexagonLayer as unknown as new (props: Record<string, unknown>) => Layer;
  const IconLayerCtor = IconLayer as unknown as new (props: Record<string, unknown>) => Layer;

  if (layerMode === "heatmap" || layerMode === "combined") {
    layers.push(
      new HexagonLayerCtor({
        id: "news-hexagon",
        data: points,
        pickable: true,
        extruded: true,
        radius: 500,
        elevationScale: layerMode === "combined" ? 20 : 28,
        coverage: 0.9,
        opacity: layerMode === "combined" ? 0.35 : 0.7,
        colorRange: [
          [191, 219, 254],
          [125, 211, 252],
          [56, 189, 248],
          [14, 165, 233],
          [3, 105, 161],
          [8, 47, 73],
        ],
        material: {
          ambient: 0.35,
          diffuse: 0.6,
          shininess: 24,
          specularColor: [180, 220, 255],
        },
        getPosition: (point: DeckNewsPoint) => point.position,
        getColorWeight: () => 1,
        getElevationWeight: () => 1,
        elevationAggregation: "SUM",
        colorAggregation: "SUM",
        onHover: handleHexHover,
      }),
    );
  }

  if (layerMode === "markers" || layerMode === "combined") {
    layers.push(
      new IconLayerCtor({
        id: "news-marker-pins",
        data: points,
        pickable: true,
        getPosition: (point: DeckNewsPoint) => point.position,
        getIcon: (point: DeckNewsPoint) => ({
          url: point.markerUrl,
          width: 48,
          height: 64,
          anchorY: 60,
        }),
        getSize: (point: DeckNewsPoint) => Math.max(40, point.radius * 3.2),
        sizeUnits: "pixels",
        sizeScale: 1,
        sizeMinPixels: 40,
        sizeMaxPixels: 58,
        onHover: handleScatterHover,
        onClick: handleScatterClick,
      }),
    );
  }

  return layers;
}

export default function DeckGLOverlay({
  map,
  points,
  layerMode,
  benchmarkActive,
  onMarkerSelect,
  onTooltipChange,
  onBenchmarkRender,
}: DeckGLOverlayProps) {
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const handlersRef = useRef({
    onMarkerSelect,
    onTooltipChange,
    onBenchmarkRender,
  });

  useEffect(() => {
    handlersRef.current = {
      onMarkerSelect,
      onTooltipChange,
      onBenchmarkRender,
    };
  }, [onBenchmarkRender, onMarkerSelect, onTooltipChange]);

  const effectivePoints = useMemo(
    () => (benchmarkActive ? buildBenchmarkPoints(points) : points),
    [benchmarkActive, points],
  );
  const hasRenderableData = effectivePoints.length > 0;

  useEffect(() => {
    if (!map) {
      return;
    }

    if (!hasRenderableData) {
      handlersRef.current.onTooltipChange(null);

      if (overlayRef.current) {
        map.removeControl(overlayRef.current as unknown as IControl);
        overlayRef.current = null;
      }
      return;
    }

    if (overlayRef.current) {
      return;
    }

    const overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
    });

    map.addControl(overlay as unknown as IControl);
    overlayRef.current = overlay;

    return () => {
      handlersRef.current.onTooltipChange(null);

      if (overlayRef.current) {
        map.removeControl(overlayRef.current as unknown as IControl);
        overlayRef.current = null;
      }
    };
  }, [hasRenderableData, map]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay || !map || !hasRenderableData) {
      return;
    }

    const canvas = map.getCanvas();

    const handleScatterHover = (info: PickingInfo<DeckNewsPoint>) => {
      if (!info.object || info.x === undefined || info.y === undefined) {
        canvas.style.cursor = "";
        handlersRef.current.onTooltipChange(null);
        return;
      }

      canvas.style.cursor = "pointer";
      handlersRef.current.onTooltipChange({
        type: "marker",
        x: info.x,
        y: info.y,
        title: info.object.title,
        dateLabel: info.object.publishedLabel,
      });
    };

    const handleScatterClick = (info: PickingInfo<DeckNewsPoint>) => {
      if (!info.object) {
        return;
      }

      handlersRef.current.onMarkerSelect?.(info.object.sourceItem);
    };

    const handleHexHover = (info: PickingInfo<{ points?: DeckNewsPoint[] }>) => {
      const count = info.object?.points?.length ?? 0;

      if (!count || info.x === undefined || info.y === undefined) {
        canvas.style.cursor = "";
        handlersRef.current.onTooltipChange(null);
        return false;
      }

      canvas.style.cursor = "crosshair";
      handlersRef.current.onTooltipChange({
        type: "hex",
        x: info.x,
        y: info.y,
        count,
      });

      return false;
    };

    overlay.setProps({
      onAfterRender: () => {
        if (benchmarkActive) {
          handlersRef.current.onBenchmarkRender?.();
        }
      },
      layers: createLayers(
        effectivePoints,
        layerMode,
        handleScatterHover,
        handleScatterClick,
        handleHexHover,
      ),
    });

    return () => {
      canvas.style.cursor = "";
    };
  }, [benchmarkActive, effectivePoints, hasRenderableData, layerMode, map]);

  return null;
}
