import { useParams } from 'react-router-dom';

export default function Evidence() {
  const { assessmentId } = useParams<{ assessmentId?: string }>();

  return (
    <main className="mx-auto max-w-4xl space-y-6">
      <header className="rounded-2xl border border-sky-200/90 bg-sky-50/95 p-6 shadow-sm backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-sky-800 bg-sky-100 px-3 py-1 rounded-lg border border-sky-200 shadow-2xs">
            EVIDENCE-CHAIN
          </span>
          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
            ✓ PostGIS Verified
          </span>
        </div>
        <h1 className="mt-2 text-2xl font-black text-sky-950 tracking-tight">Evidence Binding & Telemetry Lineage</h1>
        <p className="mt-1 text-sm text-slate-600">
          Source traceability for sensory observations, IMD rainfall grid bindings, and spatial catchment proxies.
        </p>
      </header>

      <section className="rounded-2xl border border-sky-200/90 bg-white/95 p-6 shadow-sm space-y-4">
        <h2 className="text-base font-bold text-sky-950">
          {assessmentId ? `Evidence Trace for Assessment ${assessmentId}` : 'Canonical Evidence Format Standard'}
        </h2>
        <p className="text-sm leading-relaxed text-slate-600 font-medium">
          Under the AquaRizz governance architecture, all risk drivers bind to immutable evidence tokens formatted as:
        </p>
        <div className="p-4 bg-sky-50/70 border border-sky-200 rounded-xl font-mono text-xs font-bold text-sky-900 shadow-2xs">
          EV-&lt;TYPE&gt;-&lt;WARD_ID&gt;-&lt;TIMESTAMP&gt;-&lt;HASH8&gt;
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3.5 bg-sky-50/50 rounded-xl border border-sky-100 text-xs">
            <span className="font-bold text-sky-900">EV-RAIN</span>
            <p className="text-slate-500 text-[11px] mt-1">AWS Telemetry & Radar Grid</p>
          </div>
          <div className="p-3.5 bg-sky-50/50 rounded-xl border border-sky-100 text-xs">
            <span className="font-bold text-sky-900">EV-STAGE</span>
            <p className="text-slate-500 text-[11px] mt-1">Water level pressure transducers</p>
          </div>
          <div className="p-3.5 bg-sky-50/50 rounded-xl border border-sky-100 text-xs">
            <span className="font-bold text-sky-900">EV-GEO</span>
            <p className="text-slate-500 text-[11px] mt-1">DEM, HAND & Imperviousness</p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-amber-200 bg-amber-50/70 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-amber-950">
          Deterministic Safety Floor Enforcement
        </h2>
        <p className="mt-2 text-xs leading-relaxed text-amber-900 font-medium">
          If critical sensor evidence is missing, stale (&gt;60m), or confidence drops below 0.20, agents withhold probabilistic scores and emit explicit abstention records to prevent false-negative safety hazards.
        </p>
      </section>
    </main>
  );
}
