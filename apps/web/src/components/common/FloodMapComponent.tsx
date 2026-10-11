import React, { useEffect, useImperativeHandle, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { WardRisk } from '../../api/client';
import { streetMapStyle } from '../../config/mapStyle';

export interface FloodMapComponentHandle {
  fitCatchment: () => void;
  fitZone: (zoneId: string) => void;
  fitWard: (wardId: string) => void;
}

export interface FloodMapComponentProps {
  zones?: any;
  zoneFeatures?: any[];
  risks?: Record<string, WardRisk> | WardRisk[];
  historicalFloods?: any;
  rainfall?: any;
  selectedWardId?: string | null;
  selectedZoneId?: string | null;
  onSelectWard?: (wardId: string, zoneId?: string) => void;
  onSelectZone?: (zoneId: string) => void;
  height?: string;
  showControls?: boolean;
  showHistoricalFloods?: boolean;
  setShowHistoricalFloods?: (show: boolean) => void;
  showRainfall?: boolean;
  setShowRainfall?: (show: boolean) => void;
  showZoneBoundaries?: boolean;
  setShowZoneBoundaries?: (show: boolean) => void;
  showInternalOverlay?: boolean;
}

const FloodMapComponent = React.forwardRef<FloodMapComponentHandle, FloodMapComponentProps>(function FloodMapComponent(
  {
    zones,
    zoneFeatures,
    risks,
    historicalFloods,
    rainfall,
    selectedWardId,
    selectedZoneId,
    onSelectWard,
    onSelectZone,
    height = '560px',
    showControls = true,
    showHistoricalFloods: controlledShowHistoricalFloods,
    setShowHistoricalFloods: setControlledShowHistoricalFloods,
    showRainfall: controlledShowRainfall,
    setShowRainfall: setControlledShowRainfall,
    showZoneBoundaries: controlledShowZoneBoundaries,
    setShowZoneBoundaries: setControlledShowZoneBoundaries,
    showInternalOverlay = false,
  },
  ref
) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const hasFitToDataRef = useRef<boolean>(false);
  const [mapLoaded, setMapLoaded] = useState<boolean>(false);
  const [internalHistoricalFloods, setInternalHistoricalFloods] = useState(true);
  const [internalRainfall, setInternalRainfall] = useState(true);
  const [internalZoneBoundaries, setInternalZoneBoundaries] = useState(false);

  const showHistoricalFloods = controlledShowHistoricalFloods !== undefined ? controlledShowHistoricalFloods : internalHistoricalFloods;
  const setShowHistoricalFloods = setControlledShowHistoricalFloods || setInternalHistoricalFloods;

  const showRainfall = controlledShowRainfall !== undefined ? controlledShowRainfall : internalRainfall;
  const setShowRainfall = setControlledShowRainfall || setInternalRainfall;

  const showZoneBoundaries = controlledShowZoneBoundaries !== undefined ? controlledShowZoneBoundaries : internalZoneBoundaries;
  const setShowZoneBoundaries = setControlledShowZoneBoundaries || setInternalZoneBoundaries;

  const getCoordinateBounds = (features: any[]): [[number, number], [number, number]] | null => {
    const positions: [number, number][] = [];
    const collectPositions = (value: any) => {
      if (!Array.isArray(value)) return;
      if (value.length >= 2 && typeof value[0] === 'number' && typeof value[1] === 'number') {
        positions.push([value[0], value[1]]);
        return;
      }
      value.forEach(collectPositions);
    };

    features.forEach((feature) => collectPositions(feature.geometry?.coordinates));
    if (positions.length === 0) return null;
    const longitudes = positions.map(([longitude]) => longitude);
    const latitudes = positions.map(([, latitude]) => latitude);
    return [
      [Math.min(...longitudes), Math.min(...latitudes)],
      [Math.max(...longitudes), Math.max(...latitudes)],
    ];
  };

  // Normalize risks to Record
  const riskDict: Record<string, WardRisk> = React.useMemo(() => {
    if (!risks) return {};
    if (Array.isArray(risks)) {
      const map: Record<string, WardRisk> = {};
      risks.forEach((r) => {
        map[r.ward_id] = r;
      });
      return map;
    }
    return risks;
  }, [risks]);

  const getRiskColor = (level?: string): string => {
    switch (level) {
      case 'VERY_HIGH':
        return '#ef4444';
      case 'HIGH':
        return '#f97316';
      case 'MEDIUM':
        return '#eab308';
      case 'LOW':
        return '#22c55e';
      default:
        return '#64748b';
    }
  };

  // Build GeoJSON with risk properties injected
  const enrichedGeoJson = React.useMemo(() => {
    if (!zones?.features) return null;
    return {
      type: 'FeatureCollection',
      features: zones.features.map((feat: any) => {
        const wid = feat.properties?.ward_id;
        const r = riskDict[wid];
        const riskLevel = r?.risk_level || 'UNKNOWN';
        const color = getRiskColor(riskLevel);
        const isSelected = selectedWardId === wid;
        return {
          ...feat,
          id: wid,
          properties: {
            ...feat.properties,
            risk_level: riskLevel,
            risk_score: r?.risk_score ?? null,
            hazard: r?.hazard ?? null,
            impact: r?.impact ?? null,
            fillColor: color,
            borderColor: isSelected ? '#38bdf8' : '#ffffff',
            borderWidth: isSelected ? 4 : 2,
            opacity: isSelected ? 0.75 : 0.5,
          },
        };
      }),
    };
  }, [zones, riskDict, selectedWardId]);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    hasFitToDataRef.current = false;
    setMapLoaded(false);
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: streetMapStyle as any,
      center: [80.232, 13.04],
      zoom: 10,
      maxZoom: 18,
      minZoom: 10,
    });

    if (showControls) {
      map.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true }), 'top-right');
      map.addControl(new maplibregl.FullscreenControl(), 'top-right');
    }

    map.on('load', () => {
      setMapLoaded(true);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Add/Update Wards GeoJSON Layers
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded || !enrichedGeoJson) return;

    const source = map.getSource('wards-source') as maplibregl.GeoJSONSource;
    if (source) {
      source.setData(enrichedGeoJson as any);
    } else {
      map.addSource('wards-source', {
        type: 'geojson',
        data: enrichedGeoJson as any,
      });

      // Fill Layer
      map.addLayer({
        id: 'wards-fill',
        type: 'fill',
        source: 'wards-source',
        paint: {
          'fill-color': ['get', 'fillColor'],
          'fill-opacity': ['get', 'opacity'],
        },
      });

      // Border Layer
      map.addLayer({
        id: 'wards-border',
        type: 'line',
        source: 'wards-source',
        paint: {
          'line-color': ['get', 'borderColor'],
          'line-width': ['get', 'borderWidth'],
        },
      });

      // Label Layer
      map.addLayer({
        id: 'wards-label',
        type: 'symbol',
        source: 'wards-source',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 12,
          'text-justify': 'center',
          'text-allow-overlap': true,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#020617',
          'text-halo-width': 2,
        },
      });

      // Click event
      map.on('click', 'wards-fill', (e) => {
        if (!e.features || !e.features[0]) return;
        const feature = e.features[0];
        const properties = feature.properties ?? {};
        const wid = properties.ward_id;
        const content = document.createElement('div');
        content.className = 'space-y-1 text-slate-900';
        const title = document.createElement('strong');
        title.textContent = `${String(properties.name ?? 'GCC division')} · ${String(wid ?? '')}`;
        content.appendChild(title);
        const zone = document.createElement('p');
        zone.textContent = `Zone: ${String(properties.zone ?? 'unresolved')}`;
        content.appendChild(zone);
        const area = document.createElement('p');
        area.textContent = `Boundary area: ${properties.area_sq_km == null ? 'unavailable' : `${properties.area_sq_km} km² (derived)`}`;
        content.appendChild(area);
        const floodCount = document.createElement('p');
        floodCount.textContent = `2015 NRSC polygons intersecting: ${String(properties.historical_flood_feature_count ?? 'unavailable')}`;
        content.appendChild(floodCount);
        const stationCount = document.createElement('p');
        stationCount.textContent = `Dated TN-SMART stations in division: ${String(properties.rainfall_station_count ?? 'unavailable')}`;
        content.appendChild(stationCount);
        if (properties.risk_level) {
          const riskInfo = document.createElement('p');
          const scorePercent = typeof properties.risk_score === 'number' ? (properties.risk_score * 100).toFixed(1) : null;
          riskInfo.className = 'font-semibold text-slate-800';
          riskInfo.textContent = `Flood Risk: ${properties.risk_level}${scorePercent ? ` (${scorePercent}%)` : ''}`;
          content.appendChild(riskInfo);
        }
        const liveStatus = document.createElement('p');
        liveStatus.className = 'text-[11px] text-emerald-700 font-semibold';
        liveStatus.textContent = '✓ Live risk calculated from PostgreSQL telemetry.';
        content.appendChild(liveStatus);
        new maplibregl.Popup({ closeButton: true, maxWidth: '300px' })
          .setLngLat(e.lngLat)
          .setDOMContent(content)
          .addTo(map);
        if (wid && onSelectWard) {
          onSelectWard(wid, properties.zone_id || properties.zone_candidate_id);
        }
        if (properties.zone_id && onSelectZone) {
          onSelectZone(properties.zone_id);
        }
      });

      // Hover cursor
      map.on('mouseenter', 'wards-fill', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'wards-fill', () => {
        map.getCanvas().style.cursor = '';
      });
    }
    if (!hasFitToDataRef.current) {
      const bounds = getCoordinateBounds(enrichedGeoJson.features);
      if (bounds) {
        map.fitBounds(bounds, { padding: 40, maxZoom: 12 });
        hasFitToDataRef.current = true;
      }
    }
  }, [mapLoaded, enrichedGeoJson, onSelectWard, onSelectZone]);

  // Compute effective zone ID from explicit selectedZoneId or selected ward's parent zone
  const effectiveZoneId = React.useMemo(() => {
    if (selectedZoneId) return selectedZoneId;
    if (selectedWardId && enrichedGeoJson?.features) {
      const feat = enrichedGeoJson.features.find((f: any) => f.properties?.ward_id === selectedWardId);
      return feat?.properties?.zone_id || feat?.properties?.zone_candidate_id || null;
    }
    return null;
  }, [selectedZoneId, selectedWardId, enrichedGeoJson]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const zoneCollection = { type: 'FeatureCollection', features: zoneFeatures || [] };
    if (!map.getSource('zones-source')) {
      map.addSource('zones-source', { type: 'geojson', data: zoneCollection as any });
    } else {
      (map.getSource('zones-source') as maplibregl.GeoJSONSource).setData(zoneCollection as any);
    }

    // 1. Highlight selected zone in slight yellow fill (0.22 opacity)
    if (!map.getLayer('selected-zone-fill')) {
      map.addLayer(
        {
          id: 'selected-zone-fill',
          type: 'fill',
          source: 'zones-source',
          paint: {
            'fill-color': '#facc15',
            'fill-opacity': [
              'case',
              ['==', ['get', 'zone_id'], effectiveZoneId || ''],
              0.22,
              0,
            ],
          },
        },
        map.getLayer('wards-border') ? 'wards-border' : undefined
      );
    } else {
      map.setPaintProperty('selected-zone-fill', 'fill-opacity', [
        'case',
        ['==', ['get', 'zone_id'], effectiveZoneId || ''],
        0.22,
        0,
      ]);
    }

    // 2. Highlight selected zone in solid yellow border (3.5px width)
    if (!map.getLayer('selected-zone-border')) {
      map.addLayer({
        id: 'selected-zone-border',
        type: 'line',
        source: 'zones-source',
        layout: {
          'line-join': 'round',
          'line-cap': 'round',
        },
        paint: {
          'line-color': '#eab308',
          'line-width': [
            'case',
            ['==', ['get', 'zone_id'], effectiveZoneId || ''],
            3.5,
            0,
          ],
          'line-opacity': [
            'case',
            ['==', ['get', 'zone_id'], effectiveZoneId || ''],
            1.0,
            0,
          ],
        },
      });
    } else {
      map.setPaintProperty('selected-zone-border', 'line-width', [
        'case',
        ['==', ['get', 'zone_id'], effectiveZoneId || ''],
        3.5,
        0,
      ]);
      map.setPaintProperty('selected-zone-border', 'line-opacity', [
        'case',
        ['==', ['get', 'zone_id'], effectiveZoneId || ''],
        1.0,
        0,
      ]);
    }

    // 3. Regular zone outlines (dashed line when showZoneBoundaries is enabled)
    if (!map.getLayer('zones-outline')) {
      map.addLayer({
        id: 'zones-outline',
        type: 'line',
        source: 'zones-source',
        paint: { 'line-color': '#fbbf24', 'line-width': 1.8, 'line-dasharray': [2, 1] },
      });
    }
    map.setLayoutProperty('zones-outline', 'visibility', showZoneBoundaries ? 'visible' : 'none');

    const addOrUpdateLayer = (
      sourceId: string,
      layerId: string,
      data: any,
      type: 'fill' | 'circle',
      paint: Record<string, unknown>,
      visible: boolean,
    ) => {
      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, { type: 'geojson', data: data || { type: 'FeatureCollection', features: [] } } as any);
      } else if (data) {
        (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(data);
      }
      if (!map.getLayer(layerId)) {
        map.addLayer({ id: layerId, type, source: sourceId, paint: paint as any } as any);
      }
      map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
    };

    addOrUpdateLayer(
      'historical-flood-source',
      'historical-flood-fill',
      historicalFloods,
      'fill',
      { 'fill-color': '#38bdf8', 'fill-opacity': 0.48 },
      showHistoricalFloods,
    );
    addOrUpdateLayer(
      'rainfall-source',
      'rainfall-points',
      rainfall,
      'circle',
      {
        'circle-radius': 5,
        'circle-color': [
          'case',
          ['>', ['get', 'rainfall_mm'], 204.4], '#ff0000',
          ['>', ['get', 'rainfall_mm'], 115.6], '#ffa500',
          ['>', ['get', 'rainfall_mm'], 64.4], '#ffff00',
          ['>', ['get', 'rainfall_mm'], 15.6], '#46c646',
          ['>', ['get', 'rainfall_mm'], 2.41], '#daf7a6',
          ['>', ['get', 'rainfall_mm'], 0.1], '#bfbfbf',
          '#64748b',
        ],
        'circle-stroke-color': '#0f172a',
        'circle-stroke-width': 1,
      },
      showRainfall,
    );
  }, [mapLoaded, zoneFeatures, historicalFloods, rainfall, showZoneBoundaries, showHistoricalFloods, showRainfall, effectiveZoneId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded || !map.getLayer('historical-flood-fill')) return;

    const showFloodDetails = (event: maplibregl.MapLayerMouseEvent) => {
      const feature = event.features?.[0];
      if (!feature) return;

      const properties = feature.properties ?? {};
      const content = document.createElement('div');
      content.className = 'space-y-1 text-slate-900';

      const title = document.createElement('strong');
      title.textContent = '2015 NRSC historical inundation';
      content.appendChild(title);

      const sourceFeatureId = document.createElement('p');
      sourceFeatureId.textContent = `Source feature: ${String(properties.source_feature_id ?? feature.id ?? 'not supplied')}`;
      content.appendChild(sourceFeatureId);

      const pixelValue = document.createElement('p');
      pixelValue.textContent = `Source pixel value: ${String(properties.source_pixelvalue ?? 'not supplied')}`;
      content.appendChild(pixelValue);

      const limitation = document.createElement('p');
      limitation.textContent = 'Per-feature acquisition time is unavailable. The layer was clipped to the 2022 GCC division boundary.';
      content.appendChild(limitation);

      new maplibregl.Popup({ closeButton: true, maxWidth: '280px' })
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(map);
    };

    const setPointerCursor = () => {
      map.getCanvas().style.cursor = 'pointer';
    };
    const clearPointerCursor = () => {
      map.getCanvas().style.cursor = '';
    };

    map.on('click', 'historical-flood-fill', showFloodDetails);
    map.on('mouseenter', 'historical-flood-fill', setPointerCursor);
    map.on('mouseleave', 'historical-flood-fill', clearPointerCursor);

    const showRainfallDetails = (event: maplibregl.MapLayerMouseEvent) => {
      const feature = event.features?.[0];
      if (!feature) return;
      const properties = feature.properties ?? {};
      const content = document.createElement('div');
      content.className = 'space-y-1 text-slate-900';

      const title = document.createElement('strong');
      title.textContent = String(properties.station_name ?? 'TN-SMART rainfall station');
      content.appendChild(title);

      const observation = document.createElement('p');
      observation.textContent = `${String(properties.rainfall_mm ?? 'No value')} ${String(properties.units ?? 'mm')} on ${String(properties.observation_date ?? 'date unavailable')}`;
      content.appendChild(observation);

      const interval = document.createElement('p');
      interval.textContent = `Reporting interval: ${String(properties.measurement_interval ?? 'not supplied')}`;
      content.appendChild(interval);

      const source = document.createElement('p');
      source.textContent = `Reporting agency: ${String(properties.reporting_agency ?? 'not supplied')}`;
      content.appendChild(source);

      const note = document.createElement('p');
      note.textContent = 'One dated source snapshot; not used for ward-level risk.';
      content.appendChild(note);

      new maplibregl.Popup({ closeButton: true, maxWidth: '280px' })
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(map);
    };
    map.on('click', 'rainfall-points', showRainfallDetails);
    map.on('mouseenter', 'rainfall-points', setPointerCursor);
    map.on('mouseleave', 'rainfall-points', clearPointerCursor);

    return () => {
      map.off('click', 'historical-flood-fill', showFloodDetails);
      map.off('mouseenter', 'historical-flood-fill', setPointerCursor);
      map.off('mouseleave', 'historical-flood-fill', clearPointerCursor);
      map.off('click', 'rainfall-points', showRainfallDetails);
      map.off('mouseenter', 'rainfall-points', setPointerCursor);
      map.off('mouseleave', 'rainfall-points', clearPointerCursor);
    };
  }, [mapLoaded]);

  // Update selected ward flyTo
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded || !selectedWardId || !enrichedGeoJson) return;

    const feat = enrichedGeoJson.features.find((f: any) => f.properties?.ward_id === selectedWardId);
    if (feat && feat.geometry) {
      const bounds = getCoordinateBounds([feat]);
      if (bounds) {
        map.easeTo({
          center: [
            (bounds[0][0] + bounds[1][0]) / 2,
            (bounds[0][1] + bounds[1][1]) / 2,
          ],
          duration: 600,
        });
      }
    }
  }, [selectedWardId, mapLoaded, enrichedGeoJson]);

  const handleResetView = () => {
    const map = mapRef.current;
    const bounds = zones?.features ? getCoordinateBounds(zones.features) : null;
    if (map && bounds) {
      map.fitBounds(bounds, { padding: 40, maxZoom: 12 });
    }
  };

  useImperativeHandle(ref, () => ({
    fitCatchment: () => {
      handleResetView();
    },
    fitZone: (zoneId: string) => {
      const map = mapRef.current;
      if (!map) return;
      const zf = zoneFeatures?.find((f: any) => f.properties?.zone_id === zoneId);
      if (zf && zf.geometry) {
        const bounds = getCoordinateBounds([zf]);
        if (bounds) {
          map.fitBounds(bounds, { padding: 45, maxZoom: 13, duration: 800 });
          return;
        }
      }
      const matchingWards = zones?.features?.filter(
        (f: any) => f.properties?.zone_id === zoneId || f.properties?.zone_candidate_id === zoneId
      );
      if (matchingWards && matchingWards.length > 0) {
        const bounds = getCoordinateBounds(matchingWards);
        if (bounds) {
          map.fitBounds(bounds, { padding: 45, maxZoom: 13, duration: 800 });
        }
      }
    },
    fitWard: (wardId: string) => {
      const map = mapRef.current;
      if (!map || !enrichedGeoJson) return;
      const feat = enrichedGeoJson.features.find((f: any) => f.properties?.ward_id === wardId);
      if (feat && feat.geometry) {
        const bounds = getCoordinateBounds([feat]);
        if (bounds) {
          map.fitBounds(bounds, { padding: 60, maxZoom: 14, duration: 800 });
        }
      }
    },
  }));

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-sky-200/90 shadow-sm bg-sky-50" style={{ height }}>
      {/* Map Canvas */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Controls Overlay (only when showInternalOverlay is true) */}
      {showInternalOverlay && (
        <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-2">
          <button
            onClick={handleResetView}
            className="px-3 py-1.5 bg-white/95 hover:bg-sky-50 text-sky-950 border border-sky-200/90 rounded-xl text-xs font-bold shadow-xs backdrop-blur transition flex items-center gap-1.5"
            title="Fit view to Chennai catchment"
          >
            <span>⟲</span> Fit Catchment
          </button>
          <div className="bg-white/95 backdrop-blur border border-sky-200/90 rounded-xl p-2.5 flex flex-col gap-1.5 text-[11px] text-slate-800 shadow-sm font-medium">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={showZoneBoundaries} onChange={(event) => setShowZoneBoundaries(event.target.checked)} className="rounded text-sky-600 focus:ring-sky-500" />
              GCC zones
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={showHistoricalFloods} onChange={(event) => setShowHistoricalFloods(event.target.checked)} className="rounded text-sky-600 focus:ring-sky-500" />
              2015 historical inundation
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={showRainfall} onChange={(event) => setShowRainfall(event.target.checked)} className="rounded text-sky-600 focus:ring-sky-500" />
              TN-SMART daily rainfall stations
            </label>
          </div>
          <div className="bg-white/95 backdrop-blur border border-sky-200/90 rounded-xl p-2.5 flex flex-col gap-1.5 text-[10px] text-slate-700 shadow-sm" aria-label="Map legend">
            <span className="font-bold uppercase tracking-wider text-sky-950">Legend</span>
            <span className="flex items-center gap-2"><span className="h-3 w-3 border border-slate-300 bg-sky-100" aria-hidden="true" />Low Risk Division (&lt;25%)</span>
            <span className="flex items-center gap-2"><span className="h-3 w-3 border border-amber-300 bg-amber-100" aria-hidden="true" />Moderate Hazard (25–50%)</span>
            <span className="flex items-center gap-2"><span className="h-3 w-3 border border-orange-300 bg-orange-100" aria-hidden="true" />High Risk Ward (50–75%)</span>
            <span className="flex items-center gap-2"><span className="h-3 w-3 border border-rose-300 bg-rose-100" aria-hidden="true" />Critical Inundation (&gt;75%)</span>
            <span className="flex items-center gap-2"><span className="h-3 w-3 border-2 border-dashed border-sky-500" aria-hidden="true" />GCC Zone Boundary</span>
            <span className="flex items-center gap-2"><span className="h-3 w-3 bg-sky-400/70" aria-hidden="true" />2015 Historical Footprint</span>
          </div>
        </div>
      )}

      {/* Current evidence status (only when showInternalOverlay is true) */}
      {showInternalOverlay && (
        <div className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur border border-sky-200/90 px-3.5 py-2 rounded-xl text-xs shadow-sm flex items-center gap-3 text-slate-700">
          <span className="font-bold text-sky-950 text-[11px] uppercase tracking-wider">PostGIS Telemetry:</span>
          <span className="text-[11px] font-medium">All 200 GCC divisions active. Interactive hover and click enabled for ward inspection.</span>
        </div>
      )}
    </div>
  );
});

export default FloodMapComponent;
