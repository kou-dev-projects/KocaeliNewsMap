"use client";

import { useEffect, useRef, type MutableRefObject } from "react";
import maplibregl, {
  type GeoJSONSource,
  type Map as MapLibreMap,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

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

type NewsFeatureProperties = {
  id: string;
  title: string;
  summary: string;
  source_name: string;
  source_domain: string;
  url: string;
  published_at_raw: string;
  category: string;
  district: string;
  geocode_status: string;
};

const KOCAELI_CENTER: [number, number] = [29.9213, 40.7654];
const INITIAL_ZOOM = 12;
const BUILDING_SOURCE_ID = "openfreemap";
const BUILDING_LAYER_ID = "kocaeli-3d-buildings";
const NEWS_SOURCE_ID = "news-points";
const NEWS_LAYER_ID = "news-point-circles";

const DEFAULT_STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://tiles.openfreemap.org/styles/liberty";

function buildNewsFeatureCollection(items: NewsMapItem[]) {
  return {
    type: "FeatureCollection" as const,
    features: items.map((item) => ({
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [item.longitude, item.latitude],
      },
      properties: {
        id: item.id,
        title: item.title,
        summary: item.summary ?? "",
        source_name: item.source_name,
        source_domain: item.source_domain,
        url: item.url,
        published_at_raw: item.published_at_raw ?? "",
        category: item.category ?? "",
        district: item.district ?? "",
        geocode_status: item.geocode_status,
      },
    })),
  };
}

function ensureNewsLayer(map: MapLibreMap) {
  const source = map.getSource(NEWS_SOURCE_ID) as GeoJSONSource | undefined;
  if (!source) {
    map.addSource(NEWS_SOURCE_ID, {
      type: "geojson",
      data: buildNewsFeatureCollection([]),
    });
  }

  if (!map.getLayer(NEWS_LAYER_ID)) {
    map.addLayer({
      id: NEWS_LAYER_ID,
      type: "circle",
      source: NEWS_SOURCE_ID,
      paint: {
        "circle-radius": 7,
        "circle-color": [
          "match",
          ["get", "category"],
          "yangin",
          "#dc2626",
          "trafik_kazasi",
          "#f97316",
          "elektrik_kesintisi",
          "#ca8a04",
          "hirsizlik",
          "#7c3aed",
          "kulturel_etkinlik",
          "#0284c7",
          "#0f172a",
        ],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
        "circle-opacity": 0.9,
      },
    });
  }
}

function updateNewsSource(map: MapLibreMap, items: NewsMapItem[]) {
  const source = map.getSource(NEWS_SOURCE_ID) as GeoJSONSource | undefined;
  if (!source) {
    return;
  }

  source.setData(buildNewsFeatureCollection(items));
}

function bindNewsInteractions(
  map: MapLibreMap,
  popupRef: MutableRefObject<maplibregl.Popup | null>,
  itemsRef: MutableRefObject<NewsMapItem[]>,
  onMarkerSelectRef: MutableRefObject<((item: NewsMapItem) => void) | undefined>,
) {
  if (map.getLayer(NEWS_LAYER_ID) === undefined) {
    return;
  }

  map.on("mouseenter", NEWS_LAYER_ID, () => {
    map.getCanvas().style.cursor = "pointer";
  });

  map.on("mouseleave", NEWS_LAYER_ID, () => {
    map.getCanvas().style.cursor = "";
  });

  map.on("click", NEWS_LAYER_ID, (event) => {
    const feature = event.features?.[0];
    if (!feature || feature.geometry.type !== "Point") {
      return;
    }

    const properties = feature.properties as unknown as NewsFeatureProperties;
    const coordinates = [...feature.geometry.coordinates] as [number, number];

    popupRef.current?.remove();

    const popupContent = document.createElement("div");
    popupContent.className = "space-y-2 text-slate-900";

    const title = document.createElement("h3");
    title.className = "text-sm font-semibold";
    title.textContent = properties.title;

    const date = document.createElement("p");
    date.className = "text-xs text-slate-500";
    date.textContent = properties.published_at_raw || "Tarih yok";

    popupContent.append(title, date);

    popupRef.current = new maplibregl.Popup({
      closeButton: true,
      offset: 14,
      maxWidth: "280px",
    })
      .setLngLat(coordinates)
      .setDOMContent(popupContent)
      .addTo(map);

    const selectedItem = itemsRef.current.find((item) => item.id === properties.id);
    if (selectedItem) {
      onMarkerSelectRef.current?.(selectedItem);
    }
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
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const itemsRef = useRef(items);
  const onMarkerSelectRef = useRef(onMarkerSelect);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    onMarkerSelectRef.current = onMarkerSelect;
  }, [onMarkerSelect]);

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
      const labelLayerId = map
        .getStyle()
        .layers?.find(
          (layer) =>
            layer.type === "symbol" &&
            typeof layer.layout?.["text-field"] !== "undefined",
        )?.id;

      const initializeLayers = async () => {
        map.flyTo({
          center: KOCAELI_CENTER,
          zoom: INITIAL_ZOOM,
          pitch: 45,
          bearing: -8,
          duration: 2500,
          essential: true,
        });

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

        ensureNewsLayer(map);
        updateNewsSource(map, itemsRef.current);
        bindNewsInteractions(map, popupRef, itemsRef, onMarkerSelectRef);
      };

      void initializeLayers();
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [styleUrl]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) {
      return;
    }

    ensureNewsLayer(map);
    updateNewsSource(map, items);
  }, [items]);

  return <div ref={containerRef} className={className} />;
}
