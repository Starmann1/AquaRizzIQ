# P1/P2 Prototype Implementation Status and Completion Plan

**Updated:** 2026-10-11  
**Scope:** Implementable local demonstration work after the P0 source-data gate.  
**Status rule:** `DONE` means implementation and relevant checks exist; `PARTIAL` means some controls exist but acceptance evidence is incomplete; `OPEN` means not implemented. A simulated exercise does not count as live flood evidence.

## Demonstration slice now available

The prototype can present an evidence-led sequence:

1. **Sense:** serve processed GCC divisions/zones, historical 2015 inundation, and the dated TN-SMART station snapshot with provenance and quality limitations.
2. **Predict/assess:** keep live ward risk and forecasts at `INSUFFICIENT_EVIDENCE` while the required current water level, validated rainfall, and exposure/vulnerability evidence are unavailable.
3. **Exercise:** replay the explicit seven-step synthetic storm with reset, next-step, peak, slider, and timeline controls. Scenario outputs carry `SIMULATED_SCENARIO_ONLY`; confidence is not evaluated.
4. **Explain:** show the deterministic model's weighted input terms as a non-causal trace, not Shapley percentages or causal claims.
5. **Decide:** show a bounded `EXERCISE_REVIEW` draft requiring a human. The demo endpoint has no approval or dispatch operation.

The scenario is intentionally isolated from current-risk endpoints. Its cursor is process-local and resets with the service or explicit reset action; it is not persisted as an operational assessment.

## P1 register

| ID | Status | Current implementation and remaining acceptance work |
|---|---|---|
| P1-01 Leakage-resistant evaluation | `PARTIAL` | No supported model-performance claim is made. No held-out training/evaluation pipeline or reproducible split metadata is established; required only when real labelled training data is introduced. |
| P1-02 Input-quality behaviour | `PARTIAL` | `quality_policy.py` defines deterministic decisions for all seven states for critical and non-critical inputs; `/data/quality` exposes the matrix and the UI displays it. Tests cover every state. Per-source configurable freshness, unresolved conflict lineage per persisted assessment, and audit linkage remain. |
| P1-03 API/frontend contracts | `PARTIAL` | Pydantic schemas and TypeScript types exist, including typed scenario responses. Generated OpenAPI-to-TypeScript compatibility checks and all endpoint contract checks remain. |
| P1-04 Risk boundaries | `PARTIAL` | Deterministic risk engine and prototype threshold configuration exist. Complete threshold-edge/property checks and document every policy boundary before any observed-data risk is enabled. |
| P1-05 Coverage | `PARTIAL` | Source coverage is visible in the data/map views; public snapshot is not treated as live coverage. Scenario faults for dropout, stale and contradictory sensors, and ward-level coverage summaries remain. |
| P1-06 Evaluation criteria | `PARTIAL` | No accuracy claims are made; metrics are explicitly unevaluated without suitable labels. Dataset-specific evaluation protocol and reporting artifact remain blocked on validated labelled data. |
| P1-07 Lineage | `PARTIAL` | Source manifest and processed data audits record hashes/provenance; each scenario response includes a SHA-256 fixture fingerprint and stable scenario/step reference. Immutable input snapshots and end-to-end persisted assessment lineage remain. |
| P1-08 API errors/retries | `PARTIAL` | Application, HTTP, and request-validation failures now use RFC 7807 Problem Details with request IDs; validation responses omit submitted values. Idempotency/retry policy and endpoint-wide pagination/size contracts remain. |
| P1-09 Schema consistency | `PARTIAL` | Sensitive identity fields are server-bound and scenario contract is typed. Full API/DB/frontend cross-contract validation and migration compatibility remain. |
| P1-10 Deterministic/agent boundary | `PARTIAL` | Deterministic services own risk computation; graph state is typed and live risk abstains. Add enforcement tests proving agent nodes cannot mutate policy or call dispatch. |
| P1-11 Graph failure handling | `PARTIAL` | Typed graph and failure/abstention paths exist. Retry/timeout/interruption and side-effect idempotency acceptance cases remain incomplete. |
| P1-12 Agent permissions | `PARTIAL` | Policy boundaries are documented; no direct dispatch is exposed in the scenario path. Complete per-agent allowed-tool tests and runtime tool restrictions. |
| P1-13 Human approval | `PARTIAL` | Authenticated review and approval routes, role checks, content binding, and audit trail exist. PostgreSQL transaction/concurrency behavior and expiry/revalidation need live database verification. |
| P1-14 CRS/spatial joins | `PARTIAL` | Source processing records CRS, transform, clipping, geometry validity, and unresolved joins. PostgreSQL/PostGIS geometry/SRID/index verification remains. |
| P1-15 Hydrology honesty | `DONE` for the demo slice | No unvalidated hydrology model is presented as real. Scenario values are explicit fixtures and API/UI label them simulated; broader physical-model unit validation is outside this demonstrator. |
| P1-16 Routing safety | `PARTIAL` | API and UI identify the synthetic graph, declare `safety_decision=NOT_EVALUATED`, and reject malformed/out-of-range illustrative overlays. The graph remains a pathfinding demonstration only; freshness-bound real hazard and verified road/shelter data are absent, so it is not decision support. |
| P1-17 Database integrity | `PARTIAL` | SQLite is the default; source-backed layers are loaded into portable SQL tables and the demo/API contract works without a database service. Backend selection does not silently fall back. PostgreSQL/PostGIS migrations, role grants, spatial indexes, and transaction/concurrency behavior remain unverified and optional. |
| P1-18 Security | `PARTIAL` | PBKDF2-HMAC-SHA256 password hashing, signed tokens, role checks, and server-bound reviewer identity are implemented. The legacy gap log incorrectly said bcrypt/Argon2; it is corrected to PBKDF2. Rate limiting, deployment CORS/security-header review, secret scan, and PostgreSQL least-privilege verification remain. |
| P1-19 Observability | `PARTIAL` | Request IDs and separate health/readiness routes exist. Structured correlation through persisted assessment/agent/review events and dependency-failure diagnostics need further work. |
| P1-20 Traceability | `DONE` as a status register | This roadmap and the traceability matrix distinguish verified, partial, and open evidence. Requirement-specific test names/results still need a complete refreshed inventory. |
| P1-21 Vertical tests | `PARTIAL` | Source, risk-abstention, auth, demo, and data endpoints have automated coverage. The full acceptance list (restart, stale/conflicting feeds, route invalidation, duplicate dispatch) is not all implemented or verified. |
| P1-22 Native startup | `PARTIAL` | No Docker or database service is required for the local demo; SQLite is the default. README startup is documented and SQLite API-to-demo checks pass. Clean-machine dependency installation and optional PostgreSQL/PostGIS setup are not verified. |
| P1-23 Frontend states | `PARTIAL` | Overview and map show source coverage, synthetic labeling and abstention; route/review/forecast pages have explicit unavailable states. Routes are lazy-loaded with a loading status; browser automation and responsive/accessibility acceptance checks remain. |

