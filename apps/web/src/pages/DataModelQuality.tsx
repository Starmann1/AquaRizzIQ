import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function DataModelQuality() {
  const { data: qualityData, isLoading, error } = useQuery({
    queryKey: ['dataQuality'],
    queryFn: apiClient.fetchDataQuality,
    refetchInterval: 5000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const dist = qualityData?.status_distribution || {
    VALID: 18,
    SUSPECT: 2,
    STALE: 1,
    OUTLIER: 0,
    CONFLICTING: 0,
    INVALID: 0,
  };

  const sources = qualityData?.active_telemetry_sources || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VALID':
        return 'bg-emerald-950/60 text-emerald-300 border-emerald-800';
      case 'SUSPECT':
        return 'bg-amber-950/60 text-amber-300 border-amber-800';
      case 'STALE':
        return 'bg-orange-950/60 text-orange-300 border-orange-800';
      case 'OUTLIER':
      case 'INVALID':
        return 'bg-red-950/60 text-red-300 border-red-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-slate-800 rounded-lg border border-slate-700 shadow gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">Data Quality &amp; Model Governance (P1-02)</h2>
            <SimulatedBadge />
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Real-time quality classification across telemetry sensors and ML validation domain tracking.
          </p>
        </div>
      </div>

      {/* QC State Distribution Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {Object.entries(dist).map(([state, count]) => {
          const isHealthy = state === 'VALID';
          const isWarning = state === 'SUSPECT' || state === 'STALE';
          return (
            <div
              key={state}
              className={`p-3.5 rounded-lg border shadow flex flex-col justify-between ${
                isHealthy
                  ? 'bg-emerald-950/20 border-emerald-800/60'
                  : isWarning
                  ? 'bg-amber-950/20 border-amber-800/60'
                  : 'bg-slate-900 border-slate-800'
              }`}
            >
              <div className="text-[11px] font-semibold text-slate-400 tracking-wider">
                {state}
              </div>
              <div
                className={`text-2xl font-bold font-mono mt-1 ${
                  isHealthy
                    ? 'text-emerald-400'
                    : isWarning
                    ? 'text-amber-400'
                    : 'text-slate-500'
                }`}
              >
                {String(count)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Sensor Health Monitoring Table */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 shadow overflow-hidden space-y-3">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
          <div>
            <h3 className="text-sm font-bold text-white">Active Telemetry Gauges &amp; Sensors</h3>
            <p className="text-xs text-slate-400">
              Freshness Window: <strong>15m</strong> &bull; Stale Threshold: <strong>30m</strong>
            </p>
          </div>
          <span className="text-xs text-emerald-400 font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Ingestion Pipeline Active
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Sensor ID</th>
                <th className="py-3 px-4">Station Name</th>
                <th className="py-3 px-4">Ward</th>
                <th className="py-3 px-4">Sensor Type</th>
                <th className="py-3 px-4">Quality State</th>
                <th className="py-3 px-4">Reading</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4">Quality Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-300">
              {sources.map((s: any) => (
                <tr key={s.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 font-mono text-cyan-400 font-semibold">{s.id}</td>
                  <td className="py-3 px-4 font-medium text-white">{s.name}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{s.ward_id}</td>
                  <td className="py-3 px-4 text-slate-400">{s.type}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${getStatusBadge(
                        s.quality_state
                      )}`}
                    >
                      {s.quality_state}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono font-bold text-white">{s.last_reading}</td>
                  <td className="py-3 px-4 font-mono text-slate-400">{s.latency_ms} ms</td>
                  <td className="py-3 px-4 text-[11px] text-slate-400">
                    {s.note || 'Nominal readings within physical boundaries'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Governance & Abstention Standards Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 shadow space-y-2">
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <span>Model Readiness Registry</span>
            <span className="px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 text-[10px] font-mono">
              GOVERNANCE
            </span>
          </h4>
          <div className="space-y-1.5 text-xs text-slate-300">
            <div className="flex justify-between p-2 bg-slate-900 rounded border border-slate-700/60">
              <span>M1 Terrain Susceptibility Model</span>
              <span className="font-mono text-emerald-400">PROTOTYPE (SYNTHETIC)</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-900 rounded border border-slate-700/60">
              <span>M2 Multi-Horizon Water Level Forecaster</span>
              <span className="font-mono text-emerald-400">PROTOTYPE (SYNTHETIC)</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-900 rounded border border-slate-700/60">
              <span>Calibrated Logistic Hazard Sigmoid (b0=-3.5)</span>
              <span className="font-mono text-cyan-400">OPERATIONAL BASELINE</span>
            </div>
          </div>
        </div>

        <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 shadow space-y-2">
          <h4 className="text-sm font-bold text-white flex items-center gap-2">
            <span>Abstention &amp; Fail-Safe Policy</span>
            <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 text-[10px] font-mono">
              SAFETY RULE
            </span>
          </h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            AquaRizz explicitly rejects silent fallbacks. If critical sensor telemetry is labeled as{' '}
            <strong className="text-slate-200">STALE</strong> or confidence drops below{' '}
            <strong className="text-slate-200">50%</strong>, the assessment engine yields an explicit{' '}
            <strong className="text-amber-400">ABSTAINED</strong> decision case rather than fabricating predictions.
          </p>
        </div>
      </div>
    </div>
  );
}
