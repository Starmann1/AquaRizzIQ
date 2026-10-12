import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { streetMapStyle } from '../../config/mapStyle';
import { EvacuationCorridor } from '../../api/client';

export interface RouteNodePos {
  pos: [number, number]; // [lon, lat]
  name: string;
  sector?: string;
  zone?: string;
  is_shelter?: boolean;
  safety?: number;
  capacity?: number;
  est_evacuees?: number;
}

export const ROUTE_NODES: Record<string, RouteNodePos> = {
  // --- North Chennai (Zones 1-5) ---
  N_ENNORE: { pos: [80.315, 13.198], name: 'Ennore Express Corridor', sector: 'North Chennai', zone: 'Thiruvottiyur' },
  N_WIMCO_NAGAR: { pos: [80.301, 13.170], name: 'Wimco Nagar Coastal Basin', sector: 'North Chennai', zone: 'Thiruvottiyur' },
  N_MANALI_BASIN: { pos: [80.262, 13.172], name: 'Manali CPCL Low Basin', sector: 'North Chennai', zone: 'Manali' },
  N_KOLATHUR: { pos: [80.214, 13.123], name: 'Kolathur Lake Catchment', sector: 'North Chennai', zone: 'Thiru-Vi-Ka Nagar' },
  N_VYASARPADI: { pos: [80.258, 13.111], name: 'Vyasarpadi Jeeva Basin', sector: 'North Chennai', zone: 'Tondiarpet' },
  SH_THIRUVOTTIYUR: { pos: [80.301, 13.161], name: 'Thiruvottiyur Relief Center', sector: 'North Chennai', zone: 'Thiruvottiyur', is_shelter: true, safety: 0.92, capacity: 2500 },
  SH_MANALI: { pos: [80.258, 13.168], name: 'Mathur MMDA Relief Camp', sector: 'North Chennai', zone: 'Manali', is_shelter: true, safety: 0.89, capacity: 2000 },
  SH_MADHAVARAM: { pos: [80.231, 13.148], name: 'Madhavaram Central Camp', sector: 'North Chennai', zone: 'Madhavaram', is_shelter: true, safety: 0.94, capacity: 3000 },
  SH_ROYAPURAM: { pos: [80.288, 13.109], name: 'Stanley Medical Relief Pavilion', sector: 'North Chennai', zone: 'Royapuram', is_shelter: true, safety: 0.90, capacity: 2200 },

  // --- Central Chennai (Zones 6-10) ---
  N_TNAGAR_CENTER: { pos: [80.236, 13.041], name: 'Panagal Park (T. Nagar Center)', sector: 'Central Chennai', zone: 'Teynampet' },
  N_USMAN_RD: { pos: [80.233, 13.038], name: 'South Usman Road Subway', sector: 'Central Chennai', zone: 'Teynampet' },
  N_MAMBALAM_STN: { pos: [80.224, 13.036], name: 'Mambalam Railway Station', sector: 'Central Chennai', zone: 'Teynampet' },
  N_KOYAMBEDU: { pos: [80.191, 13.072], name: 'Koyambedu Cooum Nullah', sector: 'Central Chennai', zone: 'Anna Nagar' },
  N_ARUMBAKKAM: { pos: [80.208, 13.069], name: 'Arumbakkam River Basin', sector: 'Central Chennai', zone: 'Anna Nagar' },
  N_KODAMBAKKAM: { pos: [80.225, 13.052], name: 'Kodambakkam Low Basin', sector: 'Central Chennai', zone: 'Kodambakkam' },
  N_ANNA_SALAI: { pos: [80.245, 13.033], name: 'Nandanam Anna Salai', sector: 'Central Chennai', zone: 'Teynampet' },
  SH_PERAMBUR: { pos: [80.239, 13.107], name: 'Perambur Stadium Shelter', sector: 'Central Chennai', zone: 'Thiru-Vi-Ka Nagar', is_shelter: true, safety: 0.93, capacity: 3200 },
  SH_ANNANAGAR: { pos: [80.203, 13.089], name: 'Anna Nagar West Camp', sector: 'Central Chennai', zone: 'Anna Nagar', is_shelter: true, safety: 0.95, capacity: 3500 },
  SH_AMBATTUR: { pos: [80.155, 13.114], name: 'Ambattur OT Disaster Camp', sector: 'Central Chennai', zone: 'Ambattur', is_shelter: true, safety: 0.91, capacity: 2800 },
  SH_TNAGAR: { pos: [80.239, 13.044], name: 'T. Nagar Relief Hall', sector: 'Central Chennai', zone: 'Teynampet', is_shelter: true, safety: 0.90, capacity: 2000 },
  SH_MAMBALAM: { pos: [80.219, 13.041], name: 'Mambalam Relief Camp', sector: 'Central Chennai', zone: 'Teynampet', is_shelter: true, safety: 0.88, capacity: 1800 },

  // --- South Chennai (Zones 11-15) ---
  N_RAMAPURAM: { pos: [80.179, 13.031], name: 'Ramapuram Riverbank Basin', sector: 'South Chennai', zone: 'Valasaravakkam' },
  N_EKKATTUTHANGAL: { pos: [80.203, 13.018], name: 'Ekkattuthangal Industrial Basin', sector: 'South Chennai', zone: 'Alandur' },
  N_JAFFERKHANPET: { pos: [80.213, 13.024], name: 'Jafferkhanpet River Causeway', sector: 'South Chennai', zone: 'Kodambakkam' },
  N_VELACHERY_MAIN: { pos: [80.222, 12.983], name: 'Velachery Bypass', sector: 'South Chennai', zone: 'Perungudi' },
  N_MADIPAKKAM: { pos: [80.198, 12.964], name: 'Madipakkam Wetland Buffer', sector: 'South Chennai', zone: 'Perungudi' },
  N_PERUNGUDI_BASIN: { pos: [80.244, 12.963], name: 'Perungudi Marsh Border', sector: 'South Chennai', zone: 'Perungudi' },
  N_PALLIKARANAI: { pos: [80.216, 12.936], name: 'Pallikaranai Marsh Corridor', sector: 'South Chennai', zone: 'Sholinganallur' },
  SH_PORUR: { pos: [80.161, 13.036], name: 'Porur Elevated Community Camp', sector: 'South Chennai', zone: 'Valasaravakkam', is_shelter: true, safety: 0.92, capacity: 2500 },
  SH_GUINDY: { pos: [80.207, 13.008], name: 'Kathipara King Institute Camp', sector: 'South Chennai', zone: 'Alandur', is_shelter: true, safety: 0.96, capacity: 4000 },
  SH_GURUNANAK: { pos: [80.219, 12.991], name: 'Guru Nanak Evacuation Camp', sector: 'South Chennai', zone: 'Perungudi', is_shelter: true, safety: 0.89, capacity: 3000 },
  SH_ADYAR: { pos: [80.266, 13.001], name: 'Besant Nagar Relief Pavilion', sector: 'South Chennai', zone: 'Adyar', is_shelter: true, safety: 0.93, capacity: 2200 },
  SH_SHOLINGANALLUR: { pos: [80.228, 12.872], name: 'Sathyabama Disaster Complex', sector: 'South Chennai', zone: 'Sholinganallur', is_shelter: true, safety: 0.95, capacity: 4500 },
};

