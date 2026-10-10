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
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-white">Alert Broadcast Simulation</h2>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Simulated public siren and citizen notification gateway. Consequential alerts require verified human approval.
          </p>
        </div>
      </div>

      {dispatchMessage && (
        <div className="p-3 bg-slate-800 rounded border border-sky-500/50 text-sm font-medium text-sky-300">
          {dispatchMessage}
        </div>
      )}

      {/* Dispatched Alerts History Table */}
      <div className="p-5 bg-slate-800/80 rounded-lg border border-slate-700 shadow-lg">
        <h3 className="text-base font-bold text-white mb-3">Broadcast History Log</h3>

        {!alerts || alerts.length === 0 ? (
          <p className="text-xs text-slate-500 py-8 text-center">
            No alerts have been dispatched yet. Approve a case in Human Review to enable broadcast.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/60 text-xs text-slate-400 uppercase">
                <tr>
                  <th className="px-4 py-3">Alert ID</th>
                  <th className="px-4 py-3">Level</th>
                  <th className="px-4 py-3">Message</th>
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">Dispatched At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60">
                {alerts.map((a: any) => (
                  <tr key={a.id} className="hover:bg-slate-700/30 transition">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      {a.id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge level={a.alert_level as any} />
                    </td>
                    <td className="px-4 py-3 text-slate-200 text-xs">{a.message}</td>
                    <td className="px-4 py-3 text-xs text-sky-400 font-mono">
                      {a.dispatch_method}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
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
