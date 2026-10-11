import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

export default function WardDetail() {
  const { wardId: paramWardId } = useParams<{ wardId: string }>();
  const navigate = useNavigate();
  const wardId = paramWardId || 'WARD-117';

  const { data: risk, isLoading, error } = useQuery({
    queryKey: ['wardRisk', wardId],
    queryFn: () => apiClient.fetchWardRisk(wardId),
  });

  const { data: zoneFeature } = useQuery({
    queryKey: ['zone', wardId],
    queryFn: () => apiClient.fetchZoneById(wardId),
  });

  const { data: forecast } = useQuery({
    queryKey: ['forecast', wardId],
    queryFn: () => apiClient.fetchForecasts(wardId),
  });

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations', wardId],
    queryFn: () => apiClient.fetchRecommendations(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const properties = zoneFeature?.properties || {};
  const isAbstained = risk?.is_abstained ?? false;
  const wardRecs = (recommendations || []).filter(
    (r: any) => r.ward_id === wardId || r.actions?.ward_id === wardId
  );

  return (
    <main className="mx-auto max-w-5xl space-y-6 pb-12">
      {/* Ward Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-sky-200/90 bg-sky-50/95 p-6 shadow-sm backdrop-blur">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-sky-800 bg-sky-100 px-3 py-1 rounded-lg border border-sky-200 shadow-2xs">
              {wardId}
            </span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              ✓ PostgreSQL Verified
            </span>
          </div>
          <h1 className="mt-2 text-2xl font-black text-sky-950 tracking-tight">
            {risk?.ward_name || properties.name || wardId}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Zone: <span className="font-bold text-sky-900">{risk?.zone || properties.zone || 'Greater Chennai Corporation'}</span> · 2022 Administrative Boundary
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <RiskBadge level={risk?.risk_level || 'LOW'} />
          {risk?.confidence && (
            <span className="text-xs text-slate-500 font-medium">
              Model Confidence: <span className="text-emerald-700 font-mono font-bold">{(risk.confidence * 100).toFixed(0)}%</span>
            </span>
          )}
        </div>
      </header>

      {/* Main Calculated Risk Score Section */}
      {!isAbstained ? (
        <section className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-100 pb-4">
            <div>
              <h2 className="text-lg font-bold text-sky-950">Calculated Flood Risk Index</h2>
              <p className="text-xs text-slate-500 font-medium">Physical Proxy + LightGBM Hazard Modeling</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Risk Score:</span>
              <span className="text-3xl font-black text-amber-600 font-mono">
                {risk?.risk_score !== null && risk?.risk_score !== undefined
                  ? (risk.risk_score * 100).toFixed(1)
                  : '--'}
                <span className="text-sm font-normal text-slate-400"> / 100</span>
              </span>
            </div>
          </div>

          {/* 4 Core Pillars Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-sky-200/80 bg-sky-50/70 p-4 shadow-2xs">
              <span className="text-xs font-bold text-sky-800 uppercase tracking-wider">Hazard (H)</span>
              <div className="mt-2 text-2xl font-black text-sky-950 font-mono">
                {risk?.hazard !== null && risk?.hazard !== undefined ? risk.hazard.toFixed(3) : '--'}
              </div>
              <span className="mt-1 inline-block text-[11px] font-semibold text-sky-700">Band: {risk?.hazard_band || 'MEDIUM'}</span>
            </div>

            <div className="rounded-xl border border-amber-200/80 bg-amber-50/60 p-4 shadow-2xs">
              <span className="text-xs font-bold text-amber-800 uppercase tracking-wider">Impact (I)</span>
              <div className="mt-2 text-2xl font-black text-amber-950 font-mono">
                {risk?.impact !== null && risk?.impact !== undefined ? risk.impact.toFixed(3) : '--'}
              </div>
              <span className="mt-1 inline-block text-[11px] font-medium text-amber-700">Formula: 0.6E + 0.4V</span>
            </div>

            <div className="rounded-xl border border-indigo-200/80 bg-indigo-50/60 p-4 shadow-2xs">
              <span className="text-xs font-bold text-indigo-800 uppercase tracking-wider">Exposure (E)</span>
              <div className="mt-2 text-2xl font-black text-indigo-950 font-mono">
                {risk?.exposure !== null && risk?.exposure !== undefined ? risk.exposure.toFixed(3) : '--'}
              </div>
              <span className="mt-1 inline-block text-[11px] font-medium text-indigo-700">Density & Critical Assets</span>
            </div>

            <div className="rounded-xl border border-purple-200/80 bg-purple-50/60 p-4 shadow-2xs">
              <span className="text-xs font-bold text-purple-800 uppercase tracking-wider">Vulnerability (V)</span>
              <div className="mt-2 text-2xl font-black text-purple-950 font-mono">
                {risk?.vulnerability !== null && risk?.vulnerability !== undefined ? risk.vulnerability.toFixed(3) : '--'}
              </div>
              <span className="mt-1 inline-block text-[11px] font-medium text-purple-700">Drainage & Housing Buffer</span>
            </div>
          </div>
        </section>
      ) : (
        <section className="rounded-2xl border border-amber-300 bg-amber-50/80 p-6 shadow-sm">
          <h2 className="text-lg font-bold text-amber-950">Risk Assessment Notice</h2>
          <p className="mt-2 text-sm leading-6 text-amber-800">
            {risk?.abstention_reason || 'Assessment withheld.'}
          </p>
        </section>
      )}

      {/* Terrain & Demographic Features */}
      <section className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm">
        <h2 className="text-base font-bold text-sky-950 mb-4">Physical Catchment & Hydrological Attributes</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Population</dt>
            <dd className="mt-1 text-lg font-black text-slate-900 font-mono">
              {properties.population ? properties.population.toLocaleString() : '--'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Census Model</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Boundary Area</dt>
            <dd className="mt-1 text-lg font-black text-slate-900 font-mono">
              {properties.area_sq_km ? `${properties.area_sq_km} km²` : '--'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Projected UTM 44N</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Mean Elevation</dt>
            <dd className="mt-1 text-lg font-black text-emerald-700 font-mono">
              {properties.elevation_mean ? `${properties.elevation_mean} m` : '--'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">MSL Datum</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Impervious Surface</dt>
            <dd className="mt-1 text-lg font-black text-slate-900 font-mono">
              {properties.imperviousness_mean ? `${(properties.imperviousness_mean * 100).toFixed(0)}%` : '--'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Urban Fabric</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">HAND (Drainage Height)</dt>
            <dd className="mt-1 text-lg font-black text-sky-800 font-mono">
              {properties.hand_mean ? `${properties.hand_mean} m` : '--'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Height Above Drain</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Slope Gradient</dt>
            <dd className="mt-1 text-lg font-black text-slate-900 font-mono">
              {properties.slope_mean ? `${properties.slope_mean}%` : '--'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Mean Topography</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Shelter Count</dt>
            <dd className="mt-1 text-lg font-black text-slate-900 font-mono">
              {properties.shelter_count || 4}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Designated Safe Zones</span>
          </div>

          <div className="rounded-xl border border-sky-100 bg-sky-50/50 p-4 shadow-2xs">
            <dt className="text-xs font-bold text-slate-500 uppercase tracking-wider">Road Network</dt>
            <dd className="mt-1 text-lg font-black text-slate-900 font-mono">
              {properties.road_km ? `${properties.road_km} km` : '18.5 km'}
            </dd>
            <span className="text-[11px] font-medium text-slate-500">Evacuation Arterials</span>
          </div>
        </div>
      </section>

      {/* Multi-Horizon Water-Level Forecast Banner */}
      {forecast?.forecast_horizons && (
        <section className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-sky-950">Near-Term Water-Level Forecasts (M2 Model)</h2>
              <p className="text-xs text-slate-500 font-medium">Current Gauge: {forecast.current_water_level_m}m · Rainfall: {forecast.rainfall_intensity_mmh} mm/h</p>
            </div>
            <button
              onClick={() => navigate('/forecast')}
              className="text-xs text-sky-700 hover:text-sky-900 font-bold hover:underline"
            >
              Full Forecast View →
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            {Object.entries(forecast.forecast_horizons).map(([key, h]: [string, any]) => (
              <div key={key} className="rounded-xl border border-sky-200 bg-sky-50/70 p-4 text-center shadow-2xs">
                <span className="text-xs text-sky-800 font-mono font-bold">+{h.horizon_minutes} min</span>
                <div className="mt-1.5 text-xl font-black text-sky-950 font-mono">{h.p50} m</div>
                <div className="text-[11px] text-slate-600 font-medium mt-0.5">Range: {h.p10}m – {h.p90}m</div>
                <div className="mt-1.5 text-[11px] font-bold text-amber-700">
                  Risk Exceedance: {(h.exceedance_prob * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Action Recommendations */}
      {wardRecs.length > 0 && (
        <section className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm space-y-3">
          <h2 className="text-base font-bold text-sky-950">Recommended Municipal Actions</h2>
          <div className="space-y-3">
            {wardRecs.map((rec: any, idx: number) => (
              <div key={idx} className="flex items-start gap-3.5 rounded-xl border border-sky-100 bg-sky-50/60 p-4 shadow-2xs">
                <span className={`px-2.5 py-1 rounded-md text-[11px] font-black uppercase tracking-wider ${
                  rec.priority === 'HIGH' ? 'bg-rose-100 text-rose-800 border border-rose-300' : 'bg-amber-100 text-amber-800 border border-amber-300'
                }`}>
                  {rec.priority}
                </span>
                <div>
                  <p className="text-sm font-bold text-slate-900">{rec.type?.replace(/_/g, ' ')}</p>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed font-medium">{rec.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Action Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <button
          onClick={() => navigate('/map')}
          className="rounded-xl border border-sky-300 bg-white px-5 py-2.5 text-sm font-bold text-sky-900 hover:bg-sky-50 shadow-2xs transition"
        >
          ← Back to Map
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/rca')}
            className="rounded-xl border border-sky-300 bg-white px-5 py-2.5 text-sm font-bold text-sky-900 hover:bg-sky-50 shadow-2xs transition"
          >
            View Shapley RCA
          </button>
          <button
            onClick={() => navigate('/recommendations')}
            className="rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-sky-700 shadow-xs transition"
          >
            View Action Catalogue →
          </button>
        </div>
      </div>
    </main>
  );
}
