# AquaRizz — Consolidated Architecture Baseline

## 1. System Context & Paradigm
AquaRizz operates as a **Modular Monolith** with **LangGraph Agentic Governance**.
The prototype runs **natively on the host workstation** without containerization (NO Docker/Kubernetes).

### Logical Layers
1. **Data Sources**: Simulated GCC telemetry, IMD Open Weather, historical flood archives.
2. **Ingestion & Validation**: QC classification (`VALID`, `SUSPECT`, `STALE`, `MISSING`, `CONFLICTING`, `OUTLIER`, `INVALID`).
3. **Database**: PostgreSQL with PostGIS extension. Internal metric CRS: EPSG:32644 (UTM 44N). Edge API: EPSG:4326.
4. **Geospatial Engine**: 250m regular analytical grid across GCC wards, with terrain indices (Elevation, Slope, HAND, TWI, Imperviousness).
5. **Hydrology & Sensor Simulator**: SCS Curve Number runoff calculation, linear reservoir routing proxy, tide backwater factor, Manning drain capacity proxy.
6. **Machine Learning**: 
   - **M1**: Static flood susceptibility ranking (LightGBM).
   - **M2**: Multi-horizon quantile water-level forecast (+15, +30, +60, +120 min) using LightGBM.
7. **Hazard & Risk Formulation**:
   - Hazard: Calibrated logistic sigmoid $H = \sigma((z - b) / T)$ with band cuts at 0.10, 0.40, 0.70.
   - Exposure $E$ & Vulnerability $V$: Percentile-weighted 4-factor models.
   - Impact $I = 0.6E + 0.4V$.
   - Safety floors (F1, F2, F3) for immediate overrides.
8. **Explainability**: Exact Shapley value attribution for ward risk index ($\le 8$ factor coalitions), TreeSHAP for models, content-hashed evidence registry.
9. **LangGraph Agentic Orchestration**: 6 typed agents executing in a deterministic graph pipeline.
10. **Human Review Gate**: Mandated human approval state machine (`DRAFT` -> `PENDING_REVIEW` -> `APPROVED` -> `DISPATCHED`).
11. **Routing**: OSMnx & NetworkX risk-penalized Dijkstra routing to flood shelters.
12. **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, MapLibre GL JS, Apache ECharts.
