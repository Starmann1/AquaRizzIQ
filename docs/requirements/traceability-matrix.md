# AquaRizz Requirement Traceability Matrix

**Updated:** 2026-10-11. Status distinguishes tested behavior from partial foundations. `VERIFIED` means a named repository test exists and has passed in the current verification run; `PARTIAL` means the acceptance requirement is broader than present implementation/evidence; `OPEN` means unavailable or not implemented.

| Requirement | Component | Acceptance coverage | Implementation | Status |
|---|---|---|---|---|
| REQ-SRC-01 | Source integrity | `test_dataset_sources.py`; `scripts/validate_chennai_sources.py` | `scripts/process_*.py`, `data/manifest.yaml` | VERIFIED |
| REQ-GEO-01 | Source boundaries/geometry | `test_geospatial.py`, `test_dataset_sources.py` | `scripts/import_chennai_boundaries.py`, `apps/api/app/geospatial/grid.py` | VERIFIED for source layers; grid-to-ward analysis partial |
| REQ-DATA-01 | Data quality and missingness | `test_ingestion.py`, `test_quality_policy.py`, `test_api_endpoints.py` | `apps/api/app/services/quality_policy.py`, `apps/api/app/api/data.py`, `apps/web/src/pages/DataModelQuality.tsx` | VERIFIED for deterministic critical/non-critical state decisions and surfaced matrix; per-source freshness tuning and persisted assessment lineage remain partial |
| REQ-API-ERR-01 | API error contract | validation/HTTP Problem Details cases in `test_api_endpoints.py` | `apps/api/app/errors.py`, `apps/api/app/main.py` | VERIFIED for application, HTTP, and schema-validation envelopes; idempotency and pagination policies remain partial |
| REQ-RSK-01 | Live ward risk | `test_get_risk_overview` in `test_api_endpoints.py` | `apps/api/app/api/risk.py`, `apps/api/app/risk/engine.py` | VERIFIED for fail-closed abstention; calibrated live risk unavailable |
| REQ-HYD-01 | Hydrology proxy | `test_hydrology.py` | `apps/api/app/hydrology/` | PARTIAL: proxy tests exist; not validated for Chennai |
| REQ-ML-01 | M1 susceptibility | `test_models.py` | `apps/api/app/forecasting/` | PARTIAL: implementation/unit coverage is not a real-data evaluation |
| REQ-ML-02 | M2 forecast | `test_models.py` | `apps/api/app/forecasting/` | PARTIAL: no eligible live forecast input/evaluation |
| REQ-EXP-01 | Explanation | `test_explainability.py`, `test_demo_scenario.py` | `apps/api/app/explainability/`, `apps/api/app/services/demo_scenario.py` | PARTIAL: scenario trace verified; observed-risk attribution unavailable |
| REQ-AGT-01 | Agent orchestration | `test_agents.py`, `test_verifier.py` | `apps/api/app/agents/graph.py` | PARTIAL: defined paths tested; full failures/permissions acceptance remains |
| REQ-REV-01 | Human review/authentication | `test_approval.py`, `test_operator_auth.py`, `test_audit_api.py` | `apps/api/app/api/reviews.py`, `apps/api/app/auth.py` | PARTIAL: SQLite tests pass; PostgreSQL transactions/concurrency unverified |
| REQ-ROU-01 | Prototype route safety boundary | `test_routing.py`, `test_api_endpoints.py` | `apps/api/app/routing/planner.py`, `apps/api/app/api/routes_api.py`, `apps/web/src/pages/Routing.tsx` | VERIFIED for synthetic-only labeling, invalid overlay rejection, and path/no-path behavior; operational routing remains unavailable |
| REQ-AUD-01 | Audit trail | `test_audit.py`, `test_audit_api.py` | `apps/api/app/audit/` | PARTIAL: hash-chain behavior tested; whole assessment/review/dispatch linkage remains |
| REQ-DEMO-01 | Deterministic scenario replay | `test_demo_scenario.py`, `test_demo_control_api` | `configs/scenarios/demo-storm-01.yaml`, `apps/api/app/services/demo_scenario.py` | VERIFIED for deterministic simulated replay/reset, fixture SHA-256 lineage, and bounded exercise recommendation |
| REQ-UI-01 | Operator views | `npm run build`; manual P0 API-to-map check | `apps/web/src/pages/` | PARTIAL: build passes; browser acceptance/accessibility automation incomplete |
| REQ-DB-01 | SQLite prototype / PostgreSQL portability | `test_sqlite_spatial.py`; full suite and `scripts/run_demo.py` on default SQLite | `apps/api/app/config.py`, `apps/api/app/database.py`, SQLAlchemy models | VERIFIED for SQLite startup and prototype flow; PostgreSQL/PostGIS migration, roles, indexes, and transaction behavior remain OPEN and optional |

## Verification commands

```powershell
pytest --basetemp .pytest-tmp apps/api/tests -q
cd apps/web
npm run build
```

The PostgreSQL row stays open until the same checks are run against a configured PostgreSQL/PostGIS instance. SQLite results do not substitute for database permissions, PostGIS index, migration, or concurrency evidence.
