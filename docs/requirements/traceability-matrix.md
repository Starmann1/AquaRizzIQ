# AquaRizz Requirement Traceability Matrix (P1-20)

| Req ID | Component | Description | Acceptance Test | Implementation File | Status |
|---|---|---|---|---|---|
| **REQ-ING-01** | Ingestion | Ingest batch rainfall & water levels with QC states | `test_ingestion.py` | `apps/api/app/api/data.py` | Implemented |
| **REQ-ING-02** | Data Quality | Identify VALID, SUSPECT, STALE, MISSING, CONFLICTING | `test_data_quality.py` | `apps/api/app/services/data_quality.py` | In Progress |
| **REQ-GEO-01** | Geospatial | 250m regular analytical grid in EPSG:32644 | `test_geospatial.py` | `apps/api/app/geospatial/grid.py` | Ready for P5 |
| **REQ-HYD-01** | Hydrology | SCS-CN runoff calculation & linear reservoir | `test_hydrology.py` | `apps/api/app/hydrology/scs_cn.py` | Ready for P6 |
| **REQ-ML-01** | ML (M1) | Static flood susceptibility rank S in [0, 1] | `test_models.py` | `apps/api/app/forecasting/m1_susceptibility.py` | Ready for P7 |
| **REQ-ML-02** | ML (M2) | Multi-horizon quantile water-level regressor | `test_models.py` | `apps/api/app/forecasting/m2_water_level.py` | Ready for P7 |
| **REQ-HAZ-01** | Hazard | Logistic sigmoid hazard function with ramp terms | `test_hazard.py` | `apps/api/app/risk/hazard.py` | Ready for P8 |
| **REQ-RSK-01** | Risk | Matrix-gated risk evaluation with safety floors | `test_risk.py` | `apps/api/app/risk/engine.py` | Ready for P8 |
| **REQ-EXP-01** | Explainability | Exact Shapley value attribution (<= 8 groups) | `test_explainability.py` | `apps/api/app/explainability/shapley.py` | Ready for P9 |
| **REQ-AGT-01** | LangGraph | 6-agent deterministic orchestration pipeline | `test_agents.py` | `apps/api/app/agents/graph.py` | Ready for P10 |
| **REQ-REV-01** | Human Gate | Mandated database human review before alert dispatch | `test_approval.py` | `apps/api/app/services/review.py` | Ready for P12 |
| **REQ-ROU-01** | Routing | Flood-penalized Dijkstra shelter routing | `test_routing.py` | `apps/api/app/routing/planner.py` | Ready for P13 |
| **REQ-UI-01** | Frontend | 12 operator views with visible SIMULATED badges | `e2e/demo_scenario.spec.ts`| `apps/web/src/App.tsx` | Skeleton Ready |
| **REQ-AUD-01** | Audit | Hash-chained SHA-256 immutable audit logging | `test_audit.py` | `apps/api/app/audit/logger.py` | Implemented |
