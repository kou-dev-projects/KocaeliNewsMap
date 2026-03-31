"use client";

import { useEffect, useRef } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type MapViewProps = {
  className?: string;
  styleUrl?: string;
};

const KOCAELI_CENTER: [number, number] = [29.9213, 40.7654];
const INITIAL_ZOOM = 12;
const BUILDING_SOURCE_ID = "openfreemap";
const BUILDING_LAYER_ID = "kocaeli-3d-buildings";

const DEFAULT_STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://tiles.openfreemap.org/styles/liberty";

export default function MapView({
  className = "h-full w-full",
  styleUrl = DEFAULT_STYLE_URL,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: KOCAELI_CENTER,
      zoom: INITIAL_ZOOM,
      pitch: 45,
      bearing: -8,
      canvasContextAttributes: { antialias: true },
    });

    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl(), "top-right");

    map.on("load", () => {
      map.flyTo({
        center: KOCAELI_CENTER,
        zoom: INITIAL_ZOOM,
        pitch: 45,
        bearing: -8,
        duration: 2500,
        essential: true,
      });

      const labelLayerId = map
        .getStyle()
        .layers?.find(
          (layer) =>
            layer.type === "symbol" &&
            typeof layer.layout?.["text-field"] !== "undefined",
        )?.id;

      if (!map.getSource(BUILDING_SOURCE_ID)) {
        map.addSource(BUILDING_SOURCE_ID, {
          type: "vector",
          url: "https://tiles.openfreemap.org/planet",
        });
      }

      if (!map.getLayer(BUILDING_LAYER_ID)) {
        map.addLayer(
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
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [styleUrl]);

  return <div ref={containerRef} className={className} />;
}
