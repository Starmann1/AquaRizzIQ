import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient, WardRisk } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

// SVG map path geometries for GCC wards (normalized projection for Chennai region)
// Coordinates aligned with longitude ~80.20 to 80.27 and latitude ~12.95 to 13.06
const WARD_GEOMETRIES: Record<string, { path: string; center: [number, number]; labelPos: [number, number] }> = {
  'WARD-112': {
    // T. Nagar
    path: 'M 280,110 L 490,110 L 520,240 L 350,280 L 250,190 Z',
    center: [380, 180],
    labelPos: [380, 185],
  },
  'WARD-113': {
    // West Mambalam
    path: 'M 190,150 L 280,150 L 290,280 L 160,290 Z',
    center: [230, 220],
    labelPos: [225, 225],
  },
  'WARD-117': {
    // Velachery North
    path: 'M 120,410 L 360,410 L 390,580 L 160,600 Z',
    center: [260, 500],
    labelPos: [260, 505],
  },
  'WARD-118': {
    // Velachery South
    path: 'M 90,580 L 350,580 L 360,750 L 120,750 Z',
    center: [230, 660],
    labelPos: [230, 665],
  },
  'WARD-142': {
    // Adyar East
    path: 'M 550,380 L 720,380 L 690,550 L 520,540 Z',
    center: [620, 460],
    labelPos: [620, 465],
  },
};

