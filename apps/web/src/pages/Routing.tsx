import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  apiClient,
  RouteResult,
  CityWidePlanResult,
  RoutingNetwork,
} from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import RouteMapComponent, { ROUTE_NODES } from '../components/common/RouteMapComponent';

type PlanningMode = 'single' | 'citywide';

export default function Routing() {
  const [mode, setMode] = useState<PlanningMode>('single');
  const [selectedSector, setSelectedSector] = useState<string>('All Chennai');

  // Single Route State
  const [origin, setOrigin] = useState<string>('N_TNAGAR_CENTER');
  const [destination, setDestination] = useState<string>('SH_TNAGAR');
  const [routeResult, setRouteResult] = useState<RouteResult | null>(null);

  // Inundation Chokepoints / Road Block Barrier Toggles
  const [blockUsmanRoad, setBlockUsmanRoad] = useState<boolean>(true);
  const [blockVyasarpadiSubway, setBlockVyasarpadiSubway] = useState<boolean>(false);
  const [blockVelacheryBypass, setBlockVelacheryBypass] = useState<boolean>(false);
  const [blockJafferkhanpetCauseway, setBlockJafferkhanpetCauseway] = useState<boolean>(false);

  // City-Wide Plan State
  const [cityWidePlan, setCityWidePlan] = useState<CityWidePlanResult | null>(null);

  // Fetch Network Topology
  const { data: network } = useQuery<RoutingNetwork>({
    queryKey: ['routingNetwork'],
    queryFn: apiClient.fetchRoutingNetwork,
    staleTime: 60000,
  });

  // Build active barrier overlay
  const buildOverlay = () => {
    const overlay: Record<string, number> = {};
    if (blockUsmanRoad) {
      overlay['N_TNAGAR_CENTER:N_USMAN_RD'] = 0.95;
    }
    if (blockVyasarpadiSubway) {
      overlay['N_VYASARPADI:SH_PERAMBUR'] = 0.95;
    }
    if (blockVelacheryBypass) {
      overlay['N_VELACHERY_MAIN:SH_GURUNANAK'] = 0.95;
    }
    if (blockJafferkhanpetCauseway) {
      overlay['N_JAFFERKHANPET:SH_GUINDY'] = 0.95;
    }
    return overlay;
  };

  // Compute active blocked edges for map
  const activeBlockedEdges: Array<[string, string]> = [];
  if (blockUsmanRoad) activeBlockedEdges.push(['N_TNAGAR_CENTER', 'N_USMAN_RD']);
  if (blockVyasarpadiSubway) activeBlockedEdges.push(['N_VYASARPADI', 'SH_PERAMBUR']);
  if (blockVelacheryBypass) activeBlockedEdges.push(['N_VELACHERY_MAIN', 'SH_GURUNANAK']);
  if (blockJafferkhanpetCauseway) activeBlockedEdges.push(['N_JAFFERKHANPET', 'SH_GUINDY']);

  // Mutation for single route calculation
  const routeMutation = useMutation({
    mutationFn: () => {
      const overlay = buildOverlay();
      return apiClient.calculateRoute(origin, destination, overlay);
    },
    onSuccess: (data) => {
      setRouteResult(data);
      setCityWidePlan(null); // Focus on single route
    },
  });

  // Mutation for City-Wide Evacuation Plan Simulation
  const cityWidePlanMutation = useMutation({
    mutationFn: () => {
      const overlay = buildOverlay();
      return apiClient.simulateCityWidePlan(selectedSector, overlay);
    },
    onSuccess: (data) => {
      setCityWidePlan(data);
      setRouteResult(null); // Clear single route to display all corridors
    },
  });

  const handleComputeSingle = (e: React.FormEvent) => {
    e.preventDefault();
    routeMutation.mutate();
  };

  const handleSimulateCityWide = () => {
    cityWidePlanMutation.mutate();
  };

  // Filtered origins and shelters based on sector
  const origins = (network?.origins || Object.entries(ROUTE_NODES).filter(([_, v]) => !v.is_shelter).map(([k, v]) => ({ id: k, ...v }))).filter(
    (n) => selectedSector === 'All Chennai' || n.sector === selectedSector
  );

  const shelters = (network?.shelters || Object.entries(ROUTE_NODES).filter(([_, v]) => v.is_shelter).map(([k, v]) => ({ id: k, ...v, is_shelter: true as const, capacity: v.capacity || 2000, safety: v.safety || 0.9 }))).filter(
    (s) => selectedSector === 'All Chennai' || s.sector === selectedSector
  );

  // Auto-assign nearest safest shelter for the currently selected origin
  const handleAutoAssignShelter = () => {
    const originNode = ROUTE_NODES[origin];
    if (!originNode) return;
    const availableShelters = Object.entries(ROUTE_NODES).filter(([_, n]) => n.is_shelter);

    let bestId = destination;
    let minScore = Infinity;

    availableShelters.forEach(([id, s]) => {
      const dLon = s.pos[0] - originNode.pos[0];
      const dLat = s.pos[1] - originNode.pos[1];
      const dist = Math.sqrt(dLon * dLon + dLat * dLat);
      // prioritize same sector and short distance
      const sectorPenalty = s.sector === originNode.sector ? 0 : 0.05;
      const score = dist + sectorPenalty;
      if (score < minScore) {
        minScore = score;
        bestId = id;
      }
    });

    setDestination(bestId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black text-sky-950 tracking-tight">
              Chennai Flood Evacuation & Shelter Logistics
            </h2>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-600 mt-1">
            Dynamic flood-aware evacuation corridors and relief camp allocations across North, Central, and South Chennai.
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-sky-100/70 rounded-xl border border-sky-200">
          <button
            type="button"
            onClick={() => {
              setMode('single');
              setCityWidePlan(null);
            }}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-lg transition ${
              mode === 'single'
                ? 'bg-sky-600 text-white shadow-xs'
                : 'text-slate-700 hover:text-sky-950 hover:bg-sky-200/50'
            }`}
          >
            🚗 Point-to-Point Route
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('citywide');
              if (!cityWidePlan) {
                handleSimulateCityWide();
              }
            }}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${
              mode === 'citywide'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-slate-700 hover:text-emerald-950 hover:bg-emerald-200/50'
            }`}
          >
            <span>⚡</span>
            <span>Simulate City-Wide Plan</span>
          </button>
        </div>
      </div>

      {/* Sector Selection Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white/95 rounded-xl border border-sky-200/90 shadow-2xs backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-sky-950 uppercase tracking-wider">GCC Sector:</span>
          {['All Chennai', 'North Chennai', 'Central Chennai', 'South Chennai'].map((sec) => (
            <button
              key={sec}
              type="button"
              onClick={() => setSelectedSector(sec)}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                selectedSector === sec
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-sky-50 text-slate-600 hover:bg-sky-100 hover:text-sky-900 border border-sky-200'
              }`}
            >
              {sec}
            </button>
          ))}
        </div>

        <div className="text-xs text-slate-500 font-medium flex items-center gap-2">
          <span>🛡️ 12 Designated Relief Camps</span>
          <span>•</span>
          <span>📍 18 Vulnerable Catchment Hubs</span>
        </div>
      </div>

      {/* Main Grid: Parameters on Left, Map & Analytics on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Route Configuration & Inundation Barrier Simulation */}
        <div className="space-y-4">
          {mode === 'single' ? (
            /* Single Route Control Panel */
            <div className="p-5 bg-sky-50/95 rounded-2xl border border-sky-200/90 shadow-sm space-y-4 backdrop-blur">
              <div className="flex justify-between items-center border-b border-sky-200 pb-2">
                <h3 className="text-base font-bold text-sky-950">Route Parameters</h3>
                <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-sky-200 text-sky-900">
                  {selectedSector}
                </span>
              </div>

              <form onSubmit={handleComputeSingle} className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-sky-900 uppercase tracking-wider flex justify-between">
                    <span>Emergency Origin Hub</span>
                    <span className="text-[10px] text-slate-500 font-normal">({origins.length} available)</span>
                  </label>
                  <select
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                    className="w-full mt-1.5 bg-white border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 font-medium focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-2xs"
                  >
                    {origins.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name} ({o.sector} · {o.zone})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold text-sky-900 uppercase tracking-wider">
                      Target Relief Camp / Shelter
                    </label>
                    <button
                      type="button"
                      onClick={handleAutoAssignShelter}
                      className="text-[10px] font-bold text-sky-700 hover:text-sky-900 hover:underline"
                    >
                      🎯 Auto-Assign Nearest
                    </button>
                  </div>
                  <select
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    className="w-full mt-1.5 bg-white border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 font-medium focus:border-sky-500 focus:ring-1 focus:ring-sky-500 shadow-2xs"
                  >
                    {shelters.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.sector} · Cap: {s.capacity?.toLocaleString()})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Simulated Inundation Barriers (Chennai Chokepoints) */}
                <div className="p-3.5 bg-white rounded-xl border border-amber-200 shadow-2xs space-y-2.5">
                  <span className="text-xs font-bold text-amber-950 uppercase tracking-wide flex items-center gap-1.5">
                    <span>⛔</span> Simulated Inundation Road Closures
                  </span>

                  <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={blockUsmanRoad}
                      onChange={(e) => setBlockUsmanRoad(e.target.checked)}
                      className="w-4 h-4 rounded text-amber-600 border-slate-300 focus:ring-amber-500 mt-0.5"
                    />
                    <div>
                      <span className="font-semibold text-slate-900">South Usman Subway (Central)</span>
                      <p className="text-[10px] text-slate-500">Forces bypass via elevated Chamiers / Anna Salai.</p>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={blockVyasarpadiSubway}
                      onChange={(e) => setBlockVyasarpadiSubway(e.target.checked)}
                      className="w-4 h-4 rounded text-amber-600 border-slate-300 focus:ring-amber-500 mt-0.5"
                    />
                    <div>
                      <span className="font-semibold text-slate-900">Vyasarpadi Jeeva Subway (North)</span>
                      <p className="text-[10px] text-slate-500">Diverts traffic to Basin Bridge Flyover.</p>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={blockVelacheryBypass}
                      onChange={(e) => setBlockVelacheryBypass(e.target.checked)}
                      className="w-4 h-4 rounded text-amber-600 border-slate-300 focus:ring-amber-500 mt-0.5"
                    />
                    <div>
                      <span className="font-semibold text-slate-900">Velachery Lake Underpass (South)</span>
                      <p className="text-[10px] text-slate-500">Reroutes to Guindy-Velachery high ridge.</p>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={blockJafferkhanpetCauseway}
                      onChange={(e) => setBlockJafferkhanpetCauseway(e.target.checked)}
                      className="w-4 h-4 rounded text-amber-600 border-slate-300 focus:ring-amber-500 mt-0.5"
                    />
                    <div>
                      <span className="font-semibold text-slate-900">Jafferkhanpet Causeway (Adyar River)</span>
                      <p className="text-[10px] text-slate-500">Avoids river backflow overtopping.</p>
                    </div>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={routeMutation.isPending}
                  className="w-full py-2.5 bg-sky-600 hover:bg-sky-700 text-white font-bold rounded-xl text-sm transition shadow-xs disabled:opacity-50"
                >
                  {routeMutation.isPending ? 'Calculating Safe Corridor…' : 'Compute Safe Route →'}
                </button>
              </form>
            </div>
          ) : (
            /* City-Wide Simulation Action Panel */
            <div className="p-5 bg-linear-to-b from-emerald-50 to-white rounded-2xl border border-emerald-200 shadow-sm space-y-4">
              <div className="border-b border-emerald-100 pb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded">
                  System-Wide Model
                </span>
                <h3 className="text-base font-black text-emerald-950 mt-1">
                  City-Wide Evacuation Simulation
                </h3>
                <p className="text-xs text-slate-600 mt-1">
                  Simulates optimal evacuation allocations for all 18 vulnerable hubs across Chennai to 12 relief camps.
                </p>
              </div>

              {/* Inundation barriers during simulation */}
              <div className="p-3 bg-white rounded-xl border border-amber-200 shadow-2xs space-y-2 text-xs">
                <span className="font-bold text-amber-900">Active Flood Inundation Barriers:</span>
                <div className="space-y-1.5 text-slate-700 text-[11px]">
                  <div className="flex items-center justify-between">
                    <span>Usman Road Subway (Central)</span>
                    <span className="font-bold text-rose-700">{blockUsmanRoad ? '⛔ BLOCKED' : '✓ OPEN'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Vyasarpadi Subway (North)</span>
                    <span className="font-bold text-rose-700">{blockVyasarpadiSubway ? '⛔ BLOCKED' : '✓ OPEN'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Velachery Bypass (South)</span>
                    <span className="font-bold text-rose-700">{blockVelacheryBypass ? '⛔ BLOCKED' : '✓ OPEN'}</span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleSimulateCityWide}
                disabled={cityWidePlanMutation.isPending}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-black rounded-xl text-sm transition shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <span>⚡</span>
                <span>
                  {cityWidePlanMutation.isPending
                    ? 'Simulating Full Evacuation Plan…'
                    : `Simulate Plan (${selectedSector})`}
                </span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode('single');
                  setCityWidePlan(null);
                }}
                className="w-full py-2 bg-white hover:bg-sky-50 text-slate-700 border border-slate-300 font-bold rounded-xl text-xs transition"
              >
                ← Return to Individual Route Planning
              </button>
            </div>
          )}

          {/* Quick Relief Camp Roster */}
          <div className="p-4 bg-white/95 rounded-2xl border border-sky-200/90 shadow-2xs space-y-3">
            <div className="flex justify-between items-center">
              <h4 className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                Relief Camps in {selectedSector}
              </h4>
              <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                {shelters.length} Available
              </span>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {shelters.map((s) => (
                <div
                  key={s.id}
                  onClick={() => {
                    setDestination(s.id);
                    setMode('single');
                  }}
                  className={`p-2.5 rounded-xl border text-xs cursor-pointer transition flex items-center justify-between ${
                    destination === s.id && mode === 'single'
                      ? 'border-emerald-500 bg-emerald-50/70 font-semibold text-emerald-950'
                      : 'border-slate-100 hover:border-sky-300 hover:bg-sky-50/50 text-slate-800'
                  }`}
                >
                  <div>
                    <div className="font-bold text-slate-900">{s.name}</div>
                    <div className="text-[10px] text-slate-500">{s.sector} · {s.zone}</div>
                  </div>
                  <div className="text-right">
                    <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-900 rounded font-mono font-bold text-[10px]">
                      {s.capacity?.toLocaleString()} beds
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Chennai GIS Map & Simulation Results */}
        <div className="lg:col-span-2 space-y-5">
          {/* Interactive Map with Full Chennai Network */}
          <RouteMapComponent
            originNode={origin}
            destinationNode={destination}
            routeNodes={routeResult?.route_nodes}
            corridors={cityWidePlan?.corridors}
            blockedEdges={activeBlockedEdges}
            selectedSector={selectedSector}
            onSelectOrigin={(id) => {
              setOrigin(id);
              setMode('single');
            }}
            onSelectDestination={(id) => {
              setDestination(id);
              setMode('single');
            }}
            height="460px"
          />

          {/* Results: Point-to-Point Path vs. City-Wide Evacuation Plan */}
          {mode === 'citywide' && cityWidePlan ? (
            /* City-Wide Simulation Dashboard */
            <div className="p-6 bg-white/95 rounded-2xl border border-emerald-200/90 shadow-sm space-y-5">
              <div className="flex flex-wrap justify-between items-center gap-2 border-b border-emerald-100 pb-3">
                <div>
                  <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-900 rounded">
                    Simulated Optimal Plan
                  </span>
                  <h3 className="text-xl font-black text-sky-950 mt-1">
                    Greater Chennai Evacuation Master Plan
                  </h3>
                  <p className="text-xs text-slate-500">
                    Calculated optimal paths for all {cityWidePlan.total_evacuation_corridors} vulnerable hubs to designated relief camps.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleSimulateCityWide}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-2xs"
                >
                  ↻ Re-simulate
                </button>
              </div>

              {/* Top Key Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 bg-emerald-50/70 rounded-xl border border-emerald-200 text-center shadow-2xs">
                  <p className="text-xs font-bold text-slate-500">Total Safeguarded</p>
                  <p className="text-2xl font-black text-emerald-700 mt-1 font-mono">
                    {cityWidePlan.total_evacuees_safeguarded.toLocaleString()}
                  </p>
                  <p className="text-[10px] text-emerald-800 font-semibold">Evacuees Rerouted</p>
                </div>

                <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-200 text-center shadow-2xs">
                  <p className="text-xs font-bold text-slate-500">Avg Route Safety</p>
                  <p className="text-2xl font-black text-sky-700 mt-1 font-mono">
                    {cityWidePlan.avg_route_safety_score} <span className="text-xs font-normal text-slate-400">/ 100</span>
                  </p>
                  <p className="text-[10px] text-sky-800 font-semibold">SRS Quality Index</p>
                </div>

                <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-200 text-center shadow-2xs">
                  <p className="text-xs font-bold text-slate-500">Avg Evac Distance</p>
                  <p className="text-2xl font-black text-slate-900 mt-1 font-mono">
                    {cityWidePlan.avg_evacuation_distance_km} km
                  </p>
                  <p className="text-[10px] text-slate-600 font-semibold">Per-Corridor Mean</p>
                </div>

                <div className="p-3.5 bg-sky-50/70 rounded-xl border border-sky-200 text-center shadow-2xs">
                  <p className="text-xs font-bold text-slate-500">Avg Travel Duration</p>
                  <p className="text-2xl font-black text-indigo-700 mt-1 font-mono">
                    {cityWidePlan.avg_evacuation_duration_min} min
                  </p>
                  <p className="text-[10px] text-indigo-800 font-semibold">Emergency Flow</p>
                </div>
              </div>

              {/* Shelter Occupancy & Relief Camp Allocations */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-sky-950 uppercase tracking-wider flex items-center justify-between">
                  <span>Relief Camp Capacity & Occupancy Matrix</span>
                  <span className="text-slate-500 font-normal">{cityWidePlan.shelters.length} Designated Camps</span>
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto pr-1">
                  {cityWidePlan.shelters.map((sh) => (
                    <div
                      key={sh.shelter_id}
                      className="p-3.5 bg-white rounded-xl border border-slate-200 shadow-2xs space-y-2 hover:border-emerald-300 transition"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-bold text-sm text-slate-900">{sh.shelter_name}</div>
                          <div className="text-[11px] text-slate-500">{sh.sector}</div>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            sh.occupancy_rate > 90
                              ? 'bg-rose-100 text-rose-800'
                              : sh.occupancy_rate > 60
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {sh.occupancy_rate}% Full
                        </span>
                      </div>

                      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            sh.occupancy_rate > 90
                              ? 'bg-rose-500'
                              : sh.occupancy_rate > 60
                              ? 'bg-amber-500'
                              : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, sh.occupancy_rate)}%` }}
                        />
                      </div>

                      <div className="flex justify-between text-[11px] text-slate-600 font-medium pt-0.5">
                        <span>Allocated: {sh.evacuees_allocated.toLocaleString()} people</span>
                        <span>Capacity: {sh.capacity.toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Active Corridors Breakdown */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-sky-950 uppercase tracking-wider">
                  Active Evacuation Corridors ({cityWidePlan.corridors.length})
                </h4>
                <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden max-h-56 overflow-y-auto">
                  {cityWidePlan.corridors.map((c) => (
                    <div
                      key={c.origin_id}
                      className="p-3 bg-white hover:bg-sky-50/50 flex flex-wrap items-center justify-between text-xs transition gap-2"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{c.origin_name}</span>
                        <span className="text-sky-500">➔</span>
                        <span className="font-bold text-emerald-800">{c.target_shelter_name}</span>
                      </div>
                      <div className="flex items-center gap-3 font-mono text-slate-600">
                        <span>{c.evacuees_assigned.toLocaleString()} people</span>
                        <span>{c.distance_km} km</span>
                        <span>{c.duration_min} min</span>
                        <span className="font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          SRS {c.srs_score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Single Route Details Panel */
            <div className="p-5 bg-white/95 rounded-2xl border border-sky-200/90 shadow-sm">
              <h3 className="text-base font-bold text-sky-950 mb-3">Evacuation Path Assessment</h3>
              {routeResult ? (
                <div className="space-y-4">
                  {routeResult.status === 'ROUTE_FOUND' ? (
                    <>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="p-3.5 bg-emerald-50/70 rounded-xl border border-emerald-200 text-center shadow-2xs">
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
                          {routeResult.route_nodes.map((node, idx) => {
                            const nodeObj = ROUTE_NODES[node];
                            return (
                              <React.Fragment key={node}>
                                <span className="px-3 py-1 text-xs font-bold bg-white text-sky-900 rounded-lg border border-sky-200 shadow-2xs">
                                  {nodeObj?.name || node}
                                </span>
                                {idx < routeResult.route_nodes.length - 1 && (
                                  <span className="text-sky-500 font-bold text-sm">➔</span>
                                )}
                              </React.Fragment>
                            );
                          })}
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
                <div className="text-center py-6 text-slate-500 text-sm">
                  <p className="font-medium">Select origin and relief camp, then click &ldquo;Compute Safe Route&rdquo;.</p>
                  <p className="text-xs mt-1 text-slate-400">
                    Or switch to &ldquo;Simulate City-Wide Plan&rdquo; on the top right to simulate all 18 evacuation corridors simultaneously.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
