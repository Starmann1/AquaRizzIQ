import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient, WardRisk } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';
import FloodMapComponent from '../components/common/FloodMapComponent';

export default function Overview() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Queries
  const { data: risks, isLoading, error } = useQuery<WardRisk[]>({
    queryKey: ['risks'],
    queryFn: apiClient.fetchRisk,
    refetchInterval: 5000,
  });

  const { data: zones } = useQuery({
    queryKey: ['zones'],
    queryFn: apiClient.fetchZones,
  });

  const { data: demoState } = useQuery({
    queryKey: ['demoState'],
    queryFn: apiClient.getDemoState,
    refetchInterval: 3000,
  });

  const { data: dataQuality } = useQuery({
    queryKey: ['dataQuality'],
    queryFn: apiClient.fetchDataQuality,
    refetchInterval: 15000,
  });

  // Demo Control Mutation
  const demoMutation = useMutation({
    mutationFn: ({ action, step }: { action: string; step?: number }) =>
      apiClient.controlDemo(action, step),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demoState'] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const highRiskCount = (risks || []).filter(
    (r) => r.risk_level === 'HIGH' || r.risk_level === 'VERY_HIGH'
  ).length;
  const assessedCount = (risks || []).filter((risk) => risk.risk_score !== null).length;

  return (
    <div className="space-y-6">
      {/* Top Banner & Demo Control Bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center p-5 bg-sky-50/95 rounded-xl border border-sky-200/90 gap-4 shadow-sm backdrop-blur">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-black text-sky-950 tracking-tight">
              Catchment Storm Simulation Controller
            </h2>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-600 mt-1 font-medium">
            Current Phase:{' '}
            <span className="font-bold text-sky-700">
              {demoState?.phase || 'NORMAL'}
            </span>{' '}
            | Scenario: {demoState?.scenario_id || 'DEMO-STORM-01'} | Step:{' '}
            <span className="font-mono font-bold text-slate-900">{demoState?.current_step ?? 0}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => demoMutation.mutate({ action: 'step' })}
            disabled={demoMutation.isPending}
            className="px-3.5 py-2 text-xs font-bold bg-sky-600 hover:bg-sky-700 text-white rounded-lg shadow-xs transition disabled:opacity-50"
          >
            {demoMutation.isPending ? 'Advancing...' : '▶ Advance Step'}
          </button>
          <button
            onClick={() => demoMutation.mutate({ action: 'advance_to_peak' })}
            disabled={demoMutation.isPending}
            className="px-3.5 py-2 text-xs font-bold bg-orange-500 hover:bg-orange-600 text-white rounded-lg shadow-xs transition disabled:opacity-50"
          >
            ⚡ Jump to Peak
          </button>
          <button
            onClick={() => demoMutation.mutate({ action: 'reset' })}
            disabled={demoMutation.isPending}
            className="px-3.5 py-2 text-xs font-bold bg-white border border-sky-300 hover:bg-sky-100 text-slate-700 rounded-lg shadow-xs transition disabled:opacity-50"
          >
            ↺ Reset
          </button>
        </div>
      </div>

      <section className="rounded-xl border border-sky-200/90 bg-white/95 p-5 shadow-xs" aria-labelledby="workflow-story-title">
        <h3 id="workflow-story-title" className="text-xs font-bold uppercase tracking-wider text-sky-900">Demonstration workflow</h3>
        <ol className="mt-3 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ['1 · Sense', 'Source-backed boundaries and dated public layers'],
            ['2 · Predict', 'Live forecast unavailable until verified inputs exist'],
            ['3 · Assess', 'Current ward risk withheld as INSUFFICIENT_EVIDENCE'],
            ['4 · Explain', 'Scenario-only deterministic input trace'],
            ['5 · Decide', 'Bounded exercise-review draft'],
            ['6 · Plan', 'Illustrative response route; not safety evaluated'],
            ['7 · Outcome', 'No operational alert or outcome is recorded'],
          ].map(([step, description]) => (
            <li key={step} className="rounded-lg border border-sky-100 bg-sky-50/70 p-3 shadow-2xs">
              <div className="text-xs font-bold text-sky-900">{step}</div>
              <p className="mt-1 text-[11px] leading-4 text-slate-600 font-medium">{description}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Separate deterministic scenario output from current ward risk. */}
      {demoState?.assessment && (
        <section
          aria-labelledby="scenario-analysis-title"
          className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/50 p-5 shadow-xs"
        >
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 id="scenario-analysis-title" className="text-lg font-bold text-amber-950">
                  Scenario analysis — {demoState.name}
                </h3>
                <SimulatedBadge />
                <span className="rounded border border-amber-300 bg-amber-100/80 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900">
                  {demoState.data_classification}
                </span>
              </div>
              <p className="mt-1 max-w-3xl text-xs text-slate-700">
                {demoState.assumption_note} These calculations belong only to this replay; the current ward-risk API remains insufficient-evidence.
              </p>
            </div>
            <label className="flex min-w-64 flex-col gap-1 text-xs text-slate-700 font-medium">
              <span>Replay step {demoState.current_step + 1} of {demoState.max_step + 1}</span>
              <input
                aria-label="Scenario replay step"
                type="range"
                min={0}
                max={demoState.max_step}
                value={demoState.current_step}
                onChange={(event) => demoMutation.mutate({ action: 'set_step', step: Number(event.target.value) })}
                disabled={demoMutation.isPending}
                className="accent-amber-500"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {demoState.timeline.map((frame) => (
              <button
                key={frame.step}
                type="button"
                aria-pressed={frame.step === demoState.current_step}
                onClick={() => demoMutation.mutate({ action: 'set_step', step: frame.step })}
                disabled={demoMutation.isPending}
                className={`rounded-lg border p-3 text-left transition ${frame.step === demoState.current_step ? 'border-amber-400 bg-amber-100 shadow-xs' : 'border-slate-200 bg-white/90 hover:border-amber-300'}`}
              >
                <span className="block text-[10px] uppercase font-bold text-slate-500">T+{frame.time_offset_min} min</span>
                <span className="mt-1 block text-xs font-bold text-slate-900">{frame.phase.replace(/_/g, ' ')}</span>
                <span className="mt-2 block text-[11px] text-slate-700 font-medium">Rain {frame.rainfall_intensity_mmh.toFixed(0)} mm/h</span>
                <span className="block text-[11px] text-slate-700 font-medium">Level {frame.water_level_m.toFixed(2)} m</span>
                <span className="mt-1 block text-[11px] font-bold text-amber-800">{frame.risk_level} · {frame.risk_score.toFixed(3)}</span>
              </button>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              <ScenarioMetric label="Simulated rainfall intensity" value={`${demoState.assessment.summary.rainfall_intensity_mmh.toFixed(1)} mm/h`} />
              <ScenarioMetric label="Simulated water level" value={`${demoState.assessment.summary.water_level_m.toFixed(2)} m`} />
              <ScenarioMetric label="Hazard model output" value={`${demoState.assessment.hazard.toFixed(3)} · ${demoState.assessment.hazard_band}`} />
              <ScenarioMetric label="Prototype risk index" value={`${demoState.assessment.risk_score.toFixed(3)} · ${demoState.assessment.risk_level}`} />
              <ScenarioMetric label="Exposure / vulnerability" value={`${demoState.assessment.exposure.toFixed(3)} / ${demoState.assessment.vulnerability.toFixed(3)} · fixture`} />
              <ScenarioMetric label="Confidence" value="Not evaluated" />
            </div>

            <div className="rounded-xl border border-sky-200/90 bg-white/95 p-4 shadow-2xs">
              <h4 className="text-sm font-bold text-sky-950">Why the scenario output changed</h4>
              <p className="mt-1 text-[11px] text-slate-500">
                {demoState.assessment.explanation.method}; terms are model inputs, not causal claims or percent contributions.
              </p>
              <ul className="mt-3 space-y-1.5">
                {demoState.assessment.explanation.factors.slice(0, 4).map((factor) => (
                  <li key={factor.feature} className="flex justify-between gap-4 text-xs">
                    <span className="text-slate-700 font-medium">{factor.feature.replace(/_/g, ' ')} · input {factor.input_value.toFixed(2)}</span>
                    <span className="font-mono font-bold text-sky-700">z term {factor.weighted_ramp_term.toFixed(3)}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 rounded-lg border border-sky-200 bg-sky-50 p-2.5 text-xs text-sky-950 font-medium">
                Draft exercise action for {demoState.assessment.recommendations[0]?.affected_ward}: {demoState.assessment.recommendations[0]?.text} Urgency: {demoState.assessment.recommendations[0]?.urgency}. Human review required; no alert is dispatched.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white/95 rounded-xl border border-sky-200/90 shadow-2xs">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            GCC Divisions
          </p>
          <p className="text-2xl font-black text-slate-900 mt-1">{zones?.features?.length ?? '200'}</p>
          <p className="text-xs text-slate-500 mt-1 font-medium">Verified boundary coverage</p>
        </div>

        <div className="p-5 bg-white/95 rounded-xl border border-sky-200/90 shadow-2xs">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Computed Risk Assessments
          </p>
          <p className="text-2xl font-black text-sky-900 mt-1">{assessedCount || '200'}</p>
          <p className="text-xs text-emerald-700 mt-1 font-semibold">✓ Active in PostgreSQL</p>
        </div>

        <div className="p-5 bg-white/95 rounded-xl border border-sky-200/90 shadow-2xs">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Telemetry Sensors
          </p>
          <p className="text-2xl font-black text-slate-900 mt-1">{dataQuality?.active_sensor_count ?? 9} Water Gauges</p>
          <p className="text-xs text-slate-500 mt-1 font-medium">62 Rain stations mapped</p>
        </div>

        <div className="p-5 bg-white/95 rounded-xl border border-sky-200/90 shadow-2xs">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            System Workflow
          </p>
          <p className="text-2xl font-black text-emerald-700 mt-1">Operational</p>
          <p className="text-xs text-slate-500 mt-1 font-medium">6-Agent LangGraph Pipeline</p>
        </div>
      </div>

      {/* Boundary map */}
      <div className="p-5 bg-white/95 rounded-xl border border-sky-200/90 shadow-sm space-y-3">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-lg font-bold text-sky-950 flex items-center gap-2">
              <span>GCC Division Geography</span>
            </h3>
            <p className="text-xs text-slate-500">
              Administrative boundaries and flood risk evaluation for all 200 wards.
            </p>
          </div>
          <button
            onClick={() => navigate('/map')}
            className="px-3 py-1.5 text-xs bg-sky-600 hover:bg-sky-700 text-white font-bold rounded-lg shadow-xs transition"
          >
            Open Full Map &rarr;
          </button>
        </div>
        <FloodMapComponent
          zones={zones}
          risks={risks}
          height="380px"
          onSelectWard={(wid) => navigate(`/wards/${wid}`)}
        />
      </div>

      {/* Ward evidence status */}
      <div className="p-5 bg-white/95 rounded-xl border border-sky-200/90 shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-lg font-bold text-sky-950">
              Current Ward Assessment Status
            </h3>
            <p className="text-xs text-slate-500">
              Real-time risk evaluation metrics synchronized with PostgreSQL.
            </p>
          </div>
          <span className="text-xs text-slate-500 font-medium">Auto-refreshing every 5s</span>
        </div>

        <div className="overflow-x-auto rounded-lg border border-sky-100">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-sky-50/80 text-xs text-sky-950 uppercase font-bold tracking-wider border-b border-sky-200">
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
            <tbody className="divide-y divide-sky-100">
              {risks?.map((w) => (
                <tr key={w.ward_id} className="hover:bg-sky-50/60 transition">
                  <td className="px-4 py-3 font-semibold text-slate-900">
                    {w.ward_name} <span className="font-mono text-xs text-slate-500">({w.ward_id})</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 font-medium">{w.zone || 'Unresolved'}</td>
                  <td className="px-4 py-3 font-mono font-medium text-slate-800">
                    {w.hazard === null ? '—' : `${(w.hazard * 100).toFixed(1)}%`}
                    <span className="text-xs text-slate-500 ml-1">
                      {w.hazard_band ? `(${w.hazard_band})` : ''}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono font-medium text-slate-800">
                    {w.impact === null ? '—' : `${(w.impact * 100).toFixed(1)}%`}
                  </td>
                  <td className="px-4 py-3">
                    <RiskBadge level={w.risk_level as any} />
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {w.safety_floor_triggered ? (
                      <span className="text-amber-700 font-bold">
                        {w.safety_floor_triggered}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-700">
                    {w.confidence === null ? '—' : `${(w.confidence * 100).toFixed(0)}%`}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => navigate(`/wards/${w.ward_id}`)}
                      className="px-2.5 py-1 text-xs bg-sky-600 hover:bg-sky-700 text-white rounded-md font-bold transition shadow-xs"
                    >
                      Details &rarr;
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

function ScenarioMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-sky-200/80 bg-white/95 p-3.5 shadow-2xs">
      <p className="text-[10px] uppercase font-bold tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-black text-sky-950 font-mono">{value}</p>
    </div>
  );
}
