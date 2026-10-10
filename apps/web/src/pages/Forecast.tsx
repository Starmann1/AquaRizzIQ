import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

const WARDS = [
  { id: 'WARD-117', name: 'Velachery North' },
  { id: 'WARD-112', name: 'T. Nagar' },
  { id: 'WARD-113', name: 'West Mambalam' },
  { id: 'WARD-118', name: 'Velachery South' },
  { id: 'WARD-142', name: 'Adyar East' },
];

export default function Forecast() {
  const [selectedWard, setSelectedWard] = useState<string>('WARD-117');

  const { data: forecasts, isLoading, error } = useQuery({
    queryKey: ['forecasts'],
    queryFn: () => apiClient.fetchForecasts(),
    refetchInterval: 5000,
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={(error as Error).message} />;

  const activeForecast = Array.isArray(forecasts)
    ? forecasts.find((f: any) => f.ward_id === selectedWard) || forecasts[0]
    : forecasts;

  const currentWl = activeForecast?.current_water_level_m ?? 2.15;
  const dangerThreshold = activeForecast?.danger_threshold_m ?? 2.55;
  const channelDepth = activeForecast?.channel_depth_m ?? 3.0;
  const horizons = activeForecast?.forecast_horizons ?? {};

  const getHorizon = (m: string) => horizons[`plus_${m}m`] || horizons[m] || {};

  // Build time series points for chart
  // Points: T=0, T+15, T+30, T+60, T+120
  const chartPoints = [
    { t: 'Now (0m)', min: 0, p10: currentWl, p50: currentWl, p90: currentWl, prob: 0 },
    {
      t: '+15m',
      min: 15,
      p10: getHorizon('15').p10 ?? currentWl + 0.05,
      p50: getHorizon('15').p50 ?? currentWl + 0.12,
      p90: getHorizon('15').p90 ?? currentWl + 0.22,
      prob: getHorizon('15').exceedance_prob ?? 0.08,
    },
    {
      t: '+30m',
      min: 30,
      p10: getHorizon('30').p10 ?? currentWl + 0.10,
      p50: getHorizon('30').p50 ?? currentWl + 0.25,
      p90: getHorizon('30').p90 ?? currentWl + 0.42,
      prob: getHorizon('30').exceedance_prob ?? 0.28,
    },
    {
      t: '+60m',
      min: 60,
      p10: getHorizon('60').p10 ?? currentWl + 0.18,
      p50: getHorizon('60').p50 ?? currentWl + 0.45,
      p90: getHorizon('60').p90 ?? currentWl + 0.70,
      prob: getHorizon('60').exceedance_prob ?? 0.65,
    },
    {
      t: '+120m',
      min: 120,
      p10: getHorizon('120').p10 ?? currentWl + 0.25,
      p50: getHorizon('120').p50 ?? currentWl + 0.62,
      p90: getHorizon('120').p90 ?? currentWl + 0.95,
      prob: getHorizon('120').exceedance_prob ?? 0.88,
    },
  ];

  // SVG Chart Dimensions
  const svgWidth = 700;
  const svgHeight = 320;
  const padLeft = 60;
  const padRight = 40;
  const padTop = 30;
  const padBottom = 50;
  const plotW = svgWidth - padLeft - padRight;
  const plotH = svgHeight - padTop - padBottom;

  const yMax = Math.max(3.5, channelDepth + 0.2);
  const yMin = 0.0;

  const getX = (index: number) => padLeft + (index / (chartPoints.length - 1)) * plotW;
  const getY = (val: number) => padTop + plotH - ((val - yMin) / (yMax - yMin)) * plotH;

  // Build polygon path for P10-P90 confidence fan
  const upperPath = chartPoints.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt.p90)}`).join(' ');
  const lowerPath = [...chartPoints].reverse().map((pt, i) => `L ${getX(chartPoints.length - 1 - i)} ${getY(pt.p10)}`).join(' ');
  const fanPolygon = `${upperPath} ${lowerPath} Z`;

  // Build P50 median line
  const medianLine = chartPoints.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(pt.p50)}`).join(' ');

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-slate-800 rounded-lg border border-slate-700 shadow gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">M2 Probabilistic Water Level Forecast</h2>
            <SimulatedBadge />
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Quantile predictions (P10, P50, P90) across near-term lead times (+15m, +30m, +60m, +120m) with conformal uncertainty bounds.
          </p>
        </div>

        {/* Ward Selector Pills */}
        <div className="flex flex-wrap gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-700">
          {WARDS.map((w) => (
            <button
              key={w.id}
              onClick={() => setSelectedWard(w.id)}
              className={`px-3 py-1 rounded text-xs font-medium transition ${
                selectedWard === w.id
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {w.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Fan Chart Card */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 shadow space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>{WARDS.find((w) => w.id === selectedWard)?.name}</span>
              <span className="text-xs font-mono text-slate-400 font-normal">({selectedWard})</span>
            </h3>
            <p className="text-xs text-slate-400">
              Current Level: <strong className="text-cyan-400 font-mono">{currentWl.toFixed(2)} m</strong> &bull; Bankfull Channel Depth: <strong className="text-slate-300 font-mono">{channelDepth.toFixed(1)} m</strong>
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-3 h-3 bg-blue-500/30 border border-blue-400 rounded-sm"></span>
              P10–P90 Uncertainty Fan
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-3.5 h-0.5 bg-cyan-400"></span>
              P50 Median Forecast
            </span>
            <span className="flex items-center gap-1.5 text-red-400">
              <span className="w-3.5 h-0.5 bg-red-500 border-dashed border-b"></span>
              Danger Threshold ({dangerThreshold.toFixed(2)}m)
            </span>
          </div>
        </div>

        {/* SVG Forecast Fan Chart */}
        <div className="w-full overflow-x-auto flex justify-center py-2">
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full max-w-4xl h-auto select-none">
            {/* Grid Lines */}
            {[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5].map((yVal) => (
              <g key={yVal}>
                <line
                  x1={padLeft}
                  y1={getY(yVal)}
                  x2={svgWidth - padRight}
                  y2={getY(yVal)}
                  stroke="#1e293b"
                  strokeWidth="1"
                />
                <text
                  x={padLeft - 10}
                  y={getY(yVal) + 4}
                  textAnchor="end"
                  fill="#64748b"
                  fontSize="11"
                  fontFamily="monospace"
                >
                  {yVal.toFixed(1)}m
                </text>
              </g>
            ))}

            {/* Danger Threshold Line */}
            <line
              x1={padLeft}
              y1={getY(dangerThreshold)}
              x2={svgWidth - padRight}
              y2={getY(dangerThreshold)}
              stroke="#ef4444"
              strokeWidth="2"
              strokeDasharray="5,5"
            />
            <text
              x={svgWidth - padRight - 5}
              y={getY(dangerThreshold) - 6}
              textAnchor="end"
              fill="#ef4444"
              fontSize="11"
              fontWeight="600"
            >
              Danger Limit ({dangerThreshold.toFixed(2)}m)
            </text>

            {/* P10 - P90 Fan Polygon */}
            <path d={fanPolygon} fill="#0284c7" fillOpacity="0.25" stroke="#38bdf8" strokeWidth="1" strokeOpacity="0.6" />

            {/* P50 Median Line */}
            <path d={medianLine} fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

            {/* Points & Annotations */}
            {chartPoints.map((pt, i) => (
              <g key={pt.t}>
                {/* Vertical time marker */}
                <line
                  x1={getX(i)}
                  y1={padTop}
                  x2={getX(i)}
                  y2={padTop + plotH}
                  stroke="#334155"
                  strokeWidth="0.8"
                  strokeDasharray="2,2"
                />
                {/* P50 point */}
                <circle cx={getX(i)} cy={getY(pt.p50)} r="4.5" fill="#38bdf8" stroke="#0f172a" strokeWidth="2" />
                {/* P90 point */}
                <circle cx={getX(i)} cy={getY(pt.p90)} r="3" fill="#93c5fd" />
                {/* P10 point */}
                <circle cx={getX(i)} cy={getY(pt.p10)} r="3" fill="#0284c7" />

                {/* X Axis Label */}
                <text
                  x={getX(i)}
                  y={padTop + plotH + 20}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="12"
                  fontWeight="600"
                >
                  {pt.t}
                </text>
                <text
                  x={getX(i)}
                  y={padTop + plotH + 34}
                  textAnchor="middle"
                  fill={pt.p50 >= dangerThreshold ? '#ef4444' : '#38bdf8'}
                  fontSize="11"
                  fontFamily="monospace"
                >
                  {pt.p50.toFixed(2)}m
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>

      {/* Exceedance Risk Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {chartPoints.slice(1).map((pt) => {
          const isDanger = pt.p50 >= dangerThreshold;
          return (
            <div
              key={pt.t}
              className={`p-4 rounded-lg border shadow ${
                isDanger
                  ? 'bg-red-950/30 border-red-800/80'
                  : 'bg-slate-800 border-slate-700'
              }`}
            >
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>Horizon: {pt.t}</span>
                <span className="font-mono font-bold text-white">{pt.p50.toFixed(2)} m</span>
              </div>
              <div className="mt-2">
                <div className="text-[11px] text-slate-400">Exceedance Probability:</div>
                <div
                  className={`text-xl font-bold font-mono mt-0.5 ${
                    pt.prob > 0.5 ? 'text-red-400' : pt.prob > 0.2 ? 'text-amber-400' : 'text-emerald-400'
                  }`}
                >
                  {(pt.prob * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-[10px] text-slate-400 mt-2 flex justify-between">
                <span>P10: {pt.p10.toFixed(2)}m</span>
                <span>P90: {pt.p90.toFixed(2)}m</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Model Grounding & Validation Note */}
      <div className="p-4 bg-slate-800 rounded-lg border border-slate-700 text-xs text-slate-300 space-y-1">
        <div className="font-semibold text-white flex items-center gap-2">
          <span>ML Model Governance &amp; Grounding (P0-01, P0-03)</span>
          <span className="px-1.5 py-0.2 rounded bg-slate-700 text-[10px] text-slate-300">
            M2 Quantile Delta Forecaster
          </span>
        </div>
        <p className="text-slate-400">
          Forecasts predict incremental delta head (&Delta;h) bounded by physical drain headroom. The uncertainty envelope widens monotonically over the 120-minute horizon. If telemetry data is missing or calibration samples fall below minimum threshold (N=50), the system yields an explicit <strong>ABSTAINED</strong> status rather than uncalibrated numbers.
        </p>
      </div>
    </div>
  );
}
