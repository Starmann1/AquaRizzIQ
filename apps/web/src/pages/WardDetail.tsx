import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function WardDetail() {
  const { wardId: paramWardId } = useParams<{ wardId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const wardId = paramWardId || 'WARD-117';

  const [rainfall1h, setRainfall1h] = useState<number>(65);
  const [rainfall3h, setRainfall3h] = useState<number>(105);
  const [waterLevel, setWaterLevel] = useState<number>(2.15);
  const [rateOfRise, setRateOfRise] = useState<number>(0.04);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const { data: risk, isLoading: riskLoading, error: riskError } = useQuery({
    queryKey: ['wardRisk', wardId],
    queryFn: () => apiClient.fetchWardRisk(wardId),
    refetchInterval: 5000,
  });

  const { data: zoneFeature } = useQuery({
    queryKey: ['zone', wardId],
    queryFn: () => apiClient.fetchZoneById(wardId),
  });

  const { data: forecast } = useQuery({
    queryKey: ['forecast', wardId],
    queryFn: () => apiClient.fetchForecasts(wardId),
  });

  const assessMutation = useMutation({
    mutationFn: (customFeatures: any) =>
      apiClient.triggerAssessment(wardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardRisk', wardId] });
      queryClient.invalidateQueries({ queryKey: ['risks'] });
      setIsSubmitting(false);
    },
    onError: () => {
      setIsSubmitting(false);
    },
  });

  const handleTriggerAssessment = () => {
    setIsSubmitting(true);
    assessMutation.mutate({
      rainfall_1h: rainfall1h,
      rainfall_3h: rainfall3h,
      water_level_m: waterLevel,
      rate_of_rise: rateOfRise,
    });
  };

  if (riskLoading) return <LoadingSpinner />;
  if (riskError) return <ErrorDisplay message={(riskError as Error).message} />;

  const props = zoneFeature?.properties || {};

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center p-5 bg-slate-800 rounded-lg border border-slate-700 shadow gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700">
              {wardId}
            </span>
            <h2 className="text-2xl font-bold text-white">
              {risk?.ward_name || props.name || wardId}
            </h2>
            <RiskBadge level={risk?.risk_level || 'LOW'} />
            <SimulatedBadge />
          </div>
          <p className="text-slate-400 text-sm mt-1">
            {risk?.zone || props.zone || 'Greater Chennai Corporation'} &bull; Analytical Grid Cell Catchment
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/map')}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-xs font-medium transition"
          >
            &larr; Back to Map
          </button>
          <button
            onClick={() => navigate('/rca')}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition"
          >
            Shapley RCA &rarr;
          </button>
        </div>
      </div>

      {/* Main Grid: Telemetry Meters & Static Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Water Level */}
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <div className="text-xs text-slate-400">Ultrasonic Channel Water Level</div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {waterLevel.toFixed(2)} m
          </div>
          <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden mt-3">
            <div
              className={`h-full ${waterLevel > 2.2 ? 'bg-red-500' : waterLevel > 1.8 ? 'bg-amber-500' : 'bg-cyan-500'}`}
              style={{ width: `${Math.min(100, (waterLevel / 3.0) * 100)}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>0.0 m</span>
            <span>Warning: 2.0 m</span>
            <span>Channel: 3.0 m</span>
          </div>
        </div>

        {/* Metric 2: 1h Rainfall */}
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <div className="text-xs text-slate-400">Rainfall Accumulation (1 Hour)</div>
          <div className="text-2xl font-bold font-mono text-blue-400 mt-1">
            {rainfall1h.toFixed(1)} mm
          </div>
          <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-blue-500"
              style={{ width: `${Math.min(100, (rainfall1h / 100) * 100)}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>0 mm</span>
            <span>Heavy &gt; 50 mm</span>
            <span>100 mm</span>
          </div>
        </div>

        {/* Metric 3: 3h Rainfall */}
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <div className="text-xs text-slate-400">Rainfall Accumulation (3 Hours)</div>
          <div className="text-2xl font-bold font-mono text-indigo-400 mt-1">
            {rainfall3h.toFixed(1)} mm
          </div>
          <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-indigo-500"
              style={{ width: `${Math.min(100, (rainfall3h / 150) * 100)}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>0 mm</span>
            <span>Extreme &gt; 100 mm</span>
            <span>150 mm</span>
          </div>
        </div>

        {/* Metric 4: Rate of Rise */}
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <div className="text-xs text-slate-400">Hydraulic Rate of Rise</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            +{rateOfRise.toFixed(3)} m/min
          </div>
          <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden mt-3">
            <div
              className="h-full bg-amber-500"
              style={{ width: `${Math.min(100, (rateOfRise / 0.1) * 100)}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>Steady</span>
            <span>Threshold: 0.05 m/min</span>
            <span>Flash</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Static Features vs Simulator & Assessment Trigger */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ward Geospatial & Physical Terrain Profile */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-5 shadow space-y-4">
          <h3 className="text-base font-semibold text-white border-b border-slate-700 pb-2">
            Static Terrain &amp; Geospatial Features (EPSG:32644)
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <div className="text-xs text-slate-400">Mean Elevation (DEM)</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {props.elevation_mean ? `${props.elevation_mean} m` : '5.2 m MSL'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <div className="text-xs text-slate-400">Surface Slope</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {props.slope_mean ? `${props.slope_mean}°` : '0.65°'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <div className="text-xs text-slate-400">Impervious Surface Fraction</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {props.imperviousness_mean ? `${(props.imperviousness_mean * 100).toFixed(0)}%` : '74%'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <div className="text-xs text-slate-400">Static Susceptibility Prior (M1)</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {props.susceptibility_mean ? `${props.susceptibility_mean.toFixed(2)}` : '0.84'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <div className="text-xs text-slate-400">Population Count</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {props.population?.toLocaleString() || '74,200'}
              </div>
            </div>
            <div className="p-3 bg-slate-900/60 rounded border border-slate-700/60">
              <div className="text-xs text-slate-400">Area Coverage</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">
                {props.area_sq_km ? `${props.area_sq_km} sq km` : '4.50 sq km'}
              </div>
            </div>
          </div>

          <div className="p-3 bg-blue-950/40 rounded border border-blue-800/40 text-xs text-blue-200">
            <strong>Hydrology Note:</strong> High imperviousness (&gt;70%) combined with low surface slope leads to rapid urban surface runoff accumulation with low soil infiltration retention.
          </div>
        </div>

        {/* Dynamic Parameter Tuning & Live Assessment Trigger */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-5 shadow space-y-4">
          <div className="flex justify-between items-center border-b border-slate-700 pb-2">
            <h3 className="text-base font-semibold text-white">
              Simulate Telemetry &amp; Trigger LangGraph Agent Run
            </h3>
            <span className="text-xs text-amber-400">Live Feedback</span>
          </div>

          <p className="text-xs text-slate-400">
            Adjust telemetry inputs below and trigger the 6-agent LangGraph orchestrator to compute hazard, matrix-gated risk, and generate explainable decisions.
          </p>

          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>1h Rainfall Intensity: {rainfall1h} mm/h</span>
              </div>
              <input
                type="range"
                min="0"
                max="120"
                step="5"
                value={rainfall1h}
                onChange={(e) => setRainfall1h(parseFloat(e.target.value))}
                className="w-full accent-blue-500 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>3h Cumulative Rainfall: {rainfall3h} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="200"
                step="5"
                value={rainfall3h}
                onChange={(e) => setRainfall3h(parseFloat(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>Channel Water Depth: {waterLevel.toFixed(2)} m</span>
              </div>
              <input
                type="range"
                min="0.2"
                max="3.5"
                step="0.05"
                value={waterLevel}
                onChange={(e) => setWaterLevel(parseFloat(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>Rate of Rise: {rateOfRise.toFixed(3)} m/min</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="0.10"
                step="0.005"
                value={rateOfRise}
                onChange={(e) => setRateOfRise(parseFloat(e.target.value))}
                className="w-full accent-amber-500 cursor-pointer"
              />
            </div>
          </div>

          <button
            onClick={handleTriggerAssessment}
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded font-semibold text-sm shadow transition flex items-center justify-center gap-2 mt-4"
          >
            {isSubmitting ? (
              <>
                <span className="animate-spin">&bull;</span> Running 6-Agent LangGraph Pipeline...
              </>
            ) : (
              'Run Multi-Agent Risk Assessment'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
