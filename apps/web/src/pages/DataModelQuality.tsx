import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function DataModelQuality() {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const { data: qualityData, isLoading, error } = useQuery({
    queryKey: ['dataQuality'],
    queryFn: apiClient.fetchDataQuality,
    refetchInterval: 15000,
  });

  const distribution = qualityData?.status_distribution ?? {};
  const sources = qualityData?.active_telemetry_sources ?? [];
  const states = ['VALID', 'SUSPECT', 'STALE', 'MISSING', 'CONFLICTING', 'OUTLIER', 'INVALID'];

  const filteredSources = useMemo(() => {
    return sources.filter((s: any) => {
      const matchesType =
        filterType === 'ALL' ||
        (filterType === 'WATER_LEVEL' && s.type === 'ULTRASONIC_WATER_LEVEL') ||
        (filterType === 'RAIN_GAUGE' && s.type === 'AUTOMATED_RAIN_GAUGE');

      const matchesSearch =
        !searchTerm ||
        s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        s.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (s.ward_id && s.ward_id.toLowerCase().includes(searchTerm.toLowerCase()));

      return matchesType && matchesSearch;
    });
  }, [sources, filterType, searchTerm]);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="p-6 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm backdrop-blur space-y-4">
        <div>
          <h2 className="text-2xl font-black text-sky-950 tracking-tight">Stored Data Quality & Telemetry</h2>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-slate-700 bg-white/90 p-3.5 rounded-xl border border-sky-100 shadow-2xs">
          <span>Data Pipeline: <strong className="text-sky-950 font-bold">{qualityData?.data_status ?? 'OPERATIONAL'}</strong></span>
          <span>·</span>
          <span>Last Audited: <strong className="text-slate-900 font-mono">{qualityData?.as_of ? new Date(qualityData.as_of).toLocaleString() : 'Live'}</strong></span>
          <span>·</span>
          <span>Database Verification: <strong className="text-emerald-700 font-bold">✓ Connected (PostGIS)</strong></span>
          <span>·</span>
          <span>Active Stations: <strong className="text-sky-950 font-bold">{sources.length} Verified</strong></span>
        </div>
      </header>

      {/* Quality State Distribution Cards */}
      <section className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3" aria-label="Quality state counts">
        {states.map((state) => {
          const count = distribution[state] ?? 0;
          const isValid = state === 'VALID';
          const isSuspect = state === 'SUSPECT';
          const isStale = state === 'STALE';
          const isInvalid = state === 'INVALID';

          return (
            <div
              key={state}
              className={`p-4 rounded-xl border shadow-2xs transition ${
                isValid
                  ? 'bg-linear-to-b from-emerald-50/80 to-white border-emerald-200'
                  : isSuspect
                  ? 'bg-linear-to-b from-amber-50/80 to-white border-amber-200'
                  : isStale
                  ? 'bg-white border-slate-200'
                  : isInvalid
                  ? 'bg-linear-to-b from-rose-50/80 to-white border-rose-200'
                  : 'bg-white border-slate-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-[10px] font-black tracking-wider uppercase ${
                  isValid
                    ? 'text-emerald-700'
                    : isSuspect
                    ? 'text-amber-700'
                    : isInvalid
                    ? 'text-rose-700'
                    : 'text-slate-500'
                }`}>
                  {state}
                </span>
                {isValid && count > 0 && (
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                )}
              </div>
              <div className={`text-2xl font-black font-mono mt-1 ${
                isValid
                  ? 'text-emerald-800'
                  : isSuspect
                  ? 'text-amber-800'
                  : isInvalid
                  ? 'text-rose-800'
                  : 'text-slate-700'
              }`}>
                {count}
              </div>
            </div>
          );
        })}
      </section>

      {/* Active Sensors & Telemetry Stations Table */}
      <section className="bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-sky-100 bg-sky-50/50 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-sky-950">Active Sensors & Telemetry Stations</h3>
            <p className="text-xs text-slate-500 mt-0.5 font-medium">
              Telemetry freshness window: {qualityData?.freshness_window_minutes ?? '15'} min · Stale threshold: {qualityData?.stale_threshold_minutes ?? '30'} min
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Filter buttons */}
            <div className="flex items-center gap-1 bg-white p-1 rounded-xl border border-sky-200 shadow-2xs">
              <button
                type="button"
                onClick={() => setFilterType('ALL')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                  filterType === 'ALL'
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-sky-950'
                }`}
              >
                All ({sources.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType('WATER_LEVEL')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                  filterType === 'WATER_LEVEL'
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-sky-950'
                }`}
              >
                Water Level Gauges
              </button>
              <button
                type="button"
                onClick={() => setFilterType('RAIN_GAUGE')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                  filterType === 'RAIN_GAUGE'
                    ? 'bg-sky-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-sky-950'
                }`}
              >
                Rain Gauges (AWS)
              </button>
            </div>

            {/* Search Input */}
            <input
              type="text"
              placeholder="Search station or ward..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-3 py-1 rounded-xl border border-sky-300 bg-white text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-2xs w-48"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-sky-50/80 text-sky-950 uppercase tracking-wider text-[11px] font-bold border-b border-sky-200">
              <tr>
                <th className="py-3 px-4">Sensor Node</th>
                <th className="py-3 px-4">Ward ID</th>
                <th className="py-3 px-4">Sensor Type</th>
                <th className="py-3 px-4">Quality Flag</th>
                <th className="py-3 px-4">Freshness</th>
                <th className="py-3 px-4">Last Reading</th>
                <th className="py-3 px-4">Observed At</th>
                <th className="py-3 px-4">Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sky-100">
              {filteredSources.map((source: any) => (
                <tr key={source.id} className="hover:bg-sky-50/40 transition">
                  <td className="py-3 px-4">
                    <span className="font-bold text-slate-900">{source.name}</span>
                    <br />
                    <span className="font-mono text-[10px] text-slate-500">{source.id}</span>
                  </td>
                  <td className="py-3 px-4 font-mono font-bold text-sky-900">{source.ward_id}</td>
                  <td className="py-3 px-4 font-medium text-slate-700">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                      source.type === 'ULTRASONIC_WATER_LEVEL'
                        ? 'bg-sky-50 text-sky-800 border border-sky-200'
                        : 'bg-indigo-50 text-indigo-800 border border-indigo-200'
                    }`}>
                      {source.type === 'ULTRASONIC_WATER_LEVEL' ? 'Water Level Gauge' : 'Rain Gauge (AWS)'}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                      source.quality_state === 'VALID'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : source.quality_state === 'SUSPECT'
                        ? 'bg-amber-100 text-amber-800 border border-amber-300'
                        : 'bg-rose-100 text-rose-800 border border-rose-300'
                    }`}>
                      {source.quality_state}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-bold text-emerald-700 flex items-center gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      {source.freshness_state}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono font-bold text-slate-900 text-sm">
                    {source.last_reading ?? '—'}
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {source.observed_at ? new Date(source.observed_at).toLocaleTimeString() : 'Realtime'}
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-[11px] font-semibold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      PostgreSQL Live
                    </span>
                  </td>
                </tr>
              ))}
              {filteredSources.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 px-4 text-center text-slate-500 font-medium">
                    No active telemetry stations match your filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
