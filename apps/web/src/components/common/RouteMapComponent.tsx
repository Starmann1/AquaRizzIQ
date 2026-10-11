import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { streetMapStyle } from '../../config/mapStyle';

export interface RouteNodePos {
  pos: [number, number]; // [lon, lat]
  name: string;
  is_shelter?: boolean;
}

export const ROUTE_NODES: Record<string, RouteNodePos> = {
  N_TNAGAR_CENTER: { pos: [80.236, 13.041], name: 'Panagal Park (T. Nagar Center)' },
  N_USMAN_RD: { pos: [80.233, 13.038], name: 'South Usman Road' },
  N_MAMBALAM_STN: { pos: [80.224, 13.036], name: 'Mambalam Railway Station' },
  N_ANNA_SALAI: { pos: [80.245, 13.033], name: 'Nandanam Anna Salai' },
  N_VELACHERY_MAIN: { pos: [80.222, 12.983], name: 'Velachery Bypass' },
  SH_TNAGAR: { pos: [80.239, 13.044], name: 'T. Nagar Relief Hall', is_shelter: true },
  SH_MAMBALAM: { pos: [80.219, 13.041], name: 'Mambalam Relief Camp', is_shelter: true },
  SH_GURUNANAK: { pos: [80.219, 12.991], name: 'Guru Nanak Shelter', is_shelter: true },
};

export const ROAD_EDGES: [string, string][] = [
  ['N_TNAGAR_CENTER', 'SH_TNAGAR'],
  ['N_TNAGAR_CENTER', 'N_USMAN_RD'],
  ['N_USMAN_RD', 'N_MAMBALAM_STN'],
  ['N_MAMBALAM_STN', 'SH_MAMBALAM'],
  ['N_TNAGAR_CENTER', 'N_ANNA_SALAI'],
  ['N_ANNA_SALAI', 'N_VELACHERY_MAIN'],
  ['N_VELACHERY_MAIN', 'SH_GURUNANAK'],
];

interface RouteMapComponentProps {
  originNode: string;
  destinationNode: string;
  routeNodes?: string[];
  blockUsmanRoad?: boolean;
  height?: string;
}