export const ROAD_EDGES: [string, string][] = [
  // Original Canonical Edges
  ['N_TNAGAR_CENTER', 'SH_TNAGAR'],
  ['N_TNAGAR_CENTER', 'N_USMAN_RD'],
  ['N_USMAN_RD', 'N_MAMBALAM_STN'],
  ['N_MAMBALAM_STN', 'SH_MAMBALAM'],
  ['N_TNAGAR_CENTER', 'N_ANNA_SALAI'],
  ['N_ANNA_SALAI', 'N_VELACHERY_MAIN'],
  ['N_VELACHERY_MAIN', 'SH_GURUNANAK'],

  // North Chennai
  ['N_ENNORE', 'N_WIMCO_NAGAR'],
  ['N_WIMCO_NAGAR', 'SH_THIRUVOTTIYUR'],
  ['N_ENNORE', 'N_MANALI_BASIN'],
  ['N_MANALI_BASIN', 'SH_MANALI'],
  ['SH_MANALI', 'SH_MADHAVARAM'],
  ['N_KOLATHUR', 'SH_MADHAVARAM'],
  ['N_KOLATHUR', 'SH_PERAMBUR'],
  ['N_VYASARPADI', 'SH_PERAMBUR'],
  ['N_VYASARPADI', 'SH_ROYAPURAM'],
  ['SH_ROYAPURAM', 'SH_PERAMBUR'],

  // Cross North-Central Interconnects
  ['SH_MADHAVARAM', 'SH_ANNANAGAR'],
  ['SH_PERAMBUR', 'N_KOYAMBEDU'],

  // Central Chennai
  ['N_KOYAMBEDU', 'N_ARUMBAKKAM'],
  ['N_ARUMBAKKAM', 'SH_ANNANAGAR'],
  ['N_KOYAMBEDU', 'SH_AMBATTUR'],
  ['N_ARUMBAKKAM', 'N_KODAMBAKKAM'],
  ['N_KODAMBAKKAM', 'SH_MAMBALAM'],
  ['SH_TNAGAR', 'N_ANNA_SALAI'],

  // Cross Central-South Interconnects
  ['N_KODAMBAKKAM', 'N_JAFFERKHANPET'],
  ['N_ANNA_SALAI', 'N_EKKATTUTHANGAL'],
  ['N_ANNA_SALAI', 'SH_GUINDY'],
  ['N_JAFFERKHANPET', 'SH_GUINDY'],
  ['N_RAMAPURAM', 'SH_PORUR'],
  ['N_RAMAPURAM', 'N_EKKATTUTHANGAL'],
  ['N_EKKATTUTHANGAL', 'SH_GUINDY'],

  // South Chennai
  ['SH_GUINDY', 'N_VELACHERY_MAIN'],
  ['N_MADIPAKKAM', 'SH_GURUNANAK'],
  ['N_MADIPAKKAM', 'N_VELACHERY_MAIN'],
  ['SH_GUINDY', 'SH_ADYAR'],
  ['SH_GURUNANAK', 'SH_ADYAR'],
  ['SH_GURUNANAK', 'N_PERUNGUDI_BASIN'],
  ['N_PERUNGUDI_BASIN', 'N_PALLIKARANAI'],
  ['N_PALLIKARANAI', 'SH_SHOLINGANALLUR'],
  ['N_PERUNGUDI_BASIN', 'SH_SHOLINGANALLUR'],
];

