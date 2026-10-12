import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, PendingReview } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import StatusBadge from '../components/common/StatusBadge';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

const AUTHORITIES = [
  { id: 'ALL', label: 'All Authorities', icon: '🏛️' },
  { id: 'Disaster Rescue & Fire Force', label: 'Disaster Rescue & Fire Force', icon: '🚒' },
  { id: 'Water Resources Dept (WRD)', label: 'Water Resources Dept (WRD)', icon: '💧' },
  { id: 'GCC Stormwater Drains Team', label: 'GCC Stormwater Drains Team', icon: '🌊' },
  { id: 'GCC Disaster Management Team', label: 'GCC Disaster Management Team', icon: '🏢' },
  { id: 'GCC Emergency Control Room', label: 'GCC Emergency Control Room', icon: '📡' },
];

export default function HumanReview() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [selectedDept, setSelectedDept] = useState<string>('ALL');
  const [selectedCase, setSelectedCase] = useState<PendingReview | null>(null);
  const [rationale, setRationale] = useState<string>('');
  const [checklist, setChecklist] = useState({
    evidence_reviewed: false,
    risk_verified: false,
    recommendations_approved: false,
  });
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { data: pendingCases, isLoading, error } = useQuery<PendingReview[]>({
    queryKey: ['pendingReviews', selectedDept],
    queryFn: () => apiClient.fetchPendingReviews(selectedDept),
    refetchInterval: 3000,
    enabled: true,
  });

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: apiClient.fetchAlerts,
    refetchInterval: 3000,
  });

  const approveMutation = useMutation({
    mutationFn: async (caseId: string) => {
      const res = await apiClient.approveReview(caseId, rationale, checklist);
      try {
        await apiClient.dispatchAlert(
          caseId,
          `FLOOD WARNING [${selectedCase?.risk_level || 'HIGH'}]: Action authorized for Ward ${selectedCase?.ward_id}. Operational field teams dispatched.`
        );
      } catch (err) {
        console.warn('Auto-dispatch broadcast notification:', err);
      }
      return res;
    },
    onSuccess: (data) => {
      setActionMessage(`✓ Case ${data.case_id} APPROVED & DISPATCHED. Operational action authorized and siren broadcast logged.`);
      queryClient.invalidateQueries({ queryKey: ['pendingReviews'] });
      queryClient.invalidateQueries({ queryKey: ['auditLogs'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setSelectedCase(null);
    },
    onError: (err: any) => {
      setActionMessage(`❌ Approval Error: ${err.message}`);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (caseId: string) =>
      apiClient.rejectReview(caseId, rationale),
    onSuccess: (data) => {
      setActionMessage(`✓ Case ${data.case_id} REJECTED. State updated and logged to audit trail.`);
      queryClient.invalidateQueries({ queryKey: ['pendingReviews'] });
      queryClient.invalidateQueries({ queryKey: ['auditLogs'] });
      setSelectedCase(null);
    },
    onError: (err: any) => {
      setActionMessage(`❌ Rejection Error: ${err.message}`);
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const getAuthorityBadge = (dept?: string) => {
    if (!dept) return { label: 'GCC Emergency Operations', icon: '🏛️', color: 'bg-slate-100 text-slate-800 border-slate-300' };
    if (dept.includes('Rescue') || dept.includes('Fire')) {
      return { label: dept, icon: '🚒', color: 'bg-rose-50 text-rose-800 border-rose-300' };
    }
    if (dept.includes('Water Resources') || dept.includes('WRD')) {
      return { label: dept, icon: '💧', color: 'bg-sky-50 text-sky-800 border-sky-300' };
    }
    if (dept.includes('Stormwater')) {
      return { label: dept, icon: '🌊', color: 'bg-cyan-50 text-cyan-800 border-cyan-300' };
    }
    if (dept.includes('Disaster Management')) {
      return { label: dept, icon: '🏢', color: 'bg-amber-50 text-amber-800 border-amber-300' };
    }
    return { label: dept, icon: '📡', color: 'bg-emerald-50 text-emerald-800 border-emerald-300' };
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm gap-4 backdrop-blur">
        <div>
          <h2 className="text-2xl font-black text-sky-950 tracking-tight">
            Human Review & Consequential Dispatch Gate
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            Mandatory human-in-the-loop authorization interface. Department-specific field actions and alerts remain pending until authenticated operator sign-off.
          </p>
        </div>
        <div className="flex items-center gap-2 px-3.5 py-2 bg-white border border-sky-200 rounded-xl shadow-2xs text-xs font-semibold text-slate-700">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Role: <strong className="text-sky-950 font-bold">GCC Emergency Coordinator</strong></span>
          <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 ml-1">
            ✓ Authorized Gate
          </span>
        </div>
      </div>

      {actionMessage && (
        <div className="p-4 bg-emerald-50/90 rounded-xl border border-emerald-300 text-sm font-bold text-emerald-950 shadow-2xs flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span>🛡️</span>
            <span>{actionMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => navigate('/audit')}
            className="px-3 py-1 rounded-lg bg-emerald-700 text-white hover:bg-emerald-800 text-xs font-bold transition shadow-2xs whitespace-nowrap"
          >
            Inspect Audit Trail →
          </button>
        </div>
      )}

      {/* Authority / Department Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 p-3 bg-white/95 rounded-2xl border border-sky-200/90 shadow-2xs">
        <span className="text-xs font-bold text-slate-500 px-2">Authority / Dept:</span>
        {AUTHORITIES.map((auth) => {
          const isSelected = selectedDept === auth.id;
          return (
            <button
              key={auth.id}
              type="button"
              onClick={() => {
                setSelectedDept(auth.id);
                setSelectedCase(null);
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-sky-50 text-slate-600 hover:bg-sky-100 border border-sky-200/70'
              }`}
            >
              <span>{auth.icon}</span>
              <span>{auth.label}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: List of Pending Decision Cases */}
        <div className="lg:col-span-1 p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-sky-200/60 pb-3">
            <div>
              <h3 className="text-base font-bold text-sky-950">
                Pending Decision Queue
              </h3>
              <p className="text-[11px] text-slate-500 font-medium">
                {selectedDept === 'ALL' ? 'All Municipal Departments' : selectedDept}
              </p>
            </div>
            <span className="px-2.5 py-1 text-xs bg-amber-100 text-amber-900 rounded-full font-mono font-black border border-amber-300 shadow-2xs">
              {pendingCases?.length || 0} Pending
            </span>
          </div>

          {!pendingCases || pendingCases.length === 0 ? (
            <div className="py-12 px-4 text-center space-y-2">
              <span className="text-2xl">📋</span>
              <p className="text-xs text-slate-600 font-bold">
                No pending cases awaiting review for {selectedDept === 'ALL' ? 'any authority' : selectedDept}.
              </p>
              <p className="text-[11px] text-slate-400">
                Actions dispatched from the Flood Risk Map or Recommendations feed appear here for authorization.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
              {pendingCases.map((c) => {
                const authBadge = getAuthorityBadge(c.department || c.authority_of_control);
                const isSelected = selectedCase?.case_id === c.case_id;

                return (
                  <div
                    key={c.case_id}
                    onClick={() => setSelectedCase(c)}
                    className={`p-4 rounded-xl border cursor-pointer transition shadow-2xs space-y-2 ${
                      isSelected
                        ? 'bg-white border-sky-500 ring-2 ring-sky-300/40 shadow-sm'
                        : 'bg-white/85 border-sky-200/80 hover:border-sky-300 hover:bg-white'
                    }`}
                  >
                    {/* Top Row: Ward & Risk Badge */}
                    <div className="flex justify-between items-start gap-2">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono text-xs font-black text-sky-950 bg-sky-100 px-2 py-0.5 rounded border border-sky-200">
                            {c.ward_id}
                          </span>
                          <span className="font-bold text-slate-900 text-sm">
                            {c.ward_name || c.ward_id}
                          </span>
                        </div>
                        {c.zone && (
                          <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                            Zone: {c.zone}
                          </div>
                        )}
                      </div>
                      <RiskBadge level={c.risk_level as any} />
                    </div>

                    {/* Action Title if present */}
                    {c.action_title && (
                      <div className="text-xs font-black text-slate-800 line-clamp-2">
                        {c.action_id && (
                          <span className="text-sky-700 font-mono font-bold mr-1.5">
                            [{c.action_id}]
                          </span>
                        )}
                        {c.action_title}
                      </div>
                    )}

                    {/* Department / Authority Badge */}
                    <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-lg border ${authBadge.color}`}>
                        <span>{authBadge.icon}</span>
                        <span className="truncate max-w-[160px]">{authBadge.label}</span>
                      </span>

                      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
                        <span>{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Review & Approval Checklist */}
        <div className="lg:col-span-2 p-6 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm space-y-4">
          {selectedCase ? (
            <div className="space-y-5">
              {/* Header Info */}
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-sky-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-black text-sky-800 bg-sky-100 px-2.5 py-0.5 rounded-lg border border-sky-200">
                      {selectedCase.ward_id}
                    </span>
                    <h3 className="text-xl font-black text-sky-950 tracking-tight">
                      Review Decision Case: {selectedCase.ward_name || selectedCase.ward_id}
                    </h3>
                  </div>
                  <p className="text-xs font-mono text-slate-400 font-semibold mt-1">
                    Case Ref: {selectedCase.case_id} · Hash: <span className="text-sky-800">{selectedCase.content_hash}</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <RiskBadge level={selectedCase.risk_level as any} />
                  <StatusBadge status={selectedCase.status as any} />
                </div>
              </div>

              {/* Authority & Action Details Card */}
              {(() => {
                const badge = getAuthorityBadge(selectedCase.department || selectedCase.authority_of_control);
                return (
                  <div className="rounded-2xl border border-sky-200 bg-sky-50/40 p-5 space-y-3 shadow-2xs">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-200/60 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{badge.icon}</span>
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            Authority of Control / Department
                          </div>
                          <div className="text-sm font-black text-sky-950">
                            {badge.label}
                          </div>
                        </div>
                      </div>

                      {selectedCase.urgency && (
                        <span className="text-xs font-bold text-amber-800 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-300">
                          ⏱️ Urgency: {selectedCase.urgency}
                        </span>
                      )}
                    </div>

                    {selectedCase.action_title ? (
                      <div className="space-y-1.5 pt-1">
                        <div className="flex items-center gap-2">
                          {selectedCase.action_id && (
                            <span className="font-mono text-xs font-black text-sky-800 bg-white px-2 py-0.5 rounded border border-sky-200">
                              {selectedCase.action_id}
                            </span>
                          )}
                          <h4 className="text-base font-black text-slate-900">
                            {selectedCase.action_title}
                          </h4>
                        </div>
                        <p className="text-xs sm:text-sm text-slate-700 font-medium leading-relaxed">
                          {selectedCase.action_description || 'Standard tactical flood response protocol authorized by automated decision support agent.'}
                        </p>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-600 font-medium">
                        Standard municipal flood warning and public notification protocol for {selectedCase.ward_name || selectedCase.ward_id}.
                      </p>
                    )}
                  </div>
                );
              })()}

              {/* Mandatory Checklist Items */}
              <div className="space-y-3 bg-slate-50/70 p-5 rounded-2xl border border-slate-200/80">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                    Mandatory Human Verification Checklist
                  </p>
                  <span className="text-[11px] text-slate-500 font-medium">
                    All 3 checks required before approval
                  </span>
                </div>

                <label className="flex items-center gap-3 text-sm text-slate-700 font-semibold cursor-pointer p-2.5 rounded-xl hover:bg-white transition border border-transparent hover:border-slate-200">
                  <input
                    type="checkbox"
                    checked={checklist.evidence_reviewed}
                    onChange={(e) =>
                      setChecklist({ ...checklist, evidence_reviewed: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300 cursor-pointer"
                  />
                  <span>1. Catchment sensor water levels & rainfall telemetry verified for {selectedCase.ward_name || selectedCase.ward_id}</span>
                </label>

                <label className="flex items-center gap-3 text-sm text-slate-700 font-semibold cursor-pointer p-2.5 rounded-xl hover:bg-white transition border border-transparent hover:border-slate-200">
                  <input
                    type="checkbox"
                    checked={checklist.risk_verified}
                    onChange={(e) =>
                      setChecklist({ ...checklist, risk_verified: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300 cursor-pointer"
                  />
                  <span>2. Hazard probability and deterministic safety floors confirmed</span>
                </label>

                <label className="flex items-center gap-3 text-sm text-slate-700 font-semibold cursor-pointer p-2.5 rounded-xl hover:bg-white transition border border-transparent hover:border-slate-200">
                  <input
                    type="checkbox"
                    checked={checklist.recommendations_approved}
                    onChange={(e) =>
                      setChecklist({ ...checklist, recommendations_approved: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300 cursor-pointer"
                  />
                  <span>3. Action deployment authorized for {selectedCase.department || 'designated control authority'}</span>
                </label>
              </div>

              {/* Rationale Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                  Emergency Coordinator Operational Rationale
                </label>
                <textarea
                  rows={2}
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl p-3 text-sm text-slate-900 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-2xs font-medium"
                  placeholder={`State operational reason for authorizing action under ${selectedCase.department || 'authority'}…`}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => approveMutation.mutate(selectedCase.case_id)}
                  disabled={
                    approveMutation.isPending ||
                    !rationale.trim() ||
                    Object.values(checklist).some((checked) => !checked)
                  }
                  className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-sm transition shadow-xs disabled:opacity-50 cursor-pointer flex items-center gap-2"
                >
                  {approveMutation.isPending ? 'Recording Cryptographic Approval…' : '✓ Approve & Authorize Field Action'}
                </button>
                <button
                  type="button"
                  onClick={() => rejectMutation.mutate(selectedCase.case_id)}
                  disabled={rejectMutation.isPending}
                  className="px-5 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-sm transition shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {rejectMutation.isPending ? 'Rejecting…' : '✗ Reject Decision'}
                </button>
              </div>
            </div>
          ) : (
            <div className="py-24 text-center space-y-3">
              <span className="text-3xl">👈</span>
              <p className="text-sm text-slate-700 font-bold">
                Select a pending decision case from the queue
              </p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Inspect catchment evidence, verify model hazard probability, and record human authorization for the respective municipal control authority.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Merged Alert Broadcast Gateway & Siren Transmission Log */}
      <section className="p-6 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-sky-100 pb-3">
          <div className="flex items-center gap-2.5">
            <h3 className="text-base font-bold text-sky-950">
              Broadcast History & Siren Transmission Log
            </h3>
            <SimulatedBadge />
          </div>
          <span className="text-xs font-mono font-bold text-slate-500">
            {alerts?.length || 0} Broadcasts Transmitted
          </span>
        </div>

        {!alerts || alerts.length === 0 ? (
          <div className="py-8 text-center space-y-2">
            <span className="text-2xl">📡</span>
            <p className="text-xs font-bold text-slate-600">
              No alert broadcasts transmitted yet.
            </p>
            <p className="text-[11px] text-slate-500 max-w-md mx-auto">
              When an emergency coordinator authorizes a decision case above, the approved warning is transmitted to simulated municipal sirens & citizen broadcast channels and permanently logged here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700">
              <thead className="bg-sky-50/80 text-sky-950 text-xs uppercase font-bold tracking-wider border-b border-sky-200">
                <tr>
                  <th className="px-4 py-3">Alert ID</th>
                  <th className="px-4 py-3">Level</th>
                  <th className="px-4 py-3">Broadcast Message</th>
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">Dispatched At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-sky-100">
                {alerts.map((a: any) => (
                  <tr key={a.id} className="hover:bg-sky-50/40 transition">
                    <td className="px-4 py-3 font-mono text-xs font-bold text-sky-900">
                      {a.id ? a.id.slice(0, 8) : 'ALT'}...
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={a.alert_level as any} />
                    </td>
                    <td className="px-4 py-3 text-slate-900 text-xs font-medium">
                      {a.message}
                    </td>
                    <td className="px-4 py-3 text-xs text-sky-800 font-mono font-bold">
                      {a.dispatch_method}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 font-mono whitespace-nowrap">
                      {a.dispatched_at ? new Date(a.dispatched_at).toLocaleTimeString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