export default function RouteMapComponent({
  originNode,
  destinationNode,
  routeNodes,
  blockUsmanRoad = false,
  height = '380px',
}: RouteMapComponentProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: streetMapStyle as any,
      center: [80.233, 13.02],
      zoom: 12.5,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');

    map.on('load', () => {
      // Build GeoJSON lines for the full road network
      const networkFeatures = ROAD_EDGES.map(([u, v]) => {
        const uNode = ROUTE_NODES[u];
        const vNode = ROUTE_NODES[v];
        if (!uNode || !vNode) return null;
        return {
          type: 'Feature' as const,
          properties: { u, v },
          geometry: {
            type: 'LineString' as const,
            coordinates: [uNode.pos, vNode.pos],
          },
        };
      }).filter(Boolean);

      map.addSource('road-network', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: networkFeatures as any,
        },
      });

      // Background road network lines
      map.addLayer({
        id: 'roads-bg',
        type: 'line',
        source: 'road-network',
        paint: {
          'line-color': '#94a3b8',
          'line-width': 4,
          'line-dasharray': [2, 1],
        },
      });

      // Source for active evacuation route
      map.addSource('active-route', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      });

      // Active evacuation route glowing line
      map.addLayer({
        id: 'route-glow',
        type: 'line',
        source: 'active-route',
        paint: {
          'line-color': '#0ea5e9',
          'line-width': 8,
          'line-opacity': 0.45,
        },
      });

      map.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'active-route',
        paint: {
          'line-color': '#0284c7',
          'line-width': 4,
        },
      });

      map.addLayer({
        id: 'route-label',
        type: 'symbol',
        source: 'active-route',
        layout: {
          'symbol-placement': 'line',
          'text-field': 'Illustrative route · not safety evaluated',
          'text-size': 11,
          'text-keep-upright': true,
        },
        paint: {
          'text-color': '#064e3b',
          'text-halo-color': '#d1fae5',
          'text-halo-width': 2,
        },
      });

      // Source for blocked road
      map.addSource('blocked-edges', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      });

      map.addLayer({
        id: 'blocked-line',
        type: 'line',
        source: 'blocked-edges',
        paint: {
          'line-color': '#ef4444',
          'line-width': 6,
          'line-dasharray': [1, 1],
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Route and Blocked edge sources
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // Blocked edge update
    const blockedSource = map.getSource('blocked-edges') as maplibregl.GeoJSONSource;
    if (blockedSource) {
      const tnagar = ROUTE_NODES['N_TNAGAR_CENTER'];
      const usman = ROUTE_NODES['N_USMAN_RD'];
      if (blockUsmanRoad && tnagar && usman) {
        blockedSource.setData({
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              properties: {},
              geometry: {
                type: 'LineString',
                coordinates: [tnagar.pos, usman.pos],
              },
            },
          ],
        });
      } else {
        blockedSource.setData({ type: 'FeatureCollection', features: [] });
      }
    }

    // Active Route update
    const routeSource = map.getSource('active-route') as maplibregl.GeoJSONSource;
    if (routeSource) {
      if (routeNodes && routeNodes.length > 1) {
        const coords = routeNodes
          .map((n) => ROUTE_NODES[n]?.pos)
          .filter(Boolean) as [number, number][];

        routeSource.setData({
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              properties: {},
              geometry: {
                type: 'LineString',
                coordinates: coords,
              },
            },
          ],
        });

        // Fit route
        if (coords.length > 1) {
          const lons = coords.map((c) => c[0]);
          const lats = coords.map((c) => c[1]);
          map.fitBounds(
            [
              [Math.min(...lons) - 0.01, Math.min(...lats) - 0.01],
              [Math.max(...lons) + 0.01, Math.max(...lats) + 0.01],
            ],
            { padding: 30, duration: 600 }
          );
        }
      } else {
        routeSource.setData({ type: 'FeatureCollection', features: [] });
      }
    }
  }, [routeNodes, blockUsmanRoad]);

  // Update HTML Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    Object.entries(ROUTE_NODES).forEach(([key, node]) => {
      const isOrigin = key === originNode;
      const isDest = key === destinationNode;
      const isShelter = node.is_shelter;
      const isBlocked = blockUsmanRoad && key === 'N_USMAN_RD';

      const el = document.createElement('div');
      el.className = 'cursor-pointer flex flex-col items-center group';

      let bgClass = 'bg-white border-sky-300 text-sky-900 shadow-sm';
      let icon = '📍';

      if (isOrigin) {
        bgClass = 'bg-sky-600 border-sky-300 text-white ring-4 ring-sky-500/30';
        icon = '🚗';
      } else if (isDest) {
        bgClass = 'bg-emerald-600 border-emerald-300 text-white ring-4 ring-emerald-500/30';
        icon = '🏕️';
      } else if (isShelter) {
        bgClass = 'bg-teal-700 border-teal-400 text-white';
        icon = '🛡️';
      } else if (isBlocked) {
        bgClass = 'bg-rose-700 border-rose-400 text-white animate-bounce';
        icon = '⛔';
      }

      el.innerHTML = `
        <div class="w-7 h-7 rounded-full border-2 ${bgClass} flex items-center justify-center text-xs shadow-md transform group-hover:scale-125 transition-transform">
          ${icon}
        </div>
        <div class="mt-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-white/95 text-slate-800 border border-sky-200 whitespace-nowrap shadow-xs pointer-events-none">
          ${node.name}
        </div>
      `;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(node.pos)
        .addTo(map);

      markersRef.current.push(marker);
    });
  }, [originNode, destinationNode, blockUsmanRoad]);

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-sky-200/90 shadow-sm bg-sky-50" style={{ height }}>
      <div ref={mapContainerRef} className="w-full h-full" />
      <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur border border-sky-200/90 px-3.5 py-2 rounded-xl text-[11px] text-slate-700 shadow-sm flex flex-wrap items-center gap-3 font-medium">
        <span className="flex items-center gap-1.5"><span className="text-sm">🚗</span> Origin</span>
        <span className="flex items-center gap-1.5"><span className="text-sm">🏕️</span> Shelter Destination</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 bg-sky-600 rounded"></span> Safe Route</span>
        {blockUsmanRoad && (
          <span className="flex items-center gap-1.5 text-rose-700 font-bold"><span className="text-sm">⛔</span> Flooded Subway</span>
        )}
        <span className="text-amber-800 font-medium pl-1 border-l border-slate-200">Demo road network; calibrated graph</span>
      </div>
    </div>
  );
}
