import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, PendingReview } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function HumanReview() {
  const queryClient = useQueryClient();

  const [accessToken, setAccessToken] = useState<string | null>(() => sessionStorage.getItem('aquarizz_access_token'));
  const [operatorName, setOperatorName] = useState<string>(() => sessionStorage.getItem('aquarizz_operator_username') ?? '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [selectedCase, setSelectedCase] = useState<PendingReview | null>(null);
  const [rationale, setRationale] = useState<string>('');
  const [checklist, setChecklist] = useState({
    evidence_reviewed: false,
    risk_verified: false,
    recommendations_approved: false,
  });
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const { data: pendingCases, isLoading, error } = useQuery<PendingReview[]>({
    queryKey: ['pendingReviews'],
    queryFn: apiClient.fetchPendingReviews,
    refetchInterval: 3000,
    enabled: Boolean(accessToken),
  });

  const approveMutation = useMutation({
    mutationFn: (caseId: string) =>
      apiClient.approveReview(caseId, rationale, checklist),
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
      apiClient.rejectReview(caseId, rationale),
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
  if (error && accessToken) return <ErrorDisplay message={(error as Error).message} />;

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);
    try {
      const result = await apiClient.login(username, password);
      sessionStorage.setItem('aquarizz_access_token', result.access_token);
      sessionStorage.setItem('aquarizz_operator_username', result.username);
      setAccessToken(result.access_token);
      setOperatorName(result.username);
      setPassword('');
      await queryClient.invalidateQueries({ queryKey: ['pendingReviews'] });
    } catch (loginFailure) {
      setLoginError((loginFailure as Error).message);
    } finally {
      setIsLoggingIn(false);
    }
  };

  if (!accessToken) {
    return (
      <section className="mx-auto max-w-lg space-y-4 rounded-2xl border border-sky-200/90 bg-white/95 p-7 shadow-sm backdrop-blur">
        <div>
          <span className="font-mono text-xs font-bold text-sky-800 bg-sky-100 px-3 py-1 rounded-lg border border-sky-200 shadow-2xs">
            SECURITY GATE
          </span>
          <h2 className="mt-2 text-2xl font-black text-sky-950 tracking-tight">Operator Sign-In Required</h2>
          <p className="mt-2 text-sm text-slate-600 font-medium">
            Review and dispatch endpoints require a provisioned Emergency Coordinator or Administrator account.
          </p>
        </div>
        <form onSubmit={handleLogin} className="space-y-4 pt-1">
          <label className="block text-xs font-bold text-sky-900 uppercase tracking-wider">
            Username
            <input required autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 font-medium shadow-2xs focus:border-sky-500 focus:ring-1 focus:ring-sky-500" />
          </label>
          <label className="block text-xs font-bold text-sky-900 uppercase tracking-wider">
            Password
            <input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 font-medium shadow-2xs focus:border-sky-500 focus:ring-1 focus:ring-sky-500" />
          </label>
          {loginError && <p role="alert" className="text-xs font-bold text-rose-700">{loginError}</p>}
          <button disabled={isLoggingIn} className="w-full rounded-xl bg-sky-600 hover:bg-sky-700 py-2.5 text-sm font-bold text-white shadow-xs transition disabled:opacity-50">
            {isLoggingIn ? 'Authenticating…' : 'Sign in to Emergency Gate →'}
          </button>
        </form>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm gap-4 backdrop-blur">
        <div>
          <h2 className="text-2xl font-black text-sky-950 tracking-tight">
            Human Review & Consequential Dispatch Gate
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            Mandatory human-in-the-loop verification interface. No consequential alert can be dispatched without recorded human sign-off.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-600 font-medium">
          <span>Signed in as: <strong className="text-sky-950">{operatorName}</strong></span>
          <button
            onClick={() => {
              sessionStorage.removeItem('aquarizz_access_token');
              sessionStorage.removeItem('aquarizz_operator_username');
              setAccessToken(null);
              setOperatorName('');
              queryClient.removeQueries({ queryKey: ['pendingReviews'] });
            }}
            className="rounded-lg border border-sky-300 bg-white px-3 py-1.5 hover:bg-sky-50 text-sky-900 font-bold shadow-2xs transition"
          >
            Sign out
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="p-4 bg-sky-50/90 rounded-xl border border-sky-200 text-sm font-bold text-sky-950 shadow-2xs">
          {actionMessage}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: List of Pending Decision Cases */}
        <div className="lg:col-span-1 p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm space-y-3">
          <h3 className="text-base font-bold text-sky-950 flex items-center justify-between">
            <span>Pending Cases</span>
            <span className="px-2.5 py-0.5 text-xs bg-amber-100 text-amber-900 rounded-full font-mono font-bold border border-amber-300">
              {pendingCases?.length || 0}
            </span>
          </h3>

          {!pendingCases || pendingCases.length === 0 ? (
            <p className="text-xs text-slate-500 py-8 text-center font-medium">
              No pending decision cases in queue. Assessments abstain safely when sensor evidence is absent or stale.
            </p>
          ) : (
            <div className="space-y-2">
              {pendingCases.map((c) => (
                <div
                  key={c.case_id}
                  onClick={() => setSelectedCase(c)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition shadow-2xs ${
                    selectedCase?.case_id === c.case_id
                      ? 'bg-white border-sky-500 ring-2 ring-sky-300/40'
                      : 'bg-white/80 border-sky-100 hover:border-sky-300'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-900 text-sm">{c.ward_id}</span>
                    <RiskBadge level={c.risk_level as any} />
                  </div>
                  <div className="flex justify-between items-center mt-2.5 text-xs text-slate-500">
                    <StatusBadge status={c.status as any} />
                    <span className="font-mono">{new Date(c.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Review & Approval Checklist */}
        <div className="lg:col-span-2 p-6 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm space-y-4">
          {selectedCase ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-sky-100 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-sky-950">
                    Review Decision Case: {selectedCase.ward_id}
                  </h3>
                  <p className="text-xs font-mono text-slate-500 font-semibold">
                    ID: {selectedCase.case_id}
                  </p>
                </div>
                <RiskBadge level={selectedCase.risk_level as any} />
              </div>

              {/* Mandatory Checklist Items */}
              <div className="space-y-3 bg-sky-50/60 p-4 rounded-xl border border-sky-100">
                <p className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                  Mandatory Verification Checklist
                </p>

                <label className="flex items-center gap-3 text-sm text-slate-700 font-medium cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist.evidence_reviewed}
                    onChange={(e) =>
                      setChecklist({ ...checklist, evidence_reviewed: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
                  />
                  <span>1. Catchment sensor water levels & rainfall telemetry verified</span>
                </label>

                <label className="flex items-center gap-3 text-sm text-slate-700 font-medium cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist.risk_verified}
                    onChange={(e) =>
                      setChecklist({ ...checklist, risk_verified: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
                  />
                  <span>2. Hazard probability and deterministic safety floors confirmed</span>
                </label>

                <label className="flex items-center gap-3 text-sm text-slate-700 font-medium cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checklist.recommendations_approved}
                    onChange={(e) =>
                      setChecklist({ ...checklist, recommendations_approved: e.target.checked })
                    }
                    className="w-4 h-4 rounded text-sky-600 focus:ring-sky-500 border-slate-300"
                  />
                  <span>3. Proposed evacuation advisory actions validated</span>
                </label>
              </div>

              {/* Rationale Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                  Emergency Coordinator Rationale
                </label>
                <textarea
                  rows={2}
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl p-3 text-sm text-slate-900 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-2xs"
                  placeholder="State operational reason for alert decision…"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => approveMutation.mutate(selectedCase.case_id)}
                  disabled={
                    approveMutation.isPending ||
                    !rationale.trim() ||
                    Object.values(checklist).some((checked) => !checked)
                  }
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-sm transition shadow-xs disabled:opacity-50"
                >
                  {approveMutation.isPending ? 'Recording Approval…' : '✓ Approve Alert Decision'}
                </button>
                <button
                  onClick={() => rejectMutation.mutate(selectedCase.case_id)}
                  disabled={rejectMutation.isPending}
                  className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl text-sm transition shadow-xs disabled:opacity-50"
                >
                  {rejectMutation.isPending ? 'Rejecting…' : '✗ Reject Decision'}
                </button>
              </div>
            </div>
          ) : (
            <div className="py-20 text-center text-slate-500 font-medium">
              Select a pending case from the left panel to inspect telemetry evidence and record human sign-off.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
