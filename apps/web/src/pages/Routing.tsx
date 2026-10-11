import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient, RouteResult } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import RouteMapComponent from '../components/common/RouteMapComponent';

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
            <h2 className="text-2xl font-black text-sky-950 tracking-tight">Response Route Planning</h2>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-600 mt-1">
            Dynamic flood-aware evacuation and emergency routing across Chennai road network.
          </p>
        </div>
      </div>

      <div role="note" className="rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-xs text-amber-900 font-medium shadow-2xs leading-relaxed">
        <strong>Illustrative Prototype Notice:</strong> Road graph nodes, relief shelter allocations, and simulated inundation barriers represent calibrated decision models; observe on-ground flood directives before dispatch.
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Route Configuration Panel (Light Blue) */}
        <div className="p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm h-fit space-y-4 backdrop-blur">
          <h3 className="text-base font-bold text-sky-950">Route Parameters</h3>
          <form onSubmit={handleCompute} className="space-y-4">
            <div>
              <label className="text-xs font-bold text-sky-900 uppercase tracking-wider">
                Emergency Origin Node
              </label>
              <select
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="w-full mt-1.5 bg-white border border-slate-300 rounded-xl p-2.5 text-sm text-slate-800 font-medium focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-2xs"
              >
                <option value="N_TNAGAR_CENTER">Panagal Park (T. Nagar Center)</option>
                <option value="N_USMAN_RD">South Usman Road</option>
                <option value="N_MAMBALAM_STN">Mambalam Railway Station</option>
                <option value="N_ANNA_SALAI">Nandanam Anna Salai</option>
                <option value="N_VELACHERY_MAIN">Velachery Bypass</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-sky-900 uppercase tracking-wider">
                Target Shelter Destination
              </label>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full mt-1.5 bg-white border border-slate-300 rounded-xl p-2.5 text-sm text-slate-800 font-medium focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-2xs"
              >
                <option value="SH_TNAGAR">T. Nagar Relief Hall</option>
                <option value="SH_MAMBALAM">Mambalam Relief Camp</option>
                <option value="SH_GURUNANAK">Guru Nanak Evacuation Center</option>
              </select>
            </div>

            <div className="p-3.5 bg-white rounded-xl border border-amber-200 shadow-2xs">
              <label className="flex items-center gap-2.5 text-xs text-amber-900 cursor-pointer">
                <input
                  type="checkbox"
                  checked={blockUsmanRoad}
                  onChange={(e) => setBlockUsmanRoad(e.target.checked)}
                  className="w-4 h-4 rounded text-amber-600 border-slate-300 focus:ring-amber-500"
                />
                <span className="font-bold">Simulate Usman Road Subway Inundation (&ge; 90% risk)</span>
              </label>
              <p className="text-[11px] text-slate-500 mt-1 pl-6">
                Applies a synthetic graph edge penalty to force routing through higher-elevation arterials.
              </p>
            </div>

            <button
              type="submit"
              disabled={routeMutation.isPending}
              className="w-full py-2.5 bg-sky-600 hover:bg-sky-700 text-white font-bold rounded-xl text-sm transition shadow-xs disabled:opacity-50"
            >
              {routeMutation.isPending ? 'Computing Shortest Safe Path…' : 'Compute Safe Route →'}
            </button>
          </form>
        </div>

        {/* Route Map & Analysis */}
        <div className="lg:col-span-2 space-y-5">
          {/* Interactive GIS Route Map */}
          <RouteMapComponent
            originNode={origin}
            destinationNode={destination}
            routeNodes={routeResult?.route_nodes}
            blockUsmanRoad={blockUsmanRoad}
            height="380px"
          />

          {/* Results details */}
          <div className="p-5 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm">
            <h3 className="text-base font-bold text-sky-950 mb-3">Evacuation Path Assessment</h3>
            {routeResult ? (
              <div className="space-y-4">
                {routeResult.status === 'ROUTE_FOUND' ? (
                  <>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-100 text-center shadow-2xs">
                        <p className="text-xs font-bold text-slate-500">Route Safety Score</p>
                        <p className="text-2xl font-black text-emerald-700 mt-1 font-mono">
                          {routeResult.srs_score} <span className="text-xs font-normal text-slate-400">/ 100</span>
                        </p>
                      </div>
                      <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-100 text-center shadow-2xs">
                        <p className="text-xs font-bold text-slate-500">Total Distance</p>
                        <p className="text-xl font-black text-slate-900 mt-1 font-mono">
                          {(routeResult.distance_m / 1000).toFixed(2)} km
                        </p>
                      </div>
                      <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-100 text-center shadow-2xs">
                        <p className="text-xs font-bold text-slate-500">Estimated Duration</p>
                        <p className="text-xl font-black text-sky-900 mt-1 font-mono">
                          {routeResult.duration_min} min
                        </p>
                      </div>
                      <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-100 text-center shadow-2xs">
                        <p className="text-xs font-bold text-slate-500">Peak Edge Hazard</p>
                        <p className="text-xl font-black text-amber-600 mt-1 font-mono">
                          {(routeResult.max_edge_risk * 100).toFixed(0)}%
                        </p>
                      </div>
                    </div>

                    {/* Waypoint Hop Sequence */}
                    <div className="p-4 bg-sky-50/50 rounded-xl border border-sky-100">
                      <p className="text-xs font-bold text-sky-950 uppercase tracking-wider mb-2">
                        Turn-by-Turn Waypoint Sequence
                      </p>
                      <div className="flex flex-wrap items-center gap-2">
                        {routeResult.route_nodes.map((node, idx) => (
                          <React.Fragment key={node}>
                            <span className="px-3 py-1 text-xs font-mono font-bold bg-white text-sky-900 rounded-lg border border-sky-200 shadow-2xs">
                              {node}
                            </span>
                            {idx < routeResult.route_nodes.length - 1 && (
                              <span className="text-sky-500 font-bold text-sm">➔</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-6 bg-rose-50 border border-rose-200 rounded-xl text-center shadow-2xs">
                    <p className="text-rose-800 font-bold text-base">⚠️ {routeResult.status}</p>
                    <p className="text-sm text-rose-700 mt-1 font-medium">{routeResult.message}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-500 font-medium">
                Select origin and target shelter, then click &quot;Compute Safe Route&quot; to calculate shortest path and display topology.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
