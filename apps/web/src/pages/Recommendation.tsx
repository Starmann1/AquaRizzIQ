import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient, WardRisk } from '../api/client';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export interface ActionItem {
  id: string;
  ward_id: string;
  ward_name: string;
  zone: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  type: string;
  description: string;
  created_at: string;
}

const generateActionsForWard = (ward: WardRisk): ActionItem[] => {
  const wid = ward.ward_id;
  const wname = ward.ward_name || wid;
  const zname = ward.zone || 'Greater Chennai';
  const isCritical = ward.risk_level === 'CRITICAL';
  const isHigh = ward.risk_level === 'HIGH';
  const isMed = ward.risk_level === 'MEDIUM';

  if (isCritical) {
    return [
      {
        id: `ACT-${wid}-01`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'HIGH',
        type: 'Deploy Emergency Dewatering Pumps',
        description: `Stage two 100-HP diesel drainage pumps at vulnerable low-lying outfalls in ${wname} to relieve storm drain surcharge.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-02`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'HIGH',
        type: 'Clear Sluice Gates & Drainage Culverts',
        description: `Dispatch mechanized excavator gang to clear floating debris, hyacinth, and plastic blockages at downstream culverts in ${wname}.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-03`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'HIGH',
        type: 'Station Rescue Boat Crews on Standby',
        description: `Position disaster rescue teams and inflatable boats near primary arterial corridors in ${wname} for immediate evacuation.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-04`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Open Emergency Relief Shelters',
        description: `Prepare designated community relief shelters in ${zname} with emergency rations, drinking water supply, and medical backup.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-05`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Broadcast Public Flood Advisory',
        description: `Broadcast emergency precautionary flood advisories to residents in low-lying residential sectors of ${wname}.`,
        created_at: new Date().toISOString(),
      },
    ];
  }

  if (isHigh) {
    return [
      {
        id: `ACT-${wid}-01`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'HIGH',
        type: 'Stage High-Capacity Drainage Pumps',
        description: `Position mobile dewatering units near identified low-elevation micro-catchments in ${wname} to prevent overflow.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-02`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'HIGH',
        type: 'Clear Drain Gates & Trash Racks',
        description: `Send an excavator gang to clear floating debris and plastic waste from water discharge gates in ${wname}.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-03`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Pre-Activate Community Relief Centres',
        description: `Prepare designated community shelters in ${zname} with emergency drinking water, rations, and first aid kits.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-04`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Station Rapid Response Boat Teams',
        description: `Stage disaster response inflatable rescue boats near main roads in ${wname} for rapid evacuation response.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-05`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'LOW',
        type: 'Send Localized Flood Advisory',
        description: `Send precautionary flood text warnings and loudspeaker advisories to residents in low-lying sectors of ${wname}.`,
        created_at: new Date().toISOString(),
      },
    ];
  }

  if (isMed) {
    return [
      {
        id: `ACT-${wid}-01`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Inspect Stormwater Drain Inlets',
        description: `Inspect roadside drains and clear localized inlet grating blockages and silt accumulation in ${wname}.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-02`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Increase Sensor Polling & Monitoring',
        description: `Increase ultrasonic water level gauge polling to 5-minute intervals in ${wname} to monitor channel surcharge.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-03`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'MEDIUM',
        type: 'Pre-Stage Portable Dewatering Equipment',
        description: `Stage portable trailer-mounted pumps on standby near vulnerable road intersections in ${wname}.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-04`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'LOW',
        type: 'Community Shelter Readiness Inspection',
        description: `Check generator power and sanitation facilities at designated emergency relief centres in ${zname}.`,
        created_at: new Date().toISOString(),
      },
      {
        id: `ACT-${wid}-05`,
        ward_id: wid,
        ward_name: wname,
        zone: zname,
        priority: 'LOW',
        type: 'Routine Citizen Safety Advisory',
        description: `Advise residents in ${wname} to avoid pedestrian travel along waterlogged canal edges during heavy rainfall.`,
        created_at: new Date().toISOString(),
      },
    ];
  }

  // LOW Risk
  return [
    {
      id: `ACT-${wid}-01`,
      ward_id: wid,
      ward_name: wname,
      zone: zname,
      priority: 'LOW',
      type: 'Monitor Water Levels & Weather Telemetry',
      description: `Maintain standard continuous telemetry polling across ultrasonic drain sensors and rain gauges in ${wname}.`,
      created_at: new Date().toISOString(),
    },
    {
      id: `ACT-${wid}-02`,
      ward_id: wid,
      ward_name: wname,
      zone: zname,
      priority: 'LOW',
      type: 'Routine Drain Silt & Trash Removal',
      description: `Perform scheduled maintenance and trash clearance at primary stormwater outfalls in ${wname}.`,
      created_at: new Date().toISOString(),
    },
    {
      id: `ACT-${wid}-03`,
      ward_id: wid,
      ward_name: wname,
      zone: zname,
      priority: 'LOW',
      type: 'Inspect Sluice Gates & Outfall Flaps',
      description: `Inspect motorized sluice gates and check flap valves in ${wname} to ensure unobstructed drainage discharge.`,
      created_at: new Date().toISOString(),
    },
  ];
};

