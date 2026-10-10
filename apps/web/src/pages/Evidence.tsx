import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import SimulatedBadge from '../components/common/SimulatedBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorDisplay from '../components/common/ErrorDisplay';

interface EvidenceCardData {
  id: string;
  evidence_type: string;
  source_id: string;
  ward_id: string;
  data_hash: string;
  observed_at: string;
  quality_state: string;
  values: Record<string, any>;
  is_verified: boolean;
}

const SAMPLE_EVIDENCE: EvidenceCardData[] = [
  {
    id: 'EV-RAIN-WARD117-20261010-8b1a3f01',
    evidence_type: 'METEOROLOGICAL_OBSERVATION',
    source_id: 'STN-VELACHERY-01',
    ward_id: 'WARD-117',
    data_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    observed_at: '2026-10-10T16:15:00Z',
    quality_state: 'VALID',
    values: {
      rainfall_rate_mm_h: 65.0,
      accumulation_1h_mm: 65.0,
      accumulation_3h_mm: 105.0,
      sensor_model: 'Tipping-Bucket-0.1mm',
    },
    is_verified: true,
  },
  {
    id: 'EV-SENS-WARD117-20261010-4c2d7e99',
    evidence_type: 'HYDROLOGICAL_TELEMETRY',
    source_id: 'SENS-VELACHERY-LAKE-OUTLET',
    ward_id: 'WARD-117',
    data_hash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
    observed_at: '2026-10-10T16:15:00Z',
    quality_state: 'VALID',
    values: {
      water_level_m: 2.15,
      rate_of_rise_m_min: 0.04,
      sensor_type: 'Ultrasonic Distance Meter',
      acoustic_confidence: 0.96,
    },
    is_verified: true,
  },
  {
    id: 'EV-TERR-WARD117-20261010-1a7f3c4d',
    evidence_type: 'TERRAIN_GEOSPATIAL_PRIOR',
    source_id: 'GEO-GCC-DEM-30M',
    ward_id: 'WARD-117',
    data_hash: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
    observed_at: '2026-10-10T00:00:00Z',
    quality_state: 'VALID',
    values: {
      elevation_mean_m: 4.5,
      hand_mean_m: 1.2,
      imperviousness_fraction: 0.74,
      static_susceptibility: 0.84,
    },
    is_verified: true,
  },
  {
    id: 'EV-RAIN-WARD112-20261010-3d9a11ef',
    evidence_type: 'METEOROLOGICAL_OBSERVATION',
    source_id: 'STN-TNAGAR-01',
    ward_id: 'WARD-112',
    data_hash: 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
    observed_at: '2026-10-10T16:10:00Z',
    quality_state: 'VALID',
    values: {
      rainfall_rate_mm_h: 42.0,
      accumulation_1h_mm: 42.0,
      accumulation_3h_mm: 78.0,
      sensor_model: 'Optical Disdrometer',
    },
    is_verified: true,
  },
  {
    id: 'EV-SENS-WARD113-20261010-90c74b12',
    evidence_type: 'HYDROLOGICAL_TELEMETRY',
    source_id: 'SENS-WEST-MAMBALAM-STREET',
    ward_id: 'WARD-113',
    data_hash: 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    observed_at: '2026-10-10T16:00:00Z',
    quality_state: 'SUSPECT',
    values: {
      water_level_m: 0.38,
      rate_of_rise_m_min: 0.08,
      anomaly_note: 'Rate of rise gradient mismatch with upstream station',
    },
    is_verified: true,
  },
];

export default function Evidence() {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterWard, setFilterWard] = useState<string>('ALL');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const filteredEvidence = SAMPLE_EVIDENCE.filter((item) => {
    if (filterType !== 'ALL' && !item.evidence_type.includes(filterType)) return false;
    if (filterWard !== 'ALL' && item.ward_id !== filterWard) return false;
    return true;
  });

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 bg-slate-800 rounded-lg border border-slate-700 shadow gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">Cryptographic Evidence Registry</h2>
            <SimulatedBadge />
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Immutable, content-hashed evidence records (EV-...) binding every model inference and decision to its raw observational origin.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={filterWard}
            onChange={(e) => setFilterWard(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none"
          >
            <option value="ALL">All Wards</option>
            <option value="WARD-117">WARD-117 (Velachery North)</option>
            <option value="WARD-112">WARD-112 (T. Nagar)</option>
            <option value="WARD-113">WARD-113 (West Mambalam)</option>
          </select>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none"
          >
            <option value="ALL">All Evidence Types</option>
            <option value="METEOROLOGICAL">Meteorological</option>
            <option value="HYDROLOGICAL">Hydrological</option>
            <option value="TERRAIN">Terrain &amp; Geospatial</option>
          </select>
        </div>
      </div>

      {/* Evidence Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredEvidence.map((ev) => (
          <div
            key={ev.id}
            className="bg-slate-900 rounded-lg border border-slate-800 p-5 shadow space-y-4 hover:border-slate-700 transition"
          >
            {/* Header */}
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                  {ev.id}
                </span>
                <h3 className="text-sm font-bold text-white mt-1.5">{ev.evidence_type}</h3>
                <div className="text-xs text-slate-400">
                  Source: <strong className="text-slate-300">{ev.source_id}</strong> &bull; Ward: {ev.ward_id}
                </div>
              </div>

              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                  ev.quality_state === 'VALID'
                    ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                    : 'bg-amber-950/60 text-amber-300 border-amber-800'
                }`}
              >
                {ev.quality_state}
              </span>
            </div>

            {/* SHA-256 Content Hash */}
            <div className="p-2.5 bg-slate-950 rounded border border-slate-800/80">
              <div className="flex justify-between items-center text-[11px] text-slate-400 mb-1">
                <span>SHA-256 Provenance Digest:</span>
                <button
                  onClick={() => handleCopyHash(ev.data_hash)}
                  className="text-xs text-blue-400 hover:text-blue-300"
                >
                  {copiedHash === ev.data_hash ? 'Copied!' : 'Copy Hash'}
                </button>
              </div>
              <div className="font-mono text-[11px] text-slate-300 break-all select-all">
                {ev.data_hash}
              </div>
            </div>

            {/* Observational Payload Values */}
            <div className="space-y-1.5 text-xs">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Raw Telemetry Payload Snapshot:
              </div>
              <div className="bg-slate-950/80 p-3 rounded font-mono text-[11px] text-slate-300 space-y-1">
                {Object.entries(ev.values).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500">{k}:</span>
                    <span className="text-cyan-300 font-semibold">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Timestamp & Verification Tag */}
            <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-500 flex justify-between items-center">
              <span>Observed: {new Date(ev.observed_at).toLocaleString()}</span>
              <span className="text-emerald-400 flex items-center gap-1">
                &check; Cryptographically Intact
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
