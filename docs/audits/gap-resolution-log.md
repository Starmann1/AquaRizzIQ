# AquaRizz Gap Resolution and Verification Register

**Updated:** 2026-10-11
**Source register:** `AquaRizz_Collective_Discrepancy_Gap_Register_for_Antigravity.md`
**Status vocabulary:** `DONE` = implementation and relevant checks are present; `PARTIAL` = implemented in part or not fully verified; `OPEN` = not implemented. Documentation alone does not establish verification.

Earlier versions of this file overstated completion for P0/P1 items. This status table replaces those claims and links to the current evidence. P0 gate accounting is recorded in [p0-completion-audit.md](p0-completion-audit.md); P1/P2 implementation state and remaining prototype work are recorded in [p1-p2-prototype-roadmap.md](../implementation/p1-p2-prototype-roadmap.md).

## P0 — Prototype source-data gate

| Gap | Status | Evidence / limitation |
|---|---|---|
| P0-01 Synthetic vs observed readiness | `DONE` for P0 gate | Processed/source layers carry data classification; current ward risk remains abstained. Full model readiness lifecycle is outside this source-data gate. |
| P0-02 Prototype thresholds | `DONE` for P0 gate | Prototype policy remains distinct from operational approval. Scenario output is exercise-only. |
| P0-03 Calibration specification | `PARTIAL` | No calibrated live forecast is served; calibration acceptance must be completed before forecasts are enabled. |
| P0-04 Approval freshness binding | `PARTIAL` | Review/auth protections exist; end-to-end PostgreSQL freshness/transaction verification is outstanding. |
| P0-05 Runtime DB permissions | `PARTIAL` | No PostgreSQL role test was possible with configured local credentials. The demo uses explicit SQLite mode; this is not evidence of production DB permissions. |
| P0 source inventory, provenance, processing, API/map, abstention and tests | `DONE` for supplied 50-item P0 gate | See the linked P0 audit for exact counts, commands, and exceptions. Six boundary joins remain unresolved; missing values are preserved rather than fabricated. |

## P1 — Engineering, model, and governance

| Gap | Status | Evidence |
|---|---|---|
| P1-01 Leakage-resistant splits | `PARTIAL` | No performance claim or supported held-out training workflow. |
| P1-02 Quality-state behavior | `PARTIAL` | Missing critical inputs abstain; full seven-state behavior matrix is not verified. |
| P1-03 API/model/frontend contracts | `PARTIAL` | Typed contracts exist; no full generated schema compatibility check. |
| P1-04 Risk formula boundaries | `PARTIAL` | Deterministic implementation exists; complete threshold-edge acceptance is outstanding. |
| P1-05 Coverage | `PARTIAL` | Source coverage and limitations are surfaced; sensor fault scenarios/ward coverage remain. |
| P1-06 Evaluation criteria | `PARTIAL` | Metrics are not claimed without validated labels; real evaluation awaits data. |
| P1-07 Lineage | `PARTIAL` | Source hashes/manifests exist; immutable assessment snapshots are incomplete. |
| P1-08 API errors/retry | `PARTIAL` | Application, HTTP, and schema-validation failures use RFC 7807 Problem Details and request IDs; retry/idempotency and pagination contracts remain. |
| P1-09 Cross-layer schema | `PARTIAL` | Key contracts are typed; full DB/API/UI contract checks remain. |
| P1-10 Agent boundary | `PARTIAL` | Deterministic services own numeric decisions; prohibited-tool tests are incomplete. |
| P1-11 Agent transitions | `PARTIAL` | Typed graph exists; failure/retry/interruption cases are incomplete. |
| P1-12 Agent permissions | `PARTIAL` | Policy is documented; runtime restrictions need broader tests. |
| P1-13 Human approval | `PARTIAL` | Authenticated approval flow exists; PostgreSQL concurrency/expiry verification remains. |
| P1-14 CRS and spatial joins | `PARTIAL` | Source CRS processing is explicit; six unresolved joins and PostGIS verification remain documented. |
| P1-15 Hydrology honesty | `DONE` for exercise slice | Synthetic storm replay is explicitly classified and not presented as an observed forecast. |
| P1-16 Routing semantics | `PARTIAL` | Unavailable/unverified state is surfaced; full stale/blocked/no-route acceptance is incomplete. |
| P1-17 DB integrity | `PARTIAL` | Explicit SQLite mode and EWKB shim exist; PostgreSQL/PostGIS schema, roles, migrations and transactions are unverified. |
| P1-18 Security | `PARTIAL` | PBKDF2-HMAC-SHA256, signed tokens, role checks, and server-bound reviewer identity are implemented; external deployment controls remain. Prior bcrypt/Argon2 claim was inaccurate. |
| P1-19 Observability | `PARTIAL` | Request ID and health/readiness endpoints exist; full persisted correlation trail remains. |
| P1-20 Traceability | `DONE` as current status register | See traceability matrix and P1/P2 roadmap; status is not a claim that every requirement is verified. |
| P1-21 Vertical testing | `PARTIAL` | Relevant source, API, auth, risk, routing, agent, and scenario suites exist; not all 15 listed failure scenarios are covered. |
| P1-22 Native startup | `PARTIAL` | No Docker dependency; explicit SQLite demo mode exists. Clean-machine/PostgreSQL setup is not verified. |
| P1-23 Frontend states | `PARTIAL` | Data provenance, simulated exercise, and abstention are surfaced; browser/accessibility/responsive coverage remains. |

## P2 — Prototype quality

| Gap | Status | Evidence |
|---|---|---|
| P2-01 End-to-end story | `PARTIAL` | Overview includes a deterministic storm timeline; complete persisted evidence-to-review walkthrough is not present. |
| P2-02 Explainability | `DONE` for exercise slice | Trace shows deterministic weighted inputs and explicitly disclaims causality; no percentages or unsupported confidence. |
| P2-03 Bounded recommendations | `PARTIAL` | Only a simulated draft exercise action is returned; full controlled catalogue and evidence binding remain. |
| P2-04 Demo reliability | `PARTIAL` | Reset/peak controls and API walkthrough script exist; offline tile dependency/clean start is not guaranteed. |
| P2-05 Limitations | `DONE` for known sources | P0 and dataset audits document source, datum, coverage, missing-data, and operational limitations. |

## Verification snapshot

Commands run for the current implementation are recorded in the final task report. The authoritative evidence includes the API test suite, frontend production build, local API walkthrough (when available), source validator, and P0 audit. PostgreSQL/PostGIS checks must remain `PARTIAL` until run against a configured local instance.
