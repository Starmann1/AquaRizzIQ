import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, WardRisk } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function Overview() {
  const queryClient = useQueryClient();
  const [assessingWard, setAssessingWard] = useState<string | null>(null);

  // Queries
  const { data: risks, isLoading, error } = useQuery<WardRisk[]>({
    queryKey: ['risks'],
    queryFn: apiClient.fetchRisk,
    refetchInterval: 5000,
  });

  const { data: demoState } = useQuery({
    queryKey: ['demoState'],
    queryFn: apiClient.getDemoState,
    refetchInterval: 3000,
  });

  // Demo Control Mutation
  const demoMutation = useMutation({
    mutationFn: (action: string) => apiClient.controlDemo(action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demoState'] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
    },
  });

  // Assessment Trigger Mutation
  const assessMutation = useMutation({
    mutationFn: (wardId: string) => apiClient.triggerAssessment(wardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risks'] });
      queryClient.invalidateQueries({ queryKey: ['pendingReviews'] });
      setAssessingWard(null);
    },
  });

  const handleRunAssessment = (wardId: string) => {
    setAssessingWard(wardId);
    assessMutation.mutate(wardId);
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const highRiskCount = (risks || []).filter(
    (r) => r.risk_level === 'HIGH' || r.risk_level === 'VERY_HIGH'
  ).length;

  return (
    <div className="space-y-6">
      {/* Top Banner & Demo Control Bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center p-4 bg-slate-800/90 rounded-lg border border-slate-700 gap-4 shadow-lg">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-wide">
              Catchment Storm Simulation Controller
            </h2>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Current Phase:{' '}
            <span className="font-semibold text-sky-400">
              {demoState?.phase || 'NORMAL'}
            </span>{' '}
            | Scenario: {demoState?.scenario_id || 'DEMO-STORM-01'} | Step:{' '}
            {demoState?.current_step ?? 0}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => demoMutation.mutate('step')}
            disabled={demoMutation.isPending}
            className="px-3 py-1.5 text-sm bg-sky-600 hover:bg-sky-500 text-white font-medium rounded transition disabled:opacity-50"
          >
            {demoMutation.isPending ? 'Advancing...' : '▶ Advance Storm Step'}
          </button>
          <button
            onClick={() => demoMutation.mutate('advance_to_peak')}
            disabled={demoMutation.isPending}
            className="px-3 py-1.5 text-sm bg-orange-600 hover:bg-orange-500 text-white font-medium rounded transition disabled:opacity-50"
          >
            ⚡ Jump to Peak Rain
          </button>
          <button
            onClick={() => demoMutation.mutate('reset')}
            disabled={demoMutation.isPending}
            className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 font-medium rounded transition disabled:opacity-50"
          >
            ↺ Reset
          </button>
        </div>
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Monitored GCC Wards
          </p>
          <p className="text-2xl font-bold text-white mt-1">{risks?.length || 5}</p>
          <p className="text-xs text-slate-500 mt-1">Kodambakkam & Adyar zones</p>
        </div>

        <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            High / Very High Flood Risk
          </p>
          <p className="text-2xl font-bold text-rose-400 mt-1">{highRiskCount}</p>
          <p className="text-xs text-slate-500 mt-1">Requires coordinator review</p>
        </div>

        <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Telemetry Quality State
          </p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">VALID</p>
          <p className="text-xs text-slate-500 mt-1">5 gauges active & reporting</p>
        </div>

        <div className="p-4 bg-slate-800/80 rounded-lg border border-slate-700">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Agent Orchestrator
          </p>
          <p className="text-2xl font-bold text-sky-400 mt-1">LangGraph</p>
          <p className="text-xs text-slate-500 mt-1">6 typed agents active</p>
        </div>
      </div>

      {/* Real-Time Monitored Wards Table */}
      <div className="p-5 bg-slate-800/80 rounded-lg border border-slate-700 shadow-lg">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-lg font-bold text-white">
              GCC Ward Flood Risk Matrix
            </h3>
            <p className="text-xs text-slate-400">
              Evaluated with calibrated logistic hazard H = σ((z - b) / T) and matrix-gated impact
            </p>
          </div>
          <span className="text-xs text-slate-500">Auto-refreshing every 5s</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/60 text-xs text-slate-400 uppercase">
              <tr>
                <th className="px-4 py-3">Ward</th>
                <th className="px-4 py-3">Zone</th>
                <th className="px-4 py-3">Hazard Prob (H)</th>
                <th className="px-4 py-3">Impact (I)</th>
                <th className="px-4 py-3">Risk Level</th>
                <th className="px-4 py-3">Safety Floor</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/60">
              {risks?.map((w) => (
                <tr key={w.ward_id} className="hover:bg-slate-700/30 transition">
                  <td className="px-4 py-3 font-semibold text-white">
                    {w.ward_name} ({w.ward_id})
                  </td>
                  <td className="px-4 py-3 text-slate-400">{w.zone}</td>
                  <td className="px-4 py-3 font-mono">
                    {(w.hazard * 100).toFixed(1)}%
                    <span className="text-xs text-slate-500 ml-1">
                      ({w.hazard_band})
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono">
                    {(w.impact * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    <RiskBadge level={w.risk_level as any} />
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {w.safety_floor_triggered ? (
                      <span className="text-amber-400 font-medium">
                        {w.safety_floor_triggered}
                      </span>
                    ) : (
                      <span className="text-slate-500">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {(w.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRunAssessment(w.ward_id)}
                      disabled={assessingWard === w.ward_id}
                      className="px-2.5 py-1 text-xs bg-sky-700 hover:bg-sky-600 text-white rounded font-medium transition disabled:opacity-50"
                    >
                      {assessingWard === w.ward_id ? 'Assessing...' : 'Run Pipeline'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
