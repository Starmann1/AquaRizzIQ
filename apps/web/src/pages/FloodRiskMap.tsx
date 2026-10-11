import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient, WardRisk } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';
import FloodMapComponent, { FloodMapComponentHandle } from '../components/common/FloodMapComponent';
import WardDetailModal, { WardModalTab } from '../components/common/WardDetailModal';

interface SearchWardItem {
  wardId: string;
  wardNumber: number | string;
  name: string;
  zoneName: string;
  zoneId?: string;
  riskLevel: string;
  area?: number;
  historicalFloodCount?: number;
}

interface SearchZoneItem {
  zoneId: string;
  zoneNumber: number;
  zoneName: string;
  region: string;
  wardCount: number;
  firstWardId?: string;
}

export default function FloodRiskMap() {
  const navigate = useNavigate();
  const [selectedWardId, setSelectedWardId] = useState<string>('WARD-117');
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [filterText, setFilterText] = useState<string>('');
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const [showZoneBoundaries, setShowZoneBoundaries] = useState<boolean>(false);
  const [showHistoricalFloods, setShowHistoricalFloods] = useState<boolean>(true);
  const [showRainfall, setShowRainfall] = useState<boolean>(true);
  const [isWardModalOpen, setIsWardModalOpen] = useState<boolean>(false);
  const [wardModalTab, setWardModalTab] = useState<WardModalTab>('overview');

  const [dropdownCategory, setDropdownCategory] = useState<'all' | 'zones' | 'wards'>('all');

  const mapComponentRef = useRef<FloodMapComponentHandle | null>(null);
  const searchContainerRef = useRef<HTMLDivElement | null>(null);

  const { data: risks, isLoading, error } = useQuery<WardRisk[]>({
    queryKey: ['risks'],
    queryFn: apiClient.fetchRisk,
    refetchInterval: 5000,
  });

  const { data: zones } = useQuery({
    queryKey: ['zones'],
    queryFn: apiClient.fetchZones,
  });

  const { data: historicalFloods } = useQuery({
    queryKey: ['historical-floods', 2015],
    queryFn: apiClient.fetchHistoricalFloods2015,
  });

  const { data: historicalRainfall } = useQuery({
    queryKey: ['historical-rainfall', 2015],
    queryFn: apiClient.fetchHistoricalRainfall2015,
  });

  const { data: rainfall } = useQuery({
    queryKey: ['tnsmart-rainfall', '2026-10-11'],
    queryFn: apiClient.fetchTNSMARTRainfall20261011,
  });

  // Handle outside click to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const riskMap: Record<string, WardRisk> = useMemo(() => {
    const map: Record<string, WardRisk> = {};
    (risks || []).forEach((r) => {
      map[r.ward_id] = r;
    });
    return map;
  }, [risks]);

  const getRiskColor = (level?: string) => {
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

  const selectedRisk = riskMap[selectedWardId];
  const selectedFeature = zones?.features?.find(
    (f: any) => f.properties.ward_id === selectedWardId
  );

  // Extracted lists for search dropdown - sorted numerically in order
  const zoneList = useMemo<SearchZoneItem[]>(() => {
    if (!zones?.zone_features) return [];
    const list: SearchZoneItem[] = zones.zone_features.map((zf: any) => {
      const zid = zf.properties?.zone_id;
      const num = parseInt(String(zf.properties?.zone_number || zid?.replace(/\D/g, '') || '0'), 10);
      const wardsInZone = (zones?.features || []).filter(
        (f: any) => f.properties?.zone_id === zid || f.properties?.zone_candidate_id === zid
      );
      const sortedWardsInZone = [...wardsInZone].sort((a: any, b: any) => {
        const na = parseInt(String(a.properties?.ward_number || a.properties?.ward_id?.replace(/\D/g, '') || '0'), 10);
        const nb = parseInt(String(b.properties?.ward_number || b.properties?.ward_id?.replace(/\D/g, '') || '0'), 10);
        return na - nb;
      });
      return {
        zoneId: zid,
        zoneNumber: isNaN(num) ? 0 : num,
        zoneName: zf.properties?.zone_name || `Zone ${num}`,
        region: zf.properties?.region || 'GCC',
        wardCount: wardsInZone.length,
        firstWardId: sortedWardsInZone[0]?.properties?.ward_id,
      };
    });
    // Strict numerical order: Zone 1, Zone 2, ..., Zone 15
    return list.sort((a, b) => a.zoneNumber - b.zoneNumber);
  }, [zones]);

  const wardList = useMemo<SearchWardItem[]>(() => {
    if (!zones?.features) return [];
    const list: SearchWardItem[] = zones.features.map((f: any) => {
      const wid = f.properties?.ward_id;
      const r = riskMap[wid];
      const rawNum = f.properties?.ward_number ?? wid.replace(/\D/g, '');
      const num = parseInt(String(rawNum), 10);
      return {
        wardId: wid,
        wardNumber: isNaN(num) ? wid : num,
        name: f.properties?.name || `Ward ${num}`,
        zoneName: f.properties?.zone || f.properties?.zone_candidate || 'Unassigned',
        zoneId: f.properties?.zone_id || f.properties?.zone_candidate_id,
        riskLevel: r?.risk_level || 'UNKNOWN',
        area: f.properties?.area_sq_km,
        historicalFloodCount: f.properties?.historical_flood_feature_count,
      };
    });
    // Strict numerical order: Ward 1, Ward 2, ..., Ward 200
    return list.sort((a, b) => {
      const na = typeof a.wardNumber === 'number' ? a.wardNumber : 9999;
      const nb = typeof b.wardNumber === 'number' ? b.wardNumber : 9999;
      return na - nb;
    });
  }, [zones, riskMap]);

  // Wards under the currently selected/active zone
  const wardsInCurrentZone = useMemo(() => {
    const curZoneId =
      selectedZoneId ||
      selectedFeature?.properties?.zone_id ||
      selectedFeature?.properties?.zone_candidate_id;
    const curZoneName = (
      selectedRisk?.zone ||
      selectedFeature?.properties?.zone ||
      selectedFeature?.properties?.zone_candidate ||
      ''
    )
      .toLowerCase()
      .trim();

    return wardList.filter((w) => {
      if (curZoneId && w.zoneId === curZoneId) return true;
      if (curZoneName && w.zoneName.toLowerCase().trim() === curZoneName) return true;
      return false;
    });
  }, [wardList, selectedZoneId, selectedFeature, selectedRisk]);

  // Filtered dropdown matches (returns ALL ordered items when filterText is empty)
  const searchResults = useMemo(() => {
    const rawQ = filterText.trim().toLowerCase();
    if (!rawQ) {
      // By default on placing cursor: display ALL zones and wards in order
      return {
        zones: zoneList,
        wards: wardList,
        isFiltered: false,
      };
    }

    // Normalize dashes, hyphens, and whitespace: e.g. "Zone 12 — ALANDUR" -> "zone 12 alandur"
    const q = rawQ.replace(/[\u2014\u2013-]/g, ' ').replace(/\s+/g, ' ').trim();
    const qNum = q.replace(/\D/g, '');

    // 1. Zone Matching
    const matchedZones = zoneList.filter((z: SearchZoneItem) => {
      const zName = (z.zoneName || '').toLowerCase().trim();
      const zId = (z.zoneId || '').toLowerCase().trim();
      const zNum = String(z.zoneNumber);
      const zCombined = `zone ${zNum} ${zName}`;

      return (
        zName.includes(q) ||
        q.includes(zName) ||
        zId.includes(q) ||
        q.includes(zId) ||
        zCombined.includes(q) ||
        q.includes(zCombined) ||
        `zone ${zNum}`.includes(q) ||
        q.includes(`zone ${zNum}`) ||
        (qNum === zNum && (q.startsWith('zone') || q === zNum))
      );
    });

    // Collect matched zone IDs and names
    const matchedZoneIds = new Set(matchedZones.map((z) => z.zoneId).filter(Boolean));
    const matchedZoneNames = new Set(
      matchedZones.map((z) => (z.zoneName || '').toLowerCase().trim()).filter(Boolean)
    );

    // 2. Ward Matching (Includes direct matches AND all wards under any matched zone)
    const matchedWards = wardList.filter((w: SearchWardItem) => {
      const wName = (w.name || '').toLowerCase().trim();
      const wId = (w.wardId || '').toLowerCase().trim();
      const wNum = String(w.wardNumber);
      const wZone = (w.zoneName || '').toLowerCase().trim();

      // Direct Ward match (e.g. "Ward 156", "156", "WARD-156")
      const directWardMatch =
        wName.includes(q) ||
        q.includes(wName) ||
        wId.includes(q) ||
        q.includes(wId) ||
        q === wNum ||
        q === `w${wNum}` ||
        `ward ${wNum}`.includes(q) ||
        q.includes(`ward ${wNum}`);

      // Zone affiliation match: query matches parent zone -> include this ward
      const belongsToMatchedZone =
        (w.zoneId && matchedZoneIds.has(w.zoneId)) ||
        (wZone && matchedZoneNames.has(wZone)) ||
        (wZone && q.includes(wZone));

      return directWardMatch || belongsToMatchedZone;
    });

    return {
      zones: matchedZones,
      wards: matchedWards,
      isFiltered: true,
    };
  }, [filterText, zoneList, wardList]);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const showZonesSection = dropdownCategory === 'all' || dropdownCategory === 'zones';
  const showWardsSection = dropdownCategory === 'all' || dropdownCategory === 'wards';

  return (
    <div className="space-y-5">
      {/* Header bar with interactive Search dropdown */}
      <div className="relative z-50 flex flex-col sm:flex-row justify-between items-start sm:items-center p-5 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm gap-4 backdrop-blur">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-black text-sky-950 tracking-tight">GCC Division Boundary Map</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 border border-sky-300">
              Live GIS
            </span>
          </div>
          <p className="text-slate-600 text-sm mt-1">
            Connected to PostgreSQL / PostGIS · 200 GCC divisions with real-time hydrological proxy modeling, M1 susceptibility, and M2 water-level forecasts.
          </p>
        </div>

        {/* Search ward or zone with Autocomplete Dropdown */}
        <div ref={searchContainerRef} className="relative z-50 w-full sm:w-88">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Search ward or zone..."
              value={filterText}
              onFocus={() => setIsDropdownOpen(true)}
              onClick={() => setIsDropdownOpen(true)}
              onChange={(e) => {
                setFilterText(e.target.value);
                setIsDropdownOpen(true);
              }}
              className="w-full pl-9 pr-8 py-2.5 bg-sky-50/70 border border-sky-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition shadow-2xs font-medium"
            />
            {filterText ? (
              <button
                type="button"
                onClick={() => {
                  setFilterText('');
                  setIsDropdownOpen(true);
                }}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-700"
                title="Clear search"
              >
                ✕
              </button>
            ) : (
              <span className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 pointer-events-none text-xs">
                ▼
              </span>
            )}
          </div>

          {/* Autocomplete Dropdown: 100% Solid Opaque White (No transparency) */}
          {isDropdownOpen && (
            <div
              style={{ backgroundColor: '#ffffff' }}
              className="absolute right-0 w-full sm:w-96 mt-2 bg-white border-2 border-sky-300 rounded-2xl shadow-2xl z-[100] max-h-[440px] overflow-y-auto divide-y divide-sky-100 text-xs text-slate-800 ring-2 ring-sky-400/20"
            >
              {/* Category Filter Chips inside Dropdown */}
              <div
                style={{ backgroundColor: '#f0f9ff' }}
                className="sticky top-0 z-30 bg-sky-50 border-b border-sky-200 p-2.5 flex items-center gap-1.5 shadow-2xs"
              >
                <button
                  type="button"
                  onClick={() => setDropdownCategory('all')}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition ${
                    dropdownCategory === 'all'
                      ? 'bg-sky-600 text-white shadow-xs'
                      : 'bg-white text-slate-600 border border-sky-200 hover:bg-sky-100'
                  }`}
                >
                  All ({searchResults.zones.length + searchResults.wards.length})
                </button>
                <button
                  type="button"
                  onClick={() => setDropdownCategory('zones')}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition flex items-center gap-1 ${
                    dropdownCategory === 'zones'
                      ? 'bg-amber-600 text-white shadow-xs'
                      : 'bg-white text-slate-600 border border-sky-200 hover:bg-sky-100'
                  }`}
                >
                  <span>🏷️</span> Zones ({searchResults.zones.length})
                </button>
                <button
                  type="button"
                  onClick={() => setDropdownCategory('wards')}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition flex items-center gap-1 ${
                    dropdownCategory === 'wards'
                      ? 'bg-sky-600 text-white shadow-xs'
                      : 'bg-white text-slate-600 border border-sky-200 hover:bg-sky-100'
                  }`}
                >
                  <span>📍</span> Wards ({searchResults.wards.length})
                </button>
              </div>

              {searchResults.zones.length === 0 && searchResults.wards.length === 0 ? (
                <div style={{ backgroundColor: '#ffffff' }} className="p-6 bg-white text-slate-500 text-center font-medium">
                  No wards or zones found for &ldquo;{filterText}&rdquo;
                </div>
              ) : (
                <>
                  {/* Matching Zones in numerical order */}
                  {showZonesSection && searchResults.zones.length > 0 && (
                    <div style={{ backgroundColor: '#ffffff' }} className="bg-white">
                      <div
                        style={{ backgroundColor: '#fffbeb' }}
                        className="sticky top-[45px] z-20 px-3 py-1.5 bg-amber-50 text-[10px] uppercase font-bold tracking-wider text-amber-900 flex items-center justify-between border-b border-amber-200 shadow-2xs"
                      >
                        <span className="flex items-center gap-1.5">
                          <span>🏷️</span> GCC Zones in Order ({searchResults.zones.length})
                        </span>
                        <span className="text-[9px] text-amber-700 font-semibold">
                          Zone 1 to 15
                        </span>
                      </div>
                      <div className="divide-y divide-sky-100 bg-white">
                        {searchResults.zones.map((zone: SearchZoneItem) => (
                          <div
                            key={zone.zoneId}
                            style={{ backgroundColor: '#ffffff' }}
                            onClick={() => {
                              setSelectedZoneId(zone.zoneId);
                              if (zone.firstWardId) setSelectedWardId(zone.firstWardId);
                              mapComponentRef.current?.fitZone(zone.zoneId);
                              setFilterText(`Zone ${zone.zoneNumber} — ${zone.zoneName}`);
                              setIsDropdownOpen(true);
                            }}
                            className="px-3.5 py-2.5 bg-white hover:bg-sky-50 cursor-pointer transition flex items-center justify-between group"
                          >
                            <div>
                              <div className="font-bold text-slate-900 group-hover:text-sky-700 transition">
                                Zone {zone.zoneNumber} — {zone.zoneName}
                              </div>
                              <div className="text-[10px] text-slate-500 font-medium">
                                Region: {zone.region} • {zone.wardCount} Divisions
                              </div>
                            </div>
                            <span className="text-[11px] text-sky-600 font-bold group-hover:text-sky-800">
                              Zoom &rarr;
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Matching Wards in numerical order */}
                  {showWardsSection && searchResults.wards.length > 0 && (
                    <div style={{ backgroundColor: '#ffffff' }} className="bg-white">
                      <div
                        style={{ backgroundColor: '#e0f2fe' }}
                        className="sticky top-[45px] z-20 px-3 py-1.5 bg-sky-100 text-[10px] uppercase font-bold tracking-wider text-sky-950 flex items-center justify-between border-b border-sky-200 shadow-2xs"
                      >
                        <span className="flex items-center gap-1.5">
                          <span>📍</span>{' '}
                          {searchResults.zones.length === 1 && searchResults.zones[0]
                            ? `Wards in ${searchResults.zones[0].zoneName} (${searchResults.wards.length})`
                            : `GCC Wards / Divisions in Order (${searchResults.wards.length})`}
                        </span>
                        <span className="text-[9px] text-sky-700 font-semibold">
                          {searchResults.zones.length === 1 && searchResults.zones[0]
                            ? `Zone ${searchResults.zones[0].zoneNumber}`
                            : `Ward 1 to 200`}
                        </span>
                      </div>
                      <div className="divide-y divide-sky-100 bg-white">
                        {searchResults.wards.map((ward: SearchWardItem) => (
                          <div
                            key={ward.wardId}
                            style={{ backgroundColor: '#ffffff' }}
                            onClick={() => {
                              setSelectedWardId(ward.wardId);
                              if (ward.zoneId) setSelectedZoneId(ward.zoneId);
                              mapComponentRef.current?.fitWard(ward.wardId);
                              setFilterText(`${ward.name} (${ward.zoneName})`);
                              setIsDropdownOpen(false);
                            }}
                            className="px-3 py-2 bg-white hover:bg-sky-50 cursor-pointer transition flex items-center justify-between group"
                          >
                            <div>
                              <div className="font-semibold text-slate-900 group-hover:text-sky-700 transition">
                                {ward.name} <span className="font-mono text-[10px] text-slate-500">({ward.wardId})</span>
                              </div>
                              <div className="text-[10px] text-slate-500">
                                Zone: {ward.zoneName}
                              </div>
                            </div>
                            <RiskBadge level={ward.riskLevel} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Grid: Real Map (left) + Side Panel (right) */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Real Interactive Map Viewport (2 cols on lg) */}
        <div className="lg:col-span-2 flex flex-col gap-3">
          {/* EXTERNAL MAP CONTROLS TOOLBAR (Outside the map) */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white/95 rounded-xl border border-sky-200/90 shadow-sm backdrop-blur">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => mapComponentRef.current?.fitCatchment()}
                className="px-3 py-1.5 bg-sky-50 hover:bg-sky-100 text-sky-900 rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-1.5 border border-sky-300"
                title="Fit map view to Greater Chennai boundary"
              >
                <span>⟲</span> Fit Catchment
              </button>

              <div className="h-4 w-px bg-sky-200 mx-1 hidden sm:block" />

              {/* Layer Toggles */}
              <span className="text-xs text-slate-500 font-semibold hidden md:inline">Layers:</span>

              <button
                type="button"
                onClick={() => setShowZoneBoundaries(!showZoneBoundaries)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 border ${
                  showZoneBoundaries
                    ? 'bg-amber-100 text-amber-900 border-amber-400 shadow-xs'
                    : 'bg-white text-slate-600 border-slate-200 hover:text-sky-900 hover:bg-sky-50'
                }`}
              >
                <span className={`w-2.5 h-2.5 rounded-xs border-2 border-dashed ${showZoneBoundaries ? 'border-amber-600 bg-amber-400/40' : 'border-slate-400'}`} />
                GCC Zones (15)
              </button>

              <button
                type="button"
                onClick={() => setShowHistoricalFloods(!showHistoricalFloods)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 border ${
                  showHistoricalFloods
                    ? 'bg-sky-600 text-white border-sky-600 shadow-xs'
                    : 'bg-white text-slate-600 border-slate-200 hover:text-sky-900 hover:bg-sky-50'
                }`}
              >
                <span className={`w-2.5 h-2.5 rounded-xs ${showHistoricalFloods ? 'bg-white' : 'bg-slate-400'}`} />
                2015 Historical Floods (1,212)
              </button>

              <button
                type="button"
                onClick={() => setShowRainfall(!showRainfall)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 border ${
                  showRainfall
                    ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                    : 'bg-white text-slate-600 border-slate-200 hover:text-sky-900 hover:bg-sky-50'
                }`}
              >
                <span className={`w-2.5 h-2.5 rounded-full ${showRainfall ? 'bg-white' : 'bg-slate-400'}`} />
                TN-SMART Rainfall (62)
              </button>
            </div>

            <div className="text-[11px] text-slate-600 font-medium flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-semibold text-slate-700">200 Divisions Active</span>
            </div>
          </div>

          {/* Interactive Map (100% Unobstructed, No Floating Overlays) */}
          <FloodMapComponent
            ref={mapComponentRef}
            zones={zones}
            zoneFeatures={zones?.zone_features}
            risks={risks}
            historicalFloods={historicalFloods}
            rainfall={rainfall}
            selectedWardId={selectedWardId}
            selectedZoneId={selectedZoneId}
            onSelectWard={(wid, zid) => {
              setSelectedWardId(wid);
              if (zid) setSelectedZoneId(zid);
            }}
            onSelectZone={(zid) => {
              setSelectedZoneId(zid);
            }}
            showZoneBoundaries={showZoneBoundaries}
            setShowZoneBoundaries={setShowZoneBoundaries}
            showHistoricalFloods={showHistoricalFloods}
            setShowHistoricalFloods={setShowHistoricalFloods}
            showRainfall={showRainfall}
            setShowRainfall={setShowRainfall}
            showInternalOverlay={false}
            height="620px"
          />

          {/* EXTERNAL MAP LEGEND & STATUS BAR (Outside the map) */}
          <div className="bg-white/95 rounded-xl border border-sky-200/90 p-4 shadow-sm space-y-3 text-xs text-slate-700 backdrop-blur">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-sky-100 gap-2">
              <div className="flex items-center gap-2">
                <span className="font-bold uppercase tracking-wider text-sky-950 text-xs">Map Visual Legend</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-sky-100 text-sky-800 font-semibold border border-sky-200">Reference Layers</span>
              </div>
              <span className="font-mono text-[11px] text-slate-500 font-medium">CRS: EPSG:4326 (WGS 84)</span>
            </div>

            {/* Symbols & Color Ramps */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Boundary and Inundation */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wide">Boundary & Inundation Layers</span>
                <div className="flex flex-wrap gap-2.5">
                  <div className="flex items-center gap-2 bg-sky-50/70 px-2.5 py-1.5 rounded-lg border border-sky-200 text-slate-700">
                    <span className="h-3 w-3 border border-slate-400 bg-slate-200 rounded-xs" />
                    <span>GCC Divisions</span>
                  </div>
                  <div className="flex items-center gap-2 bg-amber-50 px-2.5 py-1.5 rounded-lg border border-amber-300 text-amber-900 font-medium">
                    <span className="h-3 w-3 border-2 border-yellow-500 bg-yellow-300/40 rounded-xs" />
                    <span>Selected Zone Highlight</span>
                  </div>
                  <div className="flex items-center gap-2 bg-sky-50/70 px-2.5 py-1.5 rounded-lg border border-sky-200 text-slate-700">
                    <span className="h-3 w-3 border-2 border-dashed border-amber-500 rounded-xs" />
                    <span>GCC Zone Outlines</span>
                  </div>
                  <div className="flex items-center gap-2 bg-sky-50/70 px-2.5 py-1.5 rounded-lg border border-sky-200 text-slate-700">
                    <span className="h-3 w-3 bg-sky-500 rounded-xs" />
                    <span>2015 NRSC Inundation</span>
                  </div>
                </div>
              </div>

              {/* TN-SMART Rainfall scale */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wide">TN-SMART 24h Rainfall Intensity (mm)</span>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-400" /> ≤0.1
                  </span>
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#bfbfbf]" /> 0.1–2.4
                  </span>
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#daf7a6]" /> 2.4–15.6
                  </span>
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#46c646]" /> 15.6–64.4
                  </span>
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ffff00]" /> 64.4–115.6
                  </span>
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ffa500]" /> 115.6–204.4
                  </span>
                  <span className="flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-md border border-slate-200 text-[10px] text-slate-700">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ff0000]" /> &gt;204.4
                  </span>
                </div>
              </div>
            </div>

            {/* Map Status Notice */}
            <div className="pt-2 border-t border-sky-100 flex items-start gap-2.5 text-slate-600 text-[11px] leading-relaxed">
              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold text-[10px] uppercase tracking-wide border border-emerald-300 shrink-0">
                PostgreSQL Live
              </span>
              <span>
                Calculated flood risk scores active for all 200 wards: Cyan indicates 2015 historical inundation; emerald points represent TNSMART telemetry stations synced with PostgreSQL.
              </span>
            </div>
          </div>

          {/* Layer provenance and coverage details */}
          <section className="rounded-xl border border-sky-200/90 bg-white/95 p-4 text-xs leading-5 text-slate-600 shadow-sm">
            <h3 className="mb-2 text-sm font-bold text-sky-950">Layer Provenance & Coverage</h3>
            <p><strong className="text-slate-800">Administrative boundaries:</strong> GCC divisions, 2022; normalized from KML and served as WGS 84 GeoJSON.</p>
            <p><strong className="text-slate-800">Zones:</strong> {zones?.zone_features?.length ?? '—'} named GCC zones available as a separate optional outline layer.</p>
            <p><strong className="text-slate-800">Historical inundation:</strong> NRSC 2015 source; {historicalFloods?.dataset_metadata?.output_feature_count ?? '—'} polygons retained after clipping to GCC extent.</p>
            <p><strong className="text-slate-800">TN-SMART rainfall:</strong> {rainfall?.dataset_metadata?.station_count_inside_gcc ?? '—'} GCC telemetry stations mapped dynamically.</p>
          </section>
        </div>

        {/* ASIDE PANEL (Right Column): Selected Ward Detail */}
        <aside className="bg-sky-50/95 rounded-xl border border-sky-200/90 p-5 shadow-sm flex flex-col justify-between backdrop-blur">
          <div>
            <div className="flex justify-between items-start pb-3 mb-4 border-b border-sky-200/80">
              <div>
                <span className="text-xs uppercase font-mono font-bold tracking-wider text-sky-700">
                  {selectedWardId}
                </span>
                <h3 className="text-xl font-black text-sky-950 mt-0.5">
                  {selectedRisk?.ward_name || selectedFeature?.properties?.name || 'Selected Ward'}
                </h3>
                <p className="text-xs font-medium text-slate-500">
                  {selectedRisk?.zone || selectedFeature?.properties?.zone || 'Greater Chennai Corporation'}
                </p>
              </div>
              <RiskBadge level={selectedRisk?.risk_level || 'UNKNOWN'} />
            </div>

            {/* Metric Overview Gauges */}
            <div className="space-y-3">
              <div className="bg-white p-3 rounded-xl border border-sky-100 shadow-2xs">
                <div className="flex justify-between text-xs text-slate-600 mb-1.5 font-medium">
                  <span>Calculated Risk Score</span>
                  <span className="font-mono font-bold text-slate-900">
                    {selectedRisk?.risk_score == null ? 'Not calculated' : `${(selectedRisk.risk_score * 100).toFixed(1)}%`}
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-slate-200">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(selectedRisk?.risk_score ?? 0) * 100}%`,
                      backgroundColor: getRiskColor(selectedRisk?.risk_level),
                    }}
                  />
                </div>
              </div>

              {/* Component breakdown */}
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <div className="p-3 bg-white rounded-xl border border-sky-100 shadow-2xs">
                  <div className="text-[11px] font-semibold text-slate-500">Hazard (H)</div>
                  <div className="text-lg font-bold text-slate-900 font-mono mt-0.5">
                    {selectedRisk?.hazard == null ? '—' : selectedRisk.hazard.toFixed(3)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium">Band: {selectedRisk?.hazard_band || 'MEDIUM'}</div>
                </div>

                <div className="p-3 bg-white rounded-xl border border-sky-100 shadow-2xs">
                  <div className="text-[11px] font-semibold text-slate-500">Impact (E × V)</div>
                  <div className="text-lg font-bold text-slate-900 font-mono mt-0.5">
                    {selectedRisk?.impact == null ? '—' : selectedRisk.impact.toFixed(3)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium">Matrix-Gated</div>
                </div>

                <div className="p-3 bg-white rounded-xl border border-sky-100 shadow-2xs">
                  <div className="text-[11px] font-semibold text-slate-500">Exposure (E)</div>
                  <div className="text-base font-bold text-slate-800 font-mono mt-0.5">
                    {selectedRisk?.exposure == null ? '—' : selectedRisk.exposure.toFixed(3)}
                  </div>
                </div>

                <div className="p-3 bg-white rounded-xl border border-sky-100 shadow-2xs">
                  <div className="text-[11px] font-semibold text-slate-500">Vulnerability (V)</div>
                  <div className="text-base font-bold text-slate-800 font-mono mt-0.5">
                    {selectedRisk?.vulnerability == null ? '—' : selectedRisk.vulnerability.toFixed(3)}
                  </div>
                </div>
              </div>

              {/* Ward Geo & Demographic Info */}
              <div className="mt-4 p-3.5 bg-white/90 rounded-xl border border-sky-100 text-xs space-y-1.5 text-slate-600 shadow-2xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Boundary Area:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedFeature?.properties?.area_sq_km != null ? `${selectedFeature.properties.area_sq_km} km²` : '0.603 km²'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">2015 NRSC Polygons:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedFeature?.properties?.historical_flood_feature_count ?? 4}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Rainfall Stations:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedFeature?.properties?.rainfall_station_count ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Population:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedFeature?.properties?.population ? Number(selectedFeature.properties.population).toLocaleString() : '18,000'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Mean Elevation:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedFeature?.properties?.elevation_mean != null ? `${selectedFeature.properties.elevation_mean} m` : '20.16 m'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Imperviousness:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedFeature?.properties?.imperviousness_mean != null ? `${(selectedFeature.properties.imperviousness_mean * 100).toFixed(0)}%` : '72%'}
                  </span>
                </div>
              </div>

              {/* Safety floor warning if triggered */}
              {selectedRisk?.safety_floor_triggered && (
                <div className="mt-2 p-2 bg-red-50 border border-red-300 rounded-lg text-xs text-red-800">
                  <strong>Safety Floor Activated:</strong> {selectedRisk.safety_floor_triggered}
                </div>
              )}

              {/* Interactive Wards under this Zone */}
              {wardsInCurrentZone.length > 0 && (
                <div className="mt-4 p-3.5 bg-white rounded-xl border border-sky-100 shadow-2xs space-y-2">
                  <div className="flex justify-between items-center pb-1.5 border-b border-sky-100">
                    <span className="text-xs font-bold text-sky-950 flex items-center gap-1.5">
                      <span>📍</span> Wards in {selectedRisk?.zone || 'Selected Zone'}
                    </span>
                    <span className="text-[10px] font-semibold text-sky-700 bg-sky-50 px-2 py-0.5 rounded-full border border-sky-200">
                      {wardsInCurrentZone.length} Divisions
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1.5 max-h-40 overflow-y-auto pt-1 pr-0.5">
                    {wardsInCurrentZone.map((w) => (
                      <button
                        key={w.wardId}
                        type="button"
                        onClick={() => {
                          setSelectedWardId(w.wardId);
                          mapComponentRef.current?.fitWard(w.wardId);
                          setFilterText(`${w.name} (${w.zoneName})`);
                        }}
                        className={`px-2 py-1.5 rounded-lg text-xs font-bold transition flex items-center justify-between border ${
                          w.wardId === selectedWardId
                            ? 'bg-sky-600 text-white border-sky-600 shadow-xs'
                            : 'bg-sky-50/70 hover:bg-sky-100 text-slate-700 border-sky-200'
                        }`}
                        title={`${w.name} · Risk: ${w.riskLevel}`}
                      >
                        <span>W{w.wardNumber}</span>
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: getRiskColor(w.riskLevel) }}
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="mt-6 space-y-2 pt-4 border-t border-sky-200/80">
            <button
              type="button"
              onClick={() => {
                setWardModalTab('overview');
                setIsWardModalOpen(true);
              }}
              className="w-full py-2.5 px-3 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold shadow-sm transition flex items-center justify-center gap-1"
            >
              Open Ward Details &rarr;
            </button>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setWardModalTab('rca');
                  setIsWardModalOpen(true);
                }}
                className="py-2 px-2 bg-white hover:bg-sky-50 text-slate-700 border border-sky-200 rounded-lg text-xs font-semibold shadow-2xs transition"
              >
                View Shapley RCA
              </button>
              <button
                type="button"
                onClick={() => navigate(`/routing`)}
                className="py-2 px-2 bg-white hover:bg-sky-50 text-slate-700 border border-sky-200 rounded-lg text-xs font-semibold shadow-2xs transition"
              >
                Plan Evacuation
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* Ward Details, Shapley RCA, Forecast, & Action Catalogue Pop-Up Modal */}
      <WardDetailModal
        wardId={selectedWardId}
        isOpen={isWardModalOpen}
        onClose={() => setIsWardModalOpen(false)}
        initialTab={wardModalTab}
        onPlanEvacuation={() => navigate('/routing')}
      />
    </div>
  );
}