const CORRIDOR_COLORS = [
  '#0284c7', // Sky Blue
  '#059669', // Emerald
  '#7c3aed', // Violet
  '#d97706', // Amber
  '#dc2626', // Red
  '#0891b2', // Cyan
  '#4f46e5', // Indigo
  '#db2777', // Pink
];

interface RouteMapComponentProps {
  originNode: string;
  destinationNode: string;
  routeNodes?: string[];
  corridors?: EvacuationCorridor[];
  blockedEdges?: Array<[string, string]>;
  selectedSector?: string;
  onSelectOrigin?: (nodeId: string) => void;
  onSelectDestination?: (nodeId: string) => void;
  height?: string;
}

export default function RouteMapComponent({
  originNode,
  destinationNode,
  routeNodes,
  corridors,
  blockedEdges = [],
  selectedSector = 'All Chennai',
  onSelectOrigin,
  onSelectDestination,
  height = '480px',
}: RouteMapComponentProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: streetMapStyle as any,
      center: [80.233, 13.04],
      zoom: 11,
      minZoom: 9.5,
      maxZoom: 17,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');
    map.addControl(new maplibregl.FullscreenControl(), 'top-right');

    map.on('load', () => {
      // 1. Full Chennai Road Network Source & Layer
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

      map.addLayer({
        id: 'roads-bg',
        type: 'line',
        source: 'road-network',
        paint: {
          'line-color': '#94a3b8',
          'line-width': 3,
          'line-opacity': 0.7,
          'line-dasharray': [2, 1],
        },
      });

      // 2. Blocked Inundated Roads Layer (Dashed Red)
      map.addSource('blocked-edges', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
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

      // 3. City-Wide Multi-Corridor Layer
      map.addSource('citywide-corridors', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id: 'corridors-glow',
        type: 'line',
        source: 'citywide-corridors',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 6,
          'line-opacity': 0.35,
        },
      });

      map.addLayer({
        id: 'corridors-line',
        type: 'line',
        source: 'citywide-corridors',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 3.5,
          'line-opacity': 0.9,
        },
      });

      // 4. Single Active Route Layers (Prominent Blue)
      map.addSource('active-route', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id: 'route-glow',
        type: 'line',
        source: 'active-route',
        paint: {
          'line-color': '#0ea5e9',
          'line-width': 9,
          'line-opacity': 0.5,
        },
      });

      map.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'active-route',
        paint: {
          'line-color': '#0284c7',
          'line-width': 4.5,
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Blocked Edges
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const blockedSource = map.getSource('blocked-edges') as maplibregl.GeoJSONSource;
    if (blockedSource) {
      const features = (blockedEdges || []).map(([u, v]) => {
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

      blockedSource.setData({
        type: 'FeatureCollection',
        features: features as any,
      });
    }
  }, [blockedEdges]);

  // Update Single Route or Multi-Corridors
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const routeSource = map.getSource('active-route') as maplibregl.GeoJSONSource;
    const corridorSource = map.getSource('citywide-corridors') as maplibregl.GeoJSONSource;

    // Single Route update
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

        if (coords.length > 1) {
          const lons = coords.map((c) => c[0]);
          const lats = coords.map((c) => c[1]);
          map.fitBounds(
            [
              [Math.min(...lons) - 0.02, Math.min(...lats) - 0.02],
              [Math.max(...lons) + 0.02, Math.max(...lats) + 0.02],
            ],
            { padding: 40, duration: 600 }
          );
        }
      } else {
        routeSource.setData({ type: 'FeatureCollection', features: [] });
      }
    }

    // City-Wide Multi-Corridor update
    if (corridorSource) {
      if (corridors && corridors.length > 0) {
        const features = corridors.map((c, idx) => {
          const coords = c.route_nodes
            .map((n) => ROUTE_NODES[n]?.pos)
            .filter(Boolean) as [number, number][];
          const color = CORRIDOR_COLORS[idx % CORRIDOR_COLORS.length];
          return {
            type: 'Feature' as const,
            properties: {
              origin: c.origin_name,
              shelter: c.target_shelter_name,
              evacuees: c.evacuees_assigned,
              color,
            },
            geometry: {
              type: 'LineString' as const,
              coordinates: coords,
            },
          };
        }).filter((f) => f.geometry.coordinates.length > 1);

        corridorSource.setData({
          type: 'FeatureCollection',
          features: features as any,
        });

        // Fit map across all corridors in Chennai
        const allCoords = features.flatMap((f) => f.geometry.coordinates);
        if (allCoords.length > 1) {
          const lons = allCoords.map((c) => c[0]);
          const lats = allCoords.map((c) => c[1]);
          map.fitBounds(
            [
              [Math.min(...lons) - 0.03, Math.min(...lats) - 0.03],
              [Math.max(...lons) + 0.03, Math.max(...lats) + 0.03],
            ],
            { padding: 45, duration: 800 }
          );
        }
      } else {
        corridorSource.setData({ type: 'FeatureCollection', features: [] });
      }
    }
  }, [routeNodes, corridors]);

  // Update HTML Markers across Chennai
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const isEdgeBlocked = (nodeKey: string) =>
      (blockedEdges || []).some(([u, v]) => u === nodeKey || v === nodeKey);

    Object.entries(ROUTE_NODES).forEach(([key, node]) => {
      // Optional sector filter for markers
      if (
        selectedSector !== 'All Chennai' &&
        node.sector &&
        node.sector !== selectedSector
      ) {
        return;
      }

      const isOrigin = key === originNode;
      const isDest = key === destinationNode;
      const isShelter = node.is_shelter;
      const isBlocked = isEdgeBlocked(key);

      const el = document.createElement('div');
      el.className = 'cursor-pointer flex flex-col items-center group transition-transform hover:scale-110';

      let bgClass = 'bg-white border-sky-300 text-sky-900 shadow-sm';
      let icon = '📍';

      if (isOrigin) {
        bgClass = 'bg-sky-600 border-white text-white ring-4 ring-sky-500/40 shadow-md';
        icon = '🚗';
      } else if (isDest) {
        bgClass = 'bg-emerald-600 border-white text-white ring-4 ring-emerald-500/40 shadow-md';
        icon = '🏕️';
      } else if (isShelter) {
        bgClass = 'bg-emerald-700 border-emerald-300 text-white shadow-sm';
        icon = '🛡️';
      } else if (isBlocked) {
        bgClass = 'bg-rose-700 border-rose-300 text-white animate-pulse shadow-sm';
        icon = '⛔';
      }

      el.innerHTML = `
        <div class="w-8 h-8 rounded-full border-2 ${bgClass} flex items-center justify-center text-xs shadow-md">
          ${icon}
        </div>
        <div class="mt-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-white/95 text-slate-800 border border-sky-200 whitespace-nowrap shadow-xs pointer-events-none">
          ${node.name} ${node.capacity ? `(${node.capacity})` : ''}
        </div>
      `;

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (isShelter && onSelectDestination) {
          onSelectDestination(key);
        } else if (!isShelter && onSelectOrigin) {
          onSelectOrigin(key);
        }
      });

      const popupContent = document.createElement('div');
      popupContent.className = 'p-1.5 space-y-1 text-xs text-slate-800';
      popupContent.innerHTML = `
        <div class="font-bold text-sm text-sky-950">${node.name}</div>
        <div class="text-[11px] text-slate-500">${node.sector || 'Greater Chennai'} · ${node.zone || ''}</div>
        ${
          node.is_shelter
            ? `<div class="pt-1 text-emerald-800 font-semibold">Capacity: ${node.capacity?.toLocaleString() || '2,000'} beds | Safety: ${((node.safety || 0.9) * 100).toFixed(0)}%</div>`
            : `<div class="pt-1 text-amber-800 font-semibold">Evacuee Pool: ~${node.est_evacuees?.toLocaleString() || '1,500'} residents</div>`
        }
      `;

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(node.pos)
        .setPopup(new maplibregl.Popup({ offset: 15, closeButton: false }).setDOMContent(popupContent))
        .addTo(map);

      markersRef.current.push(marker);
    });
  }, [originNode, destinationNode, blockedEdges, selectedSector, onSelectOrigin, onSelectDestination]);

  return (
    <div
      className="relative w-full rounded-2xl overflow-hidden border border-sky-200/90 shadow-sm bg-sky-50"
      style={{ height }}
    >
      <div ref={mapContainerRef} className="w-full h-full" />
      <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur border border-sky-200/90 px-3.5 py-2 rounded-xl text-[11px] text-slate-700 shadow-sm flex flex-wrap items-center gap-3 font-medium">
        <span className="flex items-center gap-1.5"><span className="text-sm">🚗</span> Origin Hub</span>
        <span className="flex items-center gap-1.5"><span className="text-sm">🛡️</span> Designated Relief Camp</span>
        <span className="flex items-center gap-1.5"><span className="w-3.5 h-1.5 bg-sky-600 rounded"></span> Single Safe Route</span>
        {corridors && corridors.length > 0 && (
          <span className="flex items-center gap-1.5 font-bold text-emerald-700">
            <span className="w-3.5 h-1.5 bg-emerald-500 rounded"></span> City-Wide Multi-Corridor Plan ({corridors.length})
          </span>
        )}
        {blockedEdges.length > 0 && (
          <span className="flex items-center gap-1.5 text-rose-700 font-bold">
            <span className="text-sm">⛔</span> {blockedEdges.length} Blocked Chokepoints
          </span>
        )}
      </div>
    </div>
  );
}