export default function FloodRiskMap() {
  const navigate = useNavigate();
  const [selectedWardId, setSelectedWardId] = useState<string>('WARD-117');
  const [hoveredWardId, setHoveredWardId] = useState<string | null>(null);
  const [filterText, setFilterText] = useState<string>('');

  const { data: risks, isLoading, error } = useQuery<WardRisk[]>({
    queryKey: ['risks'],
    queryFn: apiClient.fetchRisk,
    refetchInterval: 5000,
  });

  const { data: zones } = useQuery({
    queryKey: ['zones'],
    queryFn: apiClient.fetchZones,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const riskMap: Record<string, WardRisk> = {};
  (risks || []).forEach((r) => {
    riskMap[r.ward_id] = r;
  });

  const getRiskColor = (level?: string) => {
    switch (level) {
      case 'VERY_HIGH':
        return '#ef4444';
      case 'HIGH':
        return '#f97316';
      case 'MEDIUM':
        return '#eab308';
      case 'LOW':
        return '#22c55e';
      default:
        return '#64748b';
    }
  };

  const selectedRisk = riskMap[selectedWardId];
  const selectedFeature = zones?.features?.find(
    (f: any) => f.properties.ward_id === selectedWardId
  );

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-slate-800 rounded-lg border border-slate-700 shadow gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">GCC Interactive Flood Risk Map</h2>
            <SimulatedBadge />
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Real-time urban flood risk surface across Greater Chennai Corporation analytical wards (EPSG:32644 analytical grid).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search ward or zone..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Main Grid: Map + Side Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Viewport (2 cols on lg) */}
        <div className="lg:col-span-2 bg-slate-900 rounded-lg border border-slate-800 p-4 shadow flex flex-col items-center justify-between relative min-h-[550px]">
          {/* Map Top Status Bar */}
          <div className="w-full flex justify-between items-center text-xs text-slate-400 mb-2 px-2">
            <span>Projection: WGS84 &rarr; UTM Zone 44N (EPSG:32644)</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Low
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span> Med
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span> High
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> Very High
              </span>
            </div>
          </div>

          {/* SVG Map Container */}
          <div className="w-full flex-1 flex items-center justify-center relative overflow-hidden bg-slate-950/70 rounded border border-slate-800/80 p-2">
            <svg
              viewBox="50 50 720 750"
              className="w-full h-auto max-h-[500px] select-none filter drop-shadow-md"
            >
              {/* Grid backdrop */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.8" />
                </pattern>
              </defs>
              <rect x="50" y="50" width="720" height="750" fill="url(#grid)" opacity="0.6" />

              {/* Waterways / Adyar River Channel & Buckingham Canal */}
              <path
                d="M 80,480 Q 280,490 520,430 T 730,410"
                fill="none"
                stroke="#0284c7"
                strokeWidth="7"
                strokeOpacity="0.45"
                strokeLinecap="round"
              />
              <text x="540" y="415" fill="#38bdf8" fontSize="11" opacity="0.7" fontStyle="italic">
                Adyar River Riverway
              </text>

              {/* Monitored Ward Polygons */}
              {Object.entries(WARD_GEOMETRIES).map(([wardId, geom]) => {
                const r = riskMap[wardId];
                const isSelected = selectedWardId === wardId;
                const isHovered = hoveredWardId === wardId;
                const fillColor = getRiskColor(r?.risk_level);

                return (
                  <g
                    key={wardId}
                    onClick={() => setSelectedWardId(wardId)}
                    onMouseEnter={() => setHoveredWardId(wardId)}
                    onMouseLeave={() => setHoveredWardId(null)}
                    className="cursor-pointer transition-all duration-200"
                  >
                    <path
                      d={geom.path}
                      fill={fillColor}
                      fillOpacity={isSelected ? 0.85 : isHovered ? 0.75 : 0.55}
                      stroke={isSelected ? '#ffffff' : isHovered ? '#cbd5e1' : '#334155'}
                      strokeWidth={isSelected ? 3.5 : isHovered ? 2.5 : 1.5}
                      className="transition-all duration-150"
                    />
                    <text
                      x={geom.labelPos[0]}
                      y={geom.labelPos[1]}
                      textAnchor="middle"
                      fill="#f8fafc"
                      fontSize="13"
                      fontWeight={isSelected ? '700' : '600'}
                      className="pointer-events-none drop-shadow"
                    >
                      {r?.ward_name || wardId}
                    </text>
                    <text
                      x={geom.labelPos[0]}
                      y={geom.labelPos[1] + 16}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize="10"
                      className="pointer-events-none drop-shadow"
                    >
                      {r?.risk_level || 'MONITORED'}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Quick hover indicator card */}
            {hoveredWardId && riskMap[hoveredWardId] && (
              <div className="absolute top-4 left-4 bg-slate-900/95 border border-slate-700 px-3 py-2 rounded text-xs shadow-xl pointer-events-none backdrop-blur">
                <div className="font-semibold text-white">{riskMap[hoveredWardId]?.ward_name}</div>
                <div className="text-slate-400">Score: {riskMap[hoveredWardId]?.risk_score.toFixed(3)}</div>
                <div className="text-slate-400">Hazard: {riskMap[hoveredWardId]?.hazard.toFixed(3)}</div>
              </div>
            )}
          </div>

          <div className="w-full flex justify-between items-center text-xs text-slate-500 mt-2 px-2">
            <span>Click any ward to inspect analytical breakdown</span>
            <span>Spatial Engine: PostGIS + Shapely 2.0</span>
          </div>
        </div>

        {/* Selected Ward Detail Panel */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-5 shadow flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs uppercase font-mono tracking-wider text-blue-400">
                  {selectedWardId}
                </span>
                <h3 className="text-xl font-bold text-white mt-0.5">
                  {selectedRisk?.ward_name || 'Selected Ward'}
                </h3>
                <p className="text-xs text-slate-400">{selectedRisk?.zone}</p>
              </div>
              <RiskBadge level={selectedRisk?.risk_level || 'UNKNOWN'} />
            </div>

            {/* Metric Overview Gauges */}
            <div className="mt-5 space-y-3">
              <div>
                <div className="flex justify-between text-xs text-slate-300 mb-1">
                  <span>Calculated Risk Score</span>
                  <span className="font-mono font-semibold">
                    {selectedRisk ? (selectedRisk.risk_score * 100).toFixed(1) : '0.0'}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(selectedRisk?.risk_score || 0) * 100}%`,
                      backgroundColor: getRiskColor(selectedRisk?.risk_level),
                    }}
                  ></div>
                </div>
              </div>

              {/* Component breakdown */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-700/60">
                  <div className="text-[11px] text-slate-400">Hazard (H)</div>
                  <div className="text-lg font-bold text-white font-mono mt-0.5">
                    {selectedRisk?.hazard.toFixed(3) || '0.000'}
                  </div>
                  <div className="text-[10px] text-slate-400">Band: {selectedRisk?.hazard_band}</div>
                </div>

                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-700/60">
                  <div className="text-[11px] text-slate-400">Impact (E x V)</div>
                  <div className="text-lg font-bold text-white font-mono mt-0.5">
                    {selectedRisk?.impact.toFixed(3) || '0.000'}
                  </div>
                  <div className="text-[10px] text-slate-400">Matrix-Gated</div>
                </div>

                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-700/60">
                  <div className="text-[11px] text-slate-400">Exposure (E)</div>
                  <div className="text-base font-semibold text-slate-200 font-mono mt-0.5">
                    {selectedRisk?.exposure.toFixed(3) || '0.000'}
                  </div>
                </div>

                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-700/60">
                  <div className="text-[11px] text-slate-400">Vulnerability (V)</div>
                  <div className="text-base font-semibold text-slate-200 font-mono mt-0.5">
                    {selectedRisk?.vulnerability.toFixed(3) || '0.000'}
                  </div>
                </div>
              </div>

              {/* Ward Geo & Demographic Info */}
              {selectedFeature?.properties && (
                <div className="mt-4 pt-4 border-t border-slate-700/70 text-xs space-y-1.5 text-slate-300">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Area:</span>
                    <span>{selectedFeature.properties.area_sq_km} sq km</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Population:</span>
                    <span>{selectedFeature.properties.population?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Mean Elevation:</span>
                    <span>{selectedFeature.properties.elevation_mean} m MSL</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Imperviousness:</span>
                    <span>{((selectedFeature.properties.imperviousness_mean || 0) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              )}

              {/* Safety floor warning if triggered */}
              {selectedRisk?.safety_floor_triggered && (
                <div className="mt-2 p-2 bg-red-950/40 border border-red-700/60 rounded text-xs text-red-300">
                  <strong>Safety Floor Activated:</strong> {selectedRisk.safety_floor_triggered}
                </div>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="mt-6 space-y-2 pt-4 border-t border-slate-700">
            <button
              onClick={() => navigate(`/wards/${selectedWardId}`)}
              className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold shadow transition"
            >
              Open Ward Telemetry &amp; Gauges &rarr;
            </button>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => navigate(`/rca`)}
                className="py-1.5 px-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-xs font-medium transition"
              >
                View Shapley RCA
              </button>
              <button
                onClick={() => navigate(`/routing`)}
                className="py-1.5 px-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-xs font-medium transition"
              >
                Plan Evacuation
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
