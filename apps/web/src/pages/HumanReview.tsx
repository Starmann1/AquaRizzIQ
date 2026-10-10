import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, PendingReview } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function HumanReview() {
  const queryClient = useQueryClient();

  const [selectedCase, setSelectedCase] = useState<PendingReview | null>(null);
  const [rationale, setRationale] = useState<string>('Ground telemetry reviewed. Surcharge overtopping imminent.');
  const [checklist, setChecklist] = useState({
    evidence_reviewed: true,
    risk_verified: true,
    recommendations_approved: true,
  });
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { data: pendingCases, isLoading, error } = useQuery<PendingReview[]>({
    queryKey: ['pendingReviews'],
    queryFn: apiClient.fetchPendingReviews,
    refetchInterval: 3000,
  });

  const approveMutation = useMutation({
    mutationFn: (caseId: string) =>
      apiClient.approveReview(caseId, 'u-coord-01', rationale, checklist),
    onSuccess: (data) => {
      setActionMessage(`✓ Case ${data.case_id} APPROVED. State transitioned to APPROVED. Ready for simulated dispatch.`);
      queryClient.invalidateQueries({ queryKey: ['pendingReviews'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setSelectedCase(null);
    },
    onError: (err: any) => {
      setActionMessage(`❌ Approval Error: ${err.message}`);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (caseId: string) =>
      apiClient.rejectReview(caseId, 'u-coord-01', rationale),
    onSuccess: (data) => {
      setActionMessage(`✓ Case ${data.case_id} REJECTED.`);
      queryClient.invalidateQueries({ queryKey: ['pendingReviews'] });
      setSelectedCase(null);
    },
    onError: (err: any) => {
      setActionMessage(`❌ Rejection Error: ${err.message}`);
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Human Review & Consequential Dispatch Gate
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Mandatory human verification interface. No consequential alert can be dispatched without recorded review (P0-04, P0-05).
          </p>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 bg-slate-800 rounded border border-sky-500/50 text-sm font-medium text-sky-300">
          {actionMessage}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: List of Pending Decision Cases */}
        <div className="lg:col-span-1 p-4 bg-slate-800/80 rounded-lg border border-slate-700">
          <h3 className="text-base font-bold text-white mb-3 flex items-center justify-between">
            <span>Pending Cases</span>
            <span className="px-2 py-0.5 text-xs bg-amber-900/60 text-amber-300 rounded font-mono">
              {pendingCases?.length || 0}
            </span>
          </h3>

          {!pendingCases || pendingCases.length === 0 ? (
            <p className="text-xs text-slate-500 py-6 text-center">
              No decision cases currently pending review. Trigger an assessment from Overview to submit a case.
            </p>
          ) : (
            <div className="space-y-2">
              {pendingCases.map((c) => (
                <div
                  key={c.case_id}
                  onClick={() => setSelectedCase(c)}
                  className={`p-3 rounded border cursor-pointer transition ${
                    selectedCase?.case_id === c.case_id
                      ? 'bg-slate-700/80 border-sky-500'
                      : 'bg-slate-900/50 border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-white text-sm">{c.ward_id}</span>
                    <RiskBadge level={c.risk_level as any} />
                  </div>
                  <div className="flex justify-between items-center mt-2 text-xs text-slate-400">
                    <StatusBadge status={c.status as any} />
                    <span>{new Date(c.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Review & Approval Checklist */}
        <div className="lg:col-span-2 p-5 bg-slate-800/80 rounded-lg border border-slate-700">
          {selectedCase ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-slate-700 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-white">
                    Review Decision Case: {selectedCase.ward_id}
                  </h3>
                  <p className="text-xs font-mono text-slate-400">
                    ID: {selectedCase.case_id}
                  </p>
                </div>
                <RiskBadge level={selectedCase.risk_level as any} />
              </div>

              {/* Mandatory Checklist Items */}
              <div className="space-y-2.5 bg-slate-900/40 p-3.5 rounded border border-slate-700/60">
                <p className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Mandatory Verification Checklist
                </p>

                <label className="flex items-center gap-2.5 text-sm text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist.evidence_reviewed}
                    onChange={(e) =>
                      setChecklist({ ...checklist, evidence_reviewed: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 bg-slate-800 border-slate-600"
                  />
                  <span>1. Catchment sensor water levels & rainfall telemetry verified</span>
                </label>

                <label className="flex items-center gap-2.5 text-sm text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist.risk_verified}
                    onChange={(e) =>
                      setChecklist({ ...checklist, risk_verified: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 bg-slate-800 border-slate-600"
                  />
                  <span>2. Hazard probability and safety floors confirmed</span>
                </label>

                <label className="flex items-center gap-2.5 text-sm text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist.recommendations_approved}
                    onChange={(e) =>
                      setChecklist({ ...checklist, recommendations_approved: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 bg-slate-800 border-slate-600"
                  />
                  <span>3. Proposed evacuation advisory actions validated</span>
                </label>
              </div>

              {/* Rationale Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Emergency Coordinator Rationale
                </label>
                <textarea
                  rows={2}
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                  placeholder="State operational reason for alert decision..."
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => approveMutation.mutate(selectedCase.case_id)}
                  disabled={approveMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded text-sm transition disabled:opacity-50"
                >
                  {approveMutation.isPending ? 'Recording Approval...' : '✓ Approve Alert Decision'}
                </button>
                <button
                  onClick={() => rejectMutation.mutate(selectedCase.case_id)}
                  disabled={rejectMutation.isPending}
                  className="px-4 py-2 bg-rose-700 hover:bg-rose-600 text-white font-semibold rounded text-sm transition disabled:opacity-50"
                >
                  {rejectMutation.isPending ? 'Rejecting...' : '✗ Reject Decision'}
                </button>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-slate-500">
              Select a pending case from the left to inspect telemetry evidence and record approval.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