export default function Recommendation() {
  const navigate = useNavigate();
  const [selectedZone, setSelectedZone] = useState<string>('ALL');
  const [selectedWardId, setSelectedWardId] = useState<string>('ALL');
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'feed' | 'zones'>('feed');

  const { data: recommendations, isLoading: recsLoading, error: recsError } = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => apiClient.fetchRecommendations(),
  });

  const { data: risks, isLoading: risksLoading } = useQuery({
    queryKey: ['risks'],
    queryFn: apiClient.fetchRisk,
  });

  // Extract unique zones
  const zones = useMemo(() => {
    const set = new Set<string>();
    (risks || []).forEach((r) => {
      if (r.zone) set.add(r.zone);
    });
    return Array.from(set).sort();
  }, [risks]);

  // Filter wards by selected zone
  const filteredWards = useMemo(() => {
    const all = [...(risks || [])].sort((a, b) =>
      a.ward_id.localeCompare(b.ward_id, undefined, { numeric: true })
    );
    if (selectedZone === 'ALL') return all;
    return all.filter((r) => r.zone === selectedZone);
  }, [risks, selectedZone]);

  const handleZoneChange = (zone: string) => {
    setSelectedZone(zone);
    setSelectedWardId('ALL');
  };

  // Complete, consistent actions across all 200 wards and all zones in Chennai
  const allChennaiActions = useMemo(() => {
    if (!risks || risks.length === 0) return [];
    const result: ActionItem[] = [];

    // Canonical standard operating protocol actions for all 200 wards
    for (const w of risks) {
      const wardActions = generateActionsForWard(w);
      result.push(...wardActions);
    }

    return result;
  }, [risks]);

  // Actions matching the active Zone & Ward selection (before priority filtering)
  const scopedActions = useMemo(() => {
    let list = allChennaiActions;
    if (selectedWardId !== 'ALL') {
      list = list.filter((a) => a.ward_id === selectedWardId);
    } else if (selectedZone !== 'ALL') {
      list = list.filter((a) => a.zone === selectedZone);
    }
    return list;
  }, [allChennaiActions, selectedWardId, selectedZone]);

  // KPI counts strictly derived from the scoped actions (regardless of priority filter tab)
  const totalActionsCount = scopedActions.length;
  const highPriorityCount = scopedActions.filter((a) => a.priority === 'HIGH').length;
  const mediumPriorityCount = scopedActions.filter((a) => a.priority === 'MEDIUM').length;
  const lowPriorityCount = scopedActions.filter((a) => a.priority === 'LOW').length;

  // Actions filtered by the priority filter button for display in feed
  const displayActions = useMemo(() => {
    if (filterPriority === 'ALL') return scopedActions;
    return scopedActions.filter((a) => a.priority === filterPriority);
  }, [scopedActions, filterPriority]);

  // Zone summaries for Zone Overview mode (exact mathematical aggregation per zone)
  const zoneSummaries = useMemo(() => {
    if (!risks) return [];

    const map = new Map<
      string,
      {
        zone: string;
        totalActions: number;
        highPriority: number;
        mediumPriority: number;
        lowPriority: number;
        wardsCount: number;
        topWard: WardRisk | null;
      }
    >();

    for (const z of zones) {
      map.set(z, {
        zone: z,
        totalActions: 0,
        highPriority: 0,
        mediumPriority: 0,
        lowPriority: 0,
        wardsCount: 0,
        topWard: null,
      });
    }

    for (const r of risks) {
      const z = r.zone;
      if (z && map.has(z)) {
        const item = map.get(z)!;
        item.wardsCount += 1;
        if (!item.topWard || (r.hazard || 0) > (item.topWard.hazard || 0)) {
          item.topWard = r;
        }
      }
    }

    for (const act of allChennaiActions) {
      if (map.has(act.zone)) {
        const item = map.get(act.zone)!;
        item.totalActions += 1;
        if (act.priority === 'HIGH') item.highPriority += 1;
        else if (act.priority === 'MEDIUM') item.mediumPriority += 1;
        else item.lowPriority += 1;
      }
    }

    return Array.from(map.values()).sort(
      (a, b) => b.highPriority - a.highPriority || b.totalActions - a.totalActions
    );
  }, [risks, allChennaiActions, zones]);

  if (recsLoading || risksLoading) return <LoadingSpinner />;
  if (recsError) return <ErrorDisplay message={(recsError as Error).message} />;

  return (
    <main className="mx-auto max-w-6xl space-y-6 pb-12">
      {/* Header & Controls */}
      <header className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm backdrop-blur space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-sky-950 tracking-tight">
              Municipal Response Recommendations
            </h1>
            <p className="mt-1 text-sm text-slate-600 font-medium">
              Actionable flood prevention and emergency relief steps across Greater Chennai Corporation
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 rounded-xl bg-sky-50 p-1 border border-sky-200 shadow-2xs">
            <button
              type="button"
              onClick={() => setViewMode('feed')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                viewMode === 'feed'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-sky-900'
              }`}
            >
              <span>📋</span>
              <span>Actions Feed</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('zones')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                viewMode === 'zones'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-sky-900'
              }`}
            >
              <span>🗺️</span>
              <span>All Zones Overview ({zones.length})</span>
            </button>
          </div>
        </div>

        {/* Toolbar: Zone, Ward, & Priority Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-sky-100">
          <div className="flex flex-wrap items-center gap-4">
            {/* Zone Selector */}
            <div className="flex items-center gap-2">
              <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                Zone:
              </label>
              <select
                value={selectedZone}
                onChange={(e) => handleZoneChange(e.target.value)}
                className="rounded-lg border border-sky-300 bg-sky-50/80 px-3 py-1.5 text-xs font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-2xs"
              >
                <option value="ALL">All Zones ({zones.length} Zones)</option>
                {zones.map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </select>
            </div>

            {/* Ward Selector */}
            <div className="flex items-center gap-2">
              <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                Ward:
              </label>
              <select
                value={selectedWardId}
                onChange={(e) => setSelectedWardId(e.target.value)}
                className="rounded-lg border border-sky-300 bg-sky-50/80 px-3 py-1.5 text-xs font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono shadow-2xs"
              >
                <option value="ALL">All Wards in Selection</option>
                {filteredWards.map((r) => (
                  <option key={r.ward_id} value={r.ward_id}>
                    {r.ward_name} ({r.zone || r.ward_id})
                  </option>
                ))}
              </select>
            </div>

            {/* Priority Filter */}
            <div className="flex items-center gap-1.5 border-l border-sky-200/80 pl-4">
              {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setFilterPriority(p)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase transition ${
                    filterPriority === p
                      ? 'bg-sky-600 text-white shadow-xs'
                      : 'bg-white border border-sky-200 text-slate-600 hover:bg-sky-50'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* VIEW MODE 1: ALL ZONES OVERVIEW */}
      {viewMode === 'zones' && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-sky-950 uppercase tracking-wider">
              Chennai Zone-Wise Municipal Action Breakdown
            </h2>
            <span className="text-xs text-slate-500 font-medium">
              Ranked by urgency across 15 GCC Zones
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {zoneSummaries.map((zs, idx) => {
              const hasHigh = zs.highPriority > 0;
              return (
                <div
                  key={zs.zone}
                  className={`rounded-2xl border p-5 space-y-3.5 shadow-2xs transition-all ${
                    hasHigh
                      ? 'border-rose-200 bg-linear-to-b from-rose-50/70 to-white hover:border-rose-300'
                      : 'border-sky-200 bg-linear-to-b from-sky-50/70 to-white hover:border-sky-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2.5">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-400">
                          #{idx + 1}
                        </span>
                        <h3 className="text-sm font-black text-slate-900">{zs.zone}</h3>
                      </div>
                      <span className="text-[11px] text-slate-500 font-semibold">
                        {zs.wardsCount} Administrative Wards
                      </span>
                    </div>

                    <span
                      className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider border ${
                        zs.highPriority > 0
                          ? 'bg-rose-100 text-rose-800 border-rose-300'
                          : zs.mediumPriority > 0
                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      }`}
                    >
                      {zs.highPriority > 0
                        ? `${zs.highPriority} High Priority`
                        : `${zs.totalActions} Active Actions`}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg bg-white p-2 border border-slate-100 shadow-2xs">
                      <div className="text-[10px] font-bold text-rose-600 uppercase">High</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">
                        {zs.highPriority}
                      </div>
                    </div>
                    <div className="rounded-lg bg-white p-2 border border-slate-100 shadow-2xs">
                      <div className="text-[10px] font-bold text-amber-600 uppercase">Medium</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">
                        {zs.mediumPriority}
                      </div>
                    </div>
                    <div className="rounded-lg bg-white p-2 border border-slate-100 shadow-2xs">
                      <div className="text-[10px] font-bold text-emerald-600 uppercase">Routine</div>
                      <div className="text-sm font-black text-slate-800 mt-0.5">
                        {zs.lowPriority}
                      </div>
                    </div>
                  </div>

                  {zs.topWard && (
                    <div className="rounded-xl bg-slate-50 p-2.5 text-xs border border-slate-100 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase">
                          Priority Attention Ward:
                        </span>
                        <div className="font-bold text-slate-800">
                          {zs.topWard.ward_name} ({zs.topWard.ward_id})
                        </div>
                      </div>
                      <span className="font-mono text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                        {zs.topWard.risk_level}
                      </span>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      handleZoneChange(zs.zone);
                      setViewMode('feed');
                    }}
                    className="w-full py-2 rounded-xl text-xs font-bold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 transition text-center shadow-2xs"
                  >
                    View Zone Recommendations →
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* VIEW MODE 2: ACTIONS FEED */}
      {viewMode === 'feed' && (
        <>
          {/* Summary KPI Bar */}
          <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {/* Total Actions Card */}
            <div
              onClick={() => setFilterPriority('ALL')}
              className={`rounded-2xl border p-5 shadow-2xs cursor-pointer transition ${
                filterPriority === 'ALL'
                  ? 'border-sky-400 bg-sky-50/70 ring-2 ring-sky-300'
                  : 'border-sky-200/90 bg-white/95 hover:border-sky-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 uppercase font-bold tracking-wider">
                  Total Actions
                </span>
                {filterPriority === 'ALL' && (
                  <span className="h-2 w-2 rounded-full bg-sky-600 animate-pulse" />
                )}
              </div>
              <div className="mt-1 text-2xl font-black text-slate-900 font-mono">
                {totalActionsCount}
              </div>
            </div>

            {/* High Priority Card */}
            <div
              onClick={() => setFilterPriority('HIGH')}
              className={`rounded-2xl border p-5 shadow-2xs cursor-pointer transition ${
                filterPriority === 'HIGH'
                  ? 'border-rose-400 bg-rose-100/60 ring-2 ring-rose-300'
                  : 'border-rose-200 bg-rose-50/50 hover:border-rose-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-rose-700 uppercase font-bold tracking-wider">
                  High Priority
                </span>
                {filterPriority === 'HIGH' && (
                  <span className="h-2 w-2 rounded-full bg-rose-600 animate-pulse" />
                )}
              </div>
              <div className="mt-1 text-2xl font-black text-rose-700 font-mono">
                {highPriorityCount}
              </div>
            </div>

            {/* Medium Priority Card */}
            <div
              onClick={() => setFilterPriority('MEDIUM')}
              className={`rounded-2xl border p-5 shadow-2xs cursor-pointer transition ${
                filterPriority === 'MEDIUM'
                  ? 'border-amber-400 bg-amber-100/60 ring-2 ring-amber-300'
                  : 'border-amber-200 bg-amber-50/50 hover:border-amber-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-amber-800 uppercase font-bold tracking-wider">
                  Medium Priority
                </span>
                {filterPriority === 'MEDIUM' && (
                  <span className="h-2 w-2 rounded-full bg-amber-600 animate-pulse" />
                )}
              </div>
              <div className="mt-1 text-2xl font-black text-amber-800 font-mono">
                {mediumPriorityCount}
              </div>
            </div>

            {/* Routine Operations Card */}
            <div
              onClick={() => setFilterPriority('LOW')}
              className={`rounded-2xl border p-5 shadow-2xs cursor-pointer transition ${
                filterPriority === 'LOW'
                  ? 'border-emerald-400 bg-emerald-100/60 ring-2 ring-emerald-300'
                  : 'border-emerald-200 bg-emerald-50/50 hover:border-emerald-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-emerald-700 uppercase font-bold tracking-wider">
                  Routine Operations
                </span>
                {filterPriority === 'LOW' && (
                  <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse" />
                )}
              </div>
              <div className="mt-1 text-2xl font-black text-emerald-700 font-mono">
                {lowPriorityCount}
              </div>
            </div>
          </section>

          {/* Single Actions Feed */}
          <section className="space-y-3">
            {displayActions.length > 0 ? (
              displayActions.map((rec, idx) => {
                const isHigh = rec.priority === 'HIGH';
                const isMed = rec.priority === 'MEDIUM';
                return (
                  <div
                    key={rec.id || idx}
                    className="rounded-2xl border border-sky-200/90 bg-white p-5 sm:p-6 shadow-xs hover:border-sky-300 hover:shadow-sm transition space-y-3.5"
                  >
                    {/* Header Row */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider border shadow-2xs ${
                            isHigh
                              ? 'bg-rose-50 text-rose-700 border-rose-300'
                              : isMed
                              ? 'bg-amber-50 text-amber-800 border-amber-300'
                              : 'bg-emerald-50 text-emerald-700 border-emerald-300'
                          }`}
                        >
                          {rec.priority} PRIORITY
                        </span>
                        <span className="font-mono text-xs font-bold text-slate-400 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                          {rec.id}
                        </span>
                      </div>

                      {rec.ward_id && (
                        <span className="rounded-lg bg-sky-50 px-2.5 py-1 text-xs font-mono font-bold text-sky-900 border border-sky-200 shadow-2xs">
                          {rec.ward_name} ({rec.zone})
                        </span>
                      )}
                    </div>

                    {/* Title & Description */}
                    <div className="space-y-1.5">
                      <h3 className="text-base font-black text-slate-900 tracking-tight">
                        {rec.type}
                      </h3>
                      <p className="text-sm text-slate-600 leading-relaxed font-medium">
                        {rec.description}
                      </p>
                    </div>

                    {/* Footer Row */}
                    <div className="pt-3.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-500">
                          Standard Operating Protocol · Automated Decision Support System
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-[11px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          Requires Human Signoff
                        </span>
                        <button
                          type="button"
                          className="rounded-xl bg-sky-600 hover:bg-sky-700 px-4 py-2 text-xs font-bold text-white shadow-xs transition"
                          onClick={() => navigate('/review')}
                        >
                          Review in Emergency Gate →
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="rounded-2xl border border-sky-200 bg-white p-8 text-center text-slate-500 font-medium">
                No recommendations match the selected priority filter for this ward/zone.
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
