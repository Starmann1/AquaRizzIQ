import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient, WardRisk } from '../api/client';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function Forecast() {
  const [selectedZone, setSelectedZone] = useState<string>('ALL');
  const [selectedWardId, setSelectedWardId] = useState<string>('WARD-015');
  const [isCompareOpen, setIsCompareOpen] = useState<boolean>(false);
  const [compareWardId, setCompareWardId] = useState<string>('WARD-117');
  const [viewMode, setViewMode] = useState<'ward' | 'zones'>('ward');

  const { data: risks } = useQuery({
    queryKey: ['risks'],
    queryFn: apiClient.fetchRisk,
  });

  const { data: forecast, isLoading, error } = useQuery({
    queryKey: ['forecasts', selectedWardId],
    queryFn: () => apiClient.fetchForecasts(selectedWardId),
  });

  const { data: compareForecast } = useQuery({
    queryKey: ['forecasts', compareWardId],
    queryFn: () => apiClient.fetchForecasts(compareWardId),
    enabled: isCompareOpen && !!compareWardId,
  });

  // Extract unique zones
  const zones = useMemo(() => {
    const set = new Set<string>();
    (risks || []).forEach((r) => {
      if (r.zone) set.add(r.zone);
    });
    return Array.from(set).sort();
  }, [risks]);

  // Filter wards by selected zone
  const filteredWards = useMemo(() => {
    const all = [...(risks || [])].sort((a, b) =>
      a.ward_id.localeCompare(b.ward_id, undefined, { numeric: true })
    );
    if (selectedZone === 'ALL') return all;
    return all.filter((r) => r.zone === selectedZone);
  }, [risks, selectedZone]);

  // Handle Zone selection change
  const handleZoneChange = (zone: string) => {
    setSelectedZone(zone);
    if (zone !== 'ALL') {
      const firstInZone = (risks || []).find((r) => r.zone === zone);
      if (firstInZone) {
        setSelectedWardId(firstInZone.ward_id);
      }
    }
  };

  // Compute Zone Summaries for zone-wise comparison
  const zoneSummaries = useMemo(() => {
    if (!risks) return [];
    const map = new Map<
      string,
      {
        zone: string;
        totalWards: number;
        criticalCount: number;
        highCount: number;
        mediumCount: number;
        lowCount: number;
        topRiskWard: WardRisk | null;
        avgHazard: number;
      }
    >();

    for (const r of risks) {
      const zName = r.zone || 'Greater Chennai';
      if (!map.has(zName)) {
        map.set(zName, {
          zone: zName,
          totalWards: 0,
          criticalCount: 0,
          highCount: 0,
          mediumCount: 0,
          lowCount: 0,
          topRiskWard: null,
          avgHazard: 0,
        });
      }
      const entry = map.get(zName)!;
      entry.totalWards += 1;
      if (r.risk_level === 'CRITICAL') entry.criticalCount += 1;
      else if (r.risk_level === 'HIGH') entry.highCount += 1;
      else if (r.risk_level === 'MEDIUM') entry.mediumCount += 1;
      else entry.lowCount += 1;

      if (!entry.topRiskWard || (r.hazard || 0) > (entry.topRiskWard.hazard || 0)) {
        entry.topRiskWard = r;
      }
      entry.avgHazard += r.hazard || 0;
    }

    return Array.from(map.values())
      .map((e) => ({
        ...e,
        avgHazard: e.totalWards > 0 ? e.avgHazard / e.totalWards : 0,
      }))
      .sort((a, b) => b.avgHazard - a.avgHazard);
  }, [risks]);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const horizons = forecast?.forecast_horizons || {};
  const currentLevel = forecast?.current_water_level_m ?? 1.85;
  const channelDepth = forecast?.channel_depth_m ?? 3.5;
  const rainfallIntensity = forecast?.rainfall_intensity_mmh ?? 26.0;
  const dangerLevel = channelDepth * 0.85;

  const compareHorizons = compareForecast?.forecast_horizons || {};
  const compareLevel = compareForecast?.current_water_level_m ?? 1.85;
  const compareDepth = compareForecast?.channel_depth_m ?? 3.5;
  const compareRainfall = compareForecast?.rainfall_intensity_mmh ?? 26.0;
  const compareDanger = compareDepth * 0.85;

  const selectedWard = (risks || []).find((r) => r.ward_id === selectedWardId);
  const compareWard = (risks || []).find((r) => r.ward_id === compareWardId);

  return (
    <main className="mx-auto max-w-6xl space-y-6 pb-12">
      {/* Forecast Header & Controls */}
      <header className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm backdrop-blur space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-sky-950 tracking-tight">
              Near-Term Water-Level Forecasts
            </h1>
            <p className="mt-1 text-sm text-slate-600 font-medium">
              Real-time monitoring and 2-hour predictive flood forecasts across Chennai
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 rounded-xl bg-sky-50 p-1 border border-sky-200 shadow-2xs">
            <button
              type="button"
              onClick={() => setViewMode('ward')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                viewMode === 'ward'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-sky-900'
              }`}
            >
              <span>📍</span>
              <span>Ward Forecast</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('zones')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                viewMode === 'zones'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-sky-900'
              }`}
            >
              <span>🗺️</span>
              <span>All Zones Overview ({zones.length})</span>
            </button>
          </div>
        </div>

        {/* Filters & Comparison Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-sky-100">
          <div className="flex flex-wrap items-center gap-4">
            {/* Zone Selector */}
            <div className="flex items-center gap-2">
              <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                Zone:
              </label>
              <select
                value={selectedZone}
                onChange={(e) => handleZoneChange(e.target.value)}
                className="rounded-lg border border-sky-300 bg-sky-50/80 px-3 py-1.5 text-xs font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-2xs"
              >
                <option value="ALL">All Zones ({zones.length} Zones)</option>
                {zones.map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </select>
            </div>

            {/* Ward Selector */}
            <div className="flex items-center gap-2">
              <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                Ward:
              </label>
              <select
                value={selectedWardId}
                onChange={(e) => setSelectedWardId(e.target.value)}
                className="rounded-lg border border-sky-300 bg-sky-50/80 px-3 py-1.5 text-xs font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono shadow-2xs"
              >
                {filteredWards.map((r) => (
                  <option key={r.ward_id} value={r.ward_id}>
                    {r.ward_name} ({r.zone || r.ward_id})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Compare Button & Secondary Ward Selector */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsCompareOpen(!isCompareOpen)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 border shadow-2xs ${
                isCompareOpen
                  ? 'bg-amber-500 text-white border-amber-600 shadow-xs'
                  : 'bg-white text-slate-700 border-sky-300 hover:bg-sky-50'
              }`}
            >
              <span>🔄</span>
              <span>{isCompareOpen ? 'Close Comparison' : 'Compare with another Ward'}</span>
            </button>

            {isCompareOpen && (
              <div className="flex items-center gap-2 animate-in fade-in duration-150">
                <label className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                  vs Ward:
                </label>
                <select
                  value={compareWardId}
                  onChange={(e) => setCompareWardId(e.target.value)}
                  className="rounded-lg border border-amber-300 bg-amber-50/80 px-3 py-1.5 text-xs font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-amber-500 font-mono shadow-2xs"
                >
                  {[...(risks || [])]
                    .filter((r) => r.ward_id !== selectedWardId)
                    .sort((a, b) => a.ward_id.localeCompare(b.ward_id, undefined, { numeric: true }))
                    .map((r) => (
                      <option key={r.ward_id} value={r.ward_id}>
                        {r.ward_name} ({r.zone || r.ward_id})
                      </option>
                    ))}
                </select>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* VIEW MODE 1: ALL ZONES OVERVIEW */}
      {viewMode === 'zones' && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-sky-950 uppercase tracking-wider">
              Chennai Zone-Wise Flood Risk & Water Overview
            </h2>
            <span className="text-xs text-slate-500 font-medium">
              Ranked by average flood hazard across 15 GCC Zones
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {zoneSummaries.map((zs, idx) => {
              const isHigh = zs.criticalCount > 0 || zs.highCount > 0;
              return (
                <div
                  key={zs.zone}
                  className={`rounded-2xl border p-5 space-y-3.5 shadow-2xs transition-all ${
                    isHigh
                      ? 'border-rose-200 bg-linear-to-b from-rose-50/70 to-white hover:border-rose-300'
                      : 'border-sky-200 bg-linear-to-b from-sky-50/70 to-white hover:border-sky-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2.5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-400">
                          #{idx + 1}
                        </span>
                        <h3 className="text-sm font-black text-slate-900">{zs.zone}</h3>
                      </div>
                      <span className="text-[11px] text-slate-500 font-semibold">
                        {zs.totalWards} Administrative Wards
                      </span>
                    </div>

                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider border ${
                        zs.criticalCount > 0
                          ? 'bg-rose-100 text-rose-800 border-rose-300'
                          : zs.highCount > 0
                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      }`}
                    >
                      {zs.criticalCount > 0
                        ? `${zs.criticalCount} Critical`
                        : zs.highCount > 0
                        ? `${zs.highCount} High Risk`
                        : 'Stable'}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg bg-white p-2 border border-slate-100 shadow-2xs">
                      <div className="text-[10px] font-bold text-rose-600 uppercase">Critical/High</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">
                        {zs.criticalCount + zs.highCount}
                      </div>
                    </div>
                    <div className="rounded-lg bg-white p-2 border border-slate-100 shadow-2xs">
                      <div className="text-[10px] font-bold text-amber-600 uppercase">Medium</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">
                        {zs.mediumCount}
                      </div>
                    </div>
                    <div className="rounded-lg bg-white p-2 border border-slate-100 shadow-2xs">
                      <div className="text-[10px] font-bold text-emerald-600 uppercase">Low</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">
                        {zs.lowCount}
                      </div>
                    </div>
                  </div>

                  {zs.topRiskWard && (
                    <div className="rounded-xl bg-slate-50 p-2.5 text-xs border border-slate-100 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase">
                          Highest Risk Ward:
                        </span>
                        <div className="font-bold text-slate-800">
                          {zs.topRiskWard.ward_name} ({zs.topRiskWard.ward_id})
                        </div>
                      </div>
                      <span className="font-mono text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                        H: {zs.topRiskWard.hazard?.toFixed(2) ?? '--'}
                      </span>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      handleZoneChange(zs.zone);
                      setViewMode('ward');
                    }}
                    className="w-full py-2 rounded-xl text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 transition text-center shadow-2xs"
                  >
                    Inspect Zone Wards →
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* VIEW MODE 2: WARD FORECAST (+ COMPARE) */}
      {viewMode === 'ward' && (
        <>
          {/* Catchment Gauges Overview */}
          <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Water Level Gauge */}
            <div className="rounded-2xl border border-sky-200/90 bg-sky-50/90 p-5 shadow-2xs backdrop-blur space-y-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Current Water Level
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-sky-900 font-mono">
                  {currentLevel.toFixed(2)} m
                </span>
                {isCompareOpen && (
                  <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                    vs {compareLevel.toFixed(2)} m ({compareWard?.ward_name || compareWardId})
                  </span>
                )}
              </div>
              <span className="text-[11px] font-medium text-slate-500 block">
                Channel Capacity: {channelDepth.toFixed(1)}m
              </span>
            </div>

            {/* Rainfall Gauge */}
            <div className="rounded-2xl border border-sky-200/90 bg-sky-50/90 p-5 shadow-2xs backdrop-blur space-y-2">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Rainfall Intensity
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-emerald-700 font-mono">
                  {rainfallIntensity.toFixed(1)} mm/h
                </span>
                {isCompareOpen && (
                  <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                    vs {compareRainfall.toFixed(1)} mm/h
                  </span>
                )}
              </div>
              <span className="text-[11px] font-medium text-slate-500 block">
                TNSMART Live Telemetry
              </span>
            </div>

            {/* Danger Warning Level */}
            <div className="rounded-2xl border border-rose-200/90 bg-rose-50/80 p-5 shadow-2xs backdrop-blur space-y-2">
              <span className="text-xs font-bold text-rose-700 uppercase tracking-wider">
                Danger Warning Level
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-rose-700 font-mono">
                  {dangerLevel.toFixed(2)} m
                </span>
                {isCompareOpen && (
                  <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                    vs {compareDanger.toFixed(2)} m
                  </span>
                )}
              </div>
              <span className="text-[11px] font-medium text-slate-500 block">
                85% Capacity Warning Threshold
              </span>
            </div>
          </section>

          {/* Multi-Horizon Water Level Predictions */}
          <section className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm space-y-5 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-sky-950 uppercase tracking-wider">
                  Predicted Water Levels (+15, +30, +60, +120 min)
                </h2>
                <p className="text-xs text-slate-500 font-medium">
                  {isCompareOpen
                    ? `Comparing ${selectedWard?.ward_name || selectedWardId} with ${compareWard?.ward_name || compareWardId}`
                    : `Forecast progression for ${selectedWard?.ward_name || selectedWardId} (${selectedWard?.zone || 'Chennai'})`}
                </p>
              </div>

              <span className="text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-300">
                ✓ Status: Live & Calibrated
              </span>
            </div>

            {/* 4 Horizon Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(horizons).map(([key, h]: [string, any]) => {
                const compH = compareHorizons[key];
                const isHighRisk = (h.exceedance_prob ?? 0) > 0.6;
                const compHighRisk = (compH?.exceedance_prob ?? 0) > 0.6;
                const levelDiff = compH ? h.p50 - compH.p50 : 0;

                return (
                  <div
                    key={key}
                    className={`rounded-2xl border p-5 space-y-3 shadow-2xs transition ${
                      isHighRisk
                        ? 'border-rose-200 bg-rose-50/60'
                        : 'border-sky-200 bg-sky-50/60'
                    }`}
                  >
                    {/* Horizon Header */}
                    <div className="flex items-center justify-between border-b border-sky-200/70 pb-2">
                      <span className="font-mono text-sm font-black text-sky-950">
                        +{h.horizon_minutes} min
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shadow-2xs ${
                          isHighRisk
                            ? 'bg-rose-100 text-rose-800 border-rose-300'
                            : (h.exceedance_prob ?? 0) > 0.3
                            ? 'bg-amber-100 text-amber-800 border-amber-300'
                            : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                        }`}
                      >
                        {isHighRisk ? 'OVERFLOW RISK' : (h.exceedance_prob ?? 0) > 0.3 ? 'ELEVATED' : 'STABLE'}
                      </span>
                    </div>

                    {/* Primary Ward Predicted Level */}
                    <div>
                      <div className="text-[11px] font-semibold text-slate-500">
                        {isCompareOpen ? (selectedWard?.ward_name || selectedWardId) : 'Expected Water Level'}
                      </div>
                      <div className="mt-0.5 text-2xl font-black text-sky-950 font-mono">
                        {h.p50} <span className="text-xs font-normal text-slate-500">m</span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-600 mt-0.5">
                        Rise: <span className="font-bold text-emerald-700">+{h.delta_p50} m</span>
                      </div>
                    </div>

                    {/* Side-by-Side Comparison Box */}
                    {isCompareOpen && compH && (
                      <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-2.5 text-xs space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-amber-950 truncate max-w-[120px]">
                            {compareWard?.ward_name || compareWardId}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase border ${
                              compHighRisk
                                ? 'bg-rose-100 text-rose-800 border-rose-300'
                                : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                            }`}
                          >
                            {compHighRisk ? 'RISK' : 'STABLE'}
                          </span>
                        </div>
                        <div className="flex items-baseline justify-between font-mono">
                          <span className="text-base font-black text-slate-900">{compH.p50} m</span>
                          <span
                            className={`text-[10px] font-bold ${
                              levelDiff > 0 ? 'text-rose-700' : 'text-emerald-700'
                            }`}
                          >
                            {levelDiff > 0 ? `+${levelDiff.toFixed(2)}m higher` : `${levelDiff.toFixed(2)}m lower`}
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Range Box */}
                    <div className="space-y-1 rounded-xl bg-white p-2.5 text-xs font-mono border border-sky-100 shadow-2xs">
                      <div className="flex justify-between text-slate-500">
                        <span>Expected Range:</span>
                        <span className="font-semibold text-slate-800">
                          {h.p10}m – {h.p90}m
                        </span>
                      </div>
                    </div>

                    {/* Overflow Risk Probability Bar */}
                    <div className="pt-1">
                      <div className="flex justify-between text-xs mb-1 font-medium">
                        <span className="text-slate-500">Risk of Overflow:</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {((h.exceedance_prob ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            isHighRisk
                              ? 'bg-rose-500'
                              : (h.exceedance_prob ?? 0) > 0.3
                              ? 'bg-amber-500'
                              : 'bg-emerald-500'
                          }`}
                          style={{
                            width: `${Math.min(100, (h.exceedance_prob ?? 0) * 100)}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
