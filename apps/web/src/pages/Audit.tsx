import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function Audit() {
  const [filterActor, setFilterActor] = useState<string>('ALL');
  const [verificationResult, setVerificationResult] = useState<any | null>(null);

  const { data: auditLogs, isLoading, error, refetch } = useQuery({
    queryKey: ['auditLogs'],
    queryFn: apiClient.fetchAuditLog,
    refetchInterval: 5000,
  });

  const verifyMutation = useMutation({
    mutationFn: apiClient.verifyAuditChain,
    onSuccess: (data) => {
      setVerificationResult(data);
    },
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const logs = Array.isArray(auditLogs) ? auditLogs : [];

  const filteredLogs = logs.filter((log: any) => {
    if (filterActor !== 'ALL' && log.actor !== filterActor) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-slate-800 rounded-lg border border-slate-700 shadow gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">Cryptographic Audit Trail (SHA-256)</h2>
            <SimulatedBadge />
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Immutable, append-only hash-chained audit log guaranteeing non-repudiation and complete traceability for all safety decisions.
          </p>
        </div>

        {/* Verification Trigger Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 text-white rounded font-semibold text-xs shadow flex items-center gap-2 transition"
          >
            {verifyMutation.isPending ? 'Verifying Hashes...' : 'Verify Hash Chain Integrity'}
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-lg border flex items-center justify-between text-sm ${
            verificationResult.is_valid
              ? 'bg-emerald-950/40 border-emerald-700/80 text-emerald-200'
              : 'bg-red-950/40 border-red-700/80 text-red-200'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg">{verificationResult.is_valid ? '🛡️' : '⚠️'}</span>
            <div>
              <div className="font-bold">
                {verificationResult.is_valid
                  ? 'Cryptographic Integrity Confirmed: CHAIN INTACT'
                  : 'INTEGRITY BREACH DETECTED: Tampered Hash'}
              </div>
              <div className="text-xs opacity-90 mt-0.5">{verificationResult.message}</div>
            </div>
          </div>
          <span className="font-mono text-xs px-2.5 py-1 bg-slate-900/60 rounded border border-slate-700">
            {verificationResult.records_checked} Records Verified
          </span>
        </div>
      )}

      {/* Filter and Log Table */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 shadow overflow-hidden">
        {/* Table Filter Header */}
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
          <div className="text-xs font-semibold text-slate-300">
            Audit Records: <span className="font-mono text-cyan-400">{filteredLogs.length}</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Actor Filter:</span>
            <select
              value={filterActor}
              onChange={(e) => setFilterActor(e.target.value)}
              className="px-2.5 py-1 bg-slate-800 border border-slate-700 rounded text-slate-200 focus:outline-none"
            >
              <option value="ALL">All Actors</option>
              <option value="SYSTEM_SERVICE">SYSTEM_SERVICE</option>
              <option value="EMERGENCY_COORDINATOR">EMERGENCY_COORDINATOR</option>
              <option value="MUNICIPAL_OPERATOR">MUNICIPAL_OPERATOR</option>
            </select>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Timestamp (UTC)</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Prev Hash &rarr; Row Hash</th>
                <th className="py-3 px-4">Details Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-300">
              {filteredLogs.map((log: any, idx: number) => {
                const prevShort = log.prev_hash
                  ? `${log.prev_hash.slice(0, 8)}...`
                  : 'GENESIS';
                const rowShort = log.row_hash ? `${log.row_hash.slice(0, 10)}...` : '';

                return (
                  <tr key={log.id || idx} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-400">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-blue-950/70 text-blue-300 border border-blue-800">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-300">
                      {log.entity_type}: <span className="text-white">{log.entity_id}</span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300">
                        {log.actor}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px]">
                      <div className="text-slate-500">
                        &larr; <span title={log.prev_hash}>{prevShort}</span>
                      </div>
                      <div className="text-cyan-400 font-bold" title={log.row_hash}>
                        &bull; {rowShort}
                      </div>
                    </td>
                    <td className="py-3 px-4 max-w-xs truncate font-mono text-[11px] text-slate-400">
                      {typeof log.details === 'object'
                        ? JSON.stringify(log.details)
                        : String(log.details)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
