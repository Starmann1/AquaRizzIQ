import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function AlertSimulation() {
  const queryClient = useQueryClient();
  const [dispatchMessage, setDispatchMessage] = useState<string | null>(null);

  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['alerts'],
    queryFn: apiClient.fetchAlerts,
    refetchInterval: 3000,
  });

  const { data: pendingCases } = useQuery({
    queryKey: ['pendingReviews'],
    queryFn: apiClient.fetchPendingReviews,
  });

  const dispatchMutation = useMutation({
    mutationFn: (caseId: string) =>
      apiClient.dispatchAlert(caseId, 'URGENT: Flood levels rising rapidly in T. Nagar low-lying areas. Move to designated shelters.'),
    onSuccess: (data) => {
      setDispatchMessage(`✓ Alert ${data.alert_id} successfully broadcast via SIMULATED_GATEWAY.`);
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
    onError: (err: any) => {
      setDispatchMessage(`❌ Dispatch Blocked: ${err.message}`);
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  return (
    <div className="space-y-6">
      <div className="p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm backdrop-blur">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-black text-sky-950 tracking-tight">Alert Broadcast Gateway</h2>
          <SimulatedBadge />
        </div>
        <p className="text-sm text-slate-600 mt-1">
          Simulated public siren and citizen notification gateway. Consequential alerts require human approval sign-off.
        </p>
      </div>

      {dispatchMessage && (
        <div className="p-4 bg-sky-50 rounded-xl border border-sky-200 text-sm font-bold text-sky-950 shadow-2xs">
          {dispatchMessage}
        </div>
      )}

      {/* Dispatched Alerts History Table */}
      <div className="p-6 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm">
        <h3 className="text-base font-bold text-sky-950 mb-3">Broadcast History & Siren Log</h3>

        {!alerts || alerts.length === 0 ? (
          <p className="text-xs text-slate-500 py-10 text-center font-medium">
            No alerts have been dispatched yet. Cases approved in Human Review appear here for broadcast transmission.
          </p>
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
                      {a.id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={a.alert_level as any} />
                    </td>
                    <td className="px-4 py-3 text-slate-900 text-xs font-medium">{a.message}</td>
                    <td className="px-4 py-3 text-xs text-sky-800 font-mono font-bold">
                      {a.dispatch_method}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 font-mono">
                      {new Date(a.dispatched_at).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
