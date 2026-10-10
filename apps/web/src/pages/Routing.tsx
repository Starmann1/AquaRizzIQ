import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient, RouteResult } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';

export default function Routing() {
  const [origin, setOrigin] = useState<string>('N_TNAGAR_CENTER');
  const [destination, setDestination] = useState<string>('SH_TNAGAR');
  const [blockUsmanRoad, setBlockUsmanRoad] = useState<boolean>(false);
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null);

  const routeMutation = useMutation({
    mutationFn: () => {
      const overlay: Record<string, number> = {};
      if (blockUsmanRoad) {
        overlay['N_TNAGAR_CENTER:N_USMAN_RD'] = 0.95; // Block Usman subway
      }
      return apiClient.calculateRoute(origin, destination, overlay);
    },
    onSuccess: (data) => {
      setRouteResult(data);
    },
  });

  const handleCompute = (e: React.FormEvent) => {
    e.preventDefault();
    routeMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-white">Risk-Aware Evacuation Routing</h2>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Calculates flood-penalized Dijkstra shortest paths to designated shelters using NetworkX (P1-16).
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Route Configuration Panel */}
        <div className="p-5 bg-slate-800/80 rounded-lg border border-slate-700">
          <h3 className="text-base font-bold text-white mb-4">Route Parameters</h3>
          <form onSubmit={handleCompute} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase">
                Evacuation Origin
              </label>
              <select
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="w-full mt-1 bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200"
              >
                <option value="N_TNAGAR_CENTER">Panagal Park (T. Nagar Center)</option>
                <option value="N_USMAN_RD">South Usman Road</option>
                <option value="N_MAMBALAM_STN">Mambalam Railway Station</option>
                <option value="N_ANNA_SALAI">Nandanam Anna Salai</option>
                <option value="N_VELACHERY_MAIN">Velachery Bypass</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase">
                Designated Safe Shelter
              </label>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full mt-1 bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200"
              >
                <option value="SH_TNAGAR">T. Nagar Relief Hall (Capacity 500)</option>
                <option value="SH_MAMBALAM">Mambalam Relief Camp (Capacity 450)</option>
                <option value="SH_GURUNANAK">Guru Nanak Indoor Stadium (Capacity 1200)</option>
              </select>
            </div>

            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <label className="flex items-center gap-2.5 text-xs text-amber-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={blockUsmanRoad}
                  onChange={(e) => setBlockUsmanRoad(e.target.checked)}
                  className="w-4 h-4 rounded text-amber-500 bg-slate-800 border-slate-600"
                />
                <span className="font-semibold">Simulate Usman Road Subway Inundation (&ge; 90% risk)</span>
              </label>
              <p className="text-xs text-slate-500 mt-1 pl-6">
                Forces algorithm to route around submerged low-lying underpasses.
              </p>
            </div>

            <button
              type="submit"
              disabled={routeMutation.isPending}
              className="w-full py-2 bg-sky-600 hover:bg-sky-500 text-white font-semibold rounded text-sm transition disabled:opacity-50"
            >
              {routeMutation.isPending ? 'Computing Safe Path...' : 'Compute Safe Route'}
            </button>
          </form>
        </div>

        {/* Route Results & Metrics */}
        <div className="lg:col-span-2 p-5 bg-slate-800/80 rounded-lg border border-slate-700">
          <h3 className="text-base font-bold text-white mb-4">Evacuation Path Analysis</h3>

          {routeResult ? (
            <div className="space-y-4">
              {routeResult.status === 'ROUTE_FOUND' ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60 text-center">
                      <p className="text-xs text-slate-400">Safe Route Score</p>
                      <p className="text-2xl font-bold text-emerald-400 mt-1">
                        {routeResult.srs_score} <span className="text-xs text-slate-500">/ 100</span>
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60 text-center">
                      <p className="text-xs text-slate-400">Total Distance</p>
                      <p className="text-xl font-bold text-white mt-1">
                        {(routeResult.distance_m / 1000).toFixed(2)} km
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60 text-center">
                      <p className="text-xs text-slate-400">Estimated Duration</p>
                      <p className="text-xl font-bold text-sky-400 mt-1">
                        {routeResult.duration_min} min
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60 text-center">
                      <p className="text-xs text-slate-400">Max Edge Risk</p>
                      <p className="text-xl font-bold text-amber-400 mt-1">
                        {(routeResult.max_edge_risk * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>

                  {/* Waypoint Hop Sequence */}
                  <div className="p-4 bg-slate-900/50 rounded border border-slate-700/60">
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                      Navigation Waypoint Sequence
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      {routeResult.route_nodes.map((node, idx) => (
                        <React.Fragment key={node}>
                          <span className="px-2.5 py-1 text-xs font-mono bg-slate-800 text-sky-300 rounded border border-slate-700">
                            {node}
                          </span>
                          {idx < routeResult.route_nodes.length - 1 && (
                            <span className="text-slate-600 font-bold">➔</span>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="p-6 bg-rose-950/40 border border-rose-700/60 rounded text-center">
                  <p className="text-rose-400 font-bold text-base">⚠️ {routeResult.status}</p>
                  <p className="text-sm text-slate-300 mt-1">{routeResult.message}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-slate-500">
              Click &quot;Compute Safe Route&quot; to calculate optimal evacuation corridors.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
