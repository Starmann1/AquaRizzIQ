import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function Recommendation() {
  const navigate = useNavigate();
  const [filterPriority, setFilterPriority] = useState<string>('ALL');

  const { data: recommendations, isLoading, error } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => apiClient.fetchRecommendations(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const allRecs = recommendations || [];
  const filteredRecs = filterPriority === 'ALL'
    ? allRecs
    : allRecs.filter((r: any) => r.priority === filterPriority);

  return (
    <main className="mx-auto max-w-5xl space-y-6 pb-12">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-sky-200/90 bg-white/95 p-6 shadow-sm backdrop-blur">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-sky-800 bg-sky-100 px-2.5 py-0.5 rounded-full border border-sky-300">
            Decision Support & Action Catalogue
          </span>
          <h1 className="mt-2 text-2xl font-black text-sky-950 tracking-tight">
            Municipal Response Recommendations
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Automated policy action synthesis grounded in live PostgreSQL risk assessments
          </p>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-2">
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => (
            <button
              key={p}
              onClick={() => setFilterPriority(p)}
              className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase transition ${
                filterPriority === p
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-white border border-sky-200 text-slate-600 hover:bg-sky-50 hover:text-sky-950'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </header>

      {/* Summary KPI Bar */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-sky-200/90 bg-white/95 p-4 shadow-2xs">
          <span className="text-xs text-slate-500 uppercase font-semibold">Total Actions</span>
          <div className="mt-1 text-2xl font-black text-slate-900 font-mono">{allRecs.length}</div>
        </div>
        <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-4 shadow-2xs">
          <span className="text-xs text-rose-700 uppercase font-semibold">High Priority</span>
          <div className="mt-1 text-2xl font-black text-rose-700 font-mono">
            {allRecs.filter((r: any) => r.priority === 'HIGH').length}
          </div>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 shadow-2xs">
          <span className="text-xs text-amber-800 uppercase font-semibold">Medium Priority</span>
          <div className="mt-1 text-2xl font-black text-amber-800 font-mono">
            {allRecs.filter((r: any) => r.priority === 'MEDIUM').length}
          </div>
        </div>
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 shadow-2xs">
          <span className="text-xs text-emerald-700 uppercase font-semibold">Routine Operations</span>
          <div className="mt-1 text-2xl font-black text-emerald-700 font-mono">
            {allRecs.filter((r: any) => r.priority === 'LOW').length}
          </div>
        </div>
      </section>

      {/* Recommendations Feed */}
      <section className="space-y-3">
        {filteredRecs.length > 0 ? (
          filteredRecs.map((rec: any, idx: number) => {
            const isHigh = rec.priority === 'HIGH';
            const isMed = rec.priority === 'MEDIUM';
            return (
              <div
                key={rec.id || idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-sky-200/80 bg-white/95 p-5 shadow-xs hover:border-sky-300 hover:shadow-sm transition"
              >
                <div className="flex items-start gap-4">
                  <span
                    className={`mt-0.5 rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border shadow-2xs ${
                      isHigh
                        ? 'bg-rose-50 text-rose-700 border-rose-300'
                        : isMed
                        ? 'bg-amber-50 text-amber-800 border-amber-300'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-300'
                    }`}
                  >
                    {rec.priority}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900 capitalize">
                        {rec.type?.replace(/_/g, ' ') || 'Response Action'}
                      </h3>
                      {rec.ward_id && (
                        <span className="rounded-md bg-sky-50 px-2 py-0.5 text-xs font-mono font-bold text-sky-800 border border-sky-200">
                          {rec.ward_id}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-slate-700 leading-relaxed">{rec.description}</p>
                    <span className="mt-2 inline-block text-[11px] text-slate-400 font-mono font-medium">
                      Policy Rule: ACT-{rec.type || 'DEFAULT'} · Generated: {rec.created_at ? new Date(rec.created_at).toLocaleTimeString() : 'Current Cycle'}
                    </span>
                  </div>
                </div>

                <div className="flex sm:flex-col items-center sm:items-end gap-2 shrink-0">
                  <span className="text-[11px] text-slate-500 font-medium">Requires Human Signoff</span>
                  <button
                    className="rounded-xl bg-sky-600 hover:bg-sky-700 px-4 py-2 text-xs font-bold text-white shadow-xs transition"
                    onClick={() => navigate('/review')}
                  >
                    Review in Emergency Gate →
                  </button>
                </div>
              </div>
            );
          })
        ) : (
          <div className="rounded-xl border border-sky-200 bg-white/95 p-8 text-center text-slate-500">
            No recommendations match the selected filter.
          </div>
        )}
      </section>
    </main>
  );
}