## P2 register

| ID | Status | Demonstration result / remaining work |
|---|---|---|
| P2-01 End-to-end story | `PARTIAL` | Overview shows the eight-step sense-to-outcome chain, replayable scenario timeline, and the boundary between live abstention and synthetic exercise. The scenario has a stable fixture hash/reference; persisted observed assessment/evidence identifiers await a valid live input pipeline. |
| P2-02 Honest explanation | `DONE` for scenario | Timeline shows deterministic weighted-ramp terms, fixture inputs, method, and explicit non-causal wording; no invented attribution percentages or confidence. Real-data explanations remain unavailable until evidence suffices. |
| P2-03 Bounded recommendations | `PARTIAL` | Scenario recommendation is a catalogued draft with exercise-only scope, affected ward, exercise urgency, reason, assumptions, null confidence, evidence requirements, and mandatory human review. A production-approved operational catalogue and persisted approval binding remain outside the demonstrator. |
| P2-04 Demo reliability | `PARTIAL` | Scenario reset and deterministic peak/step selection work; `scripts/run_demo.py` verifies the API flow without approving/dispatching. Real OpenStreetMap raster tiles provide geographic context and require an internet connection; all demonstration data layers are served from the local SQL database. Clean-machine dependency installation remains unverified. |
| P2-05 Limitations | `DONE` for known sources | P0 audit and dataset docs state dated/stale/public/synthetic limitations, missing values, unresolved joins, datum caveat and risk abstention. Keep those surfaced in the walkthrough. |

## Completion sequence and acceptance gates

The implementation target is a strong, reviewable prototype. The following order keeps unverified data and database dependencies from being disguised as completed behavior.

1. **Contracts and quality behavior (P1-02/03/09):** one typed policy decision per quality state; explicit units/ranges/nullability; run API contract and invalid-input tests; keep non-valid critical evidence fail-closed.
2. **Deterministic core (P1-04/10/11/12/15):** test risk boundaries and safety-floor precedence; make graph failure/abstention paths explicit; ensure agents cannot mutate policy or dispatch; preserve deterministic no-LLM fallback.
3. **Identity, review, and traceability (P1-07/13/18/19/20):** bind reviewer identity on the server; record case/evidence/action linkage; ensure request IDs and audit verification are surfaced; report any non-persisted scenario state as such.
4. **Spatial and route boundaries (P1-14/16):** validate CRS/SRID and geometry behavior; keep synthetic route results machine-readable as simulated and safety-not-evaluated; do not unlock operational routing without verified current network and hazard inputs.
5. **Vertical acceptance (P1-21/23, P2-01/02/03/05):** walkthrough source layers → live abstention → scenario replay → non-causal trace → bounded human-review draft; exercise empty/error/rejected/no-path states; display limitations in the relevant UI.
6. **Reproducibility and deployment (P1-17/22, P2-04):** run the full suite and browser build using the default SQLite configuration. PostgreSQL/PostGIS is optional; verify its permissions, constraints, indexes, and transactions only after a working project-local `DATABASE_URL` is configured.
7. **Evidence-gated ML (P1-01/05/06):** until suitable labelled observations exist, retain `PARTIAL`; when available, define spatial-temporal holdouts, leakage checks, baselines, metrics, and coverage before any performance claim.

The state table above is the current gap register, not a promise that prerequisites unavailable on this workstation have passed. The remaining `PARTIAL` entries describe missing evidence or external data/runtime prerequisites and must not be converted to `DONE` by synthetic fixtures.

## Current local run

From the repository root in PowerShell:

```powershell
$env:DATABASE_URL = 'sqlite:///aquarizz.db'
python -m uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

In a second terminal:

```powershell
cd apps/web
npm install
npm run dev
```

SQLite is the default local demonstration database; it does not exercise PostgreSQL roles, PostGIS indexes, or production migrations. The map background uses OpenStreetMap tiles and needs an internet connection. Processed source layers are bundled locally and stored in the configured database at development startup.
