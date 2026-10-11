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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm gap-4 backdrop-blur">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black text-sky-950 tracking-tight">Cryptographic Audit Trail (SHA-256)</h2>
            <SimulatedBadge />
          </div>
          <p className="text-slate-600 text-sm mt-1">
            Immutable, append-only hash-chained ledger guaranteeing non-repudiation and complete traceability for all safety decisions.
          </p>
        </div>

        {/* Verification Trigger Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
            className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl font-bold text-xs shadow-xs flex items-center gap-2 transition"
          >
            {verifyMutation.isPending ? 'Verifying Hashes…' : '🛡️ Verify Hash Chain Integrity'}
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between text-sm shadow-2xs ${
            verificationResult.is_valid
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-rose-50 border-rose-300 text-rose-900'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <span className="text-xl">{verificationResult.is_valid ? '✅' : '⚠️'}</span>
            <div>
              <div className="font-bold">
                {verificationResult.is_valid
                  ? 'Cryptographic Integrity Confirmed: HASH CHAIN INTACT'
                  : 'INTEGRITY BREACH DETECTED: Tampered Hash'}
              </div>
              <div className="text-xs opacity-90 mt-0.5">{verificationResult.message}</div>
            </div>
          </div>
          <span className="font-mono text-xs px-3 py-1 bg-white rounded-lg border border-emerald-200 shadow-2xs font-bold text-emerald-800">
            {verificationResult.records_checked} Records Verified
          </span>
        </div>
      )}

      {/* Filter and Log Table */}
      <div className="bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm overflow-hidden">
        {/* Table Filter Header */}
        <div className="p-4 border-b border-sky-100 flex justify-between items-center bg-sky-50/50">
          <div className="text-xs font-bold text-sky-950">
            Audit Records: <span className="font-mono text-sky-700 font-black">{filteredLogs.length}</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 font-semibold">Actor Filter:</span>
            <select
              value={filterActor}
              onChange={(e) => setFilterActor(e.target.value)}
              className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-slate-800 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none shadow-2xs"
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
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-sky-50/80 text-sky-950 uppercase tracking-wider text-[11px] font-bold border-b border-sky-200">
              <tr>
                <th className="py-3 px-4">Timestamp (UTC)</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Entity</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Prev Hash &rarr; Row Hash</th>
                <th className="py-3 px-4">Details Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sky-100">
              {filteredLogs.map((log: any, idx: number) => {
                const prevShort = log.prev_hash
                  ? `${log.prev_hash.slice(0, 8)}...`
                  : 'GENESIS';
                const rowShort = log.row_hash ? `${log.row_hash.slice(0, 10)}...` : '';

                return (
                  <tr key={log.id || idx} className="hover:bg-sky-50/40 transition">
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-600 font-medium">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2.5 py-0.5 rounded-md text-[11px] font-mono font-bold bg-sky-100 text-sky-900 border border-sky-300">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-600">
                      {log.entity_type}: <span className="text-slate-900 font-bold">{log.entity_id}</span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                        {log.actor}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-[11px]">
                      <div className="text-slate-400">
                        &larr; <span title={log.prev_hash}>{prevShort}</span>
                      </div>
                      <div className="text-sky-700 font-bold" title={log.row_hash}>
                        &bull; {rowShort}
                      </div>
                    </td>
                    <td className="py-3 px-4 max-w-xs truncate font-mono text-[11px] text-slate-600">
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
