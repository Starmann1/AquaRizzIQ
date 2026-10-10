# AquaRizz — AGENTS.md (Agent System Guidelines)

## 1. Project Overview & Role Architecture
AquaRizz is a local-first, modular-monolith early warning flood decision support system for Chennai (Greater Chennai Corporation - GCC), combining physical hydrological proxies, calibrated statistical hazard modeling, LightGBM machine learning, and LangGraph agentic orchestration.

### The 6 Canonical Agents
1. **Orchestrator Agent**: Manages the analysis cycle, schedules workflow nodes, handles retries, logs node transitions, and ensures policy invariants.
2. **Data & Retrieval Agent**: Gathers catchment inputs (rainfall observations, forecasts, sensor water levels, static terrain features) and assesses data quality flags (`VALID`, `SUSPECT`, `STALE`, `MISSING`, `CONFLICTING`, `OUTLIER`, `INVALID`). Triggers abstention on critical missing data.
3. **Forecasting Agent**: Executes near-term forecast models (M2 LightGBM Quantile Regressor for $\Delta h$ at +15, +30, +60, +120 min horizons) and queries susceptibility scores (M1).
4. **Flood Risk Analysis Agent**: Computes hazard index $H = \sigma((z - b) / T)$, calculates Exposure $E$, Vulnerability $V$, Impact $I$, determines risk band/level, and checks deterministic safety floors (F1-F3).
5. **RCA & Explanation Agent**: Decomposes risk drivers using Exact Shapley values (grouped coalitions $\le 8$), formats evidence bindings (`EV-<TYPE>-<WARD>-<TIMESTAMP>-<HASH8>`), and generates explanations.
6. **Decision & Recommendation Agent**: Synthesizes structured recommendations, checks action catalogues against policy rules, verifies thresholds, and drafts alert decision cases for human approval.

---

## 2. Strict Boundary Rules for Autonomous Agents (P1-10, P1-12)

### Prohibited Agent Actions
- **NO Raw SQL Execution**: Agents must never run arbitrary SQL or schema alterations.
- **NO Direct Alert Dispatch**: Agents CANNOT approve or dispatch consequential alerts. Only human operators via authenticated endpoints can trigger dispatch.
- **NO Numerical Invention**: Agents cannot synthesize numbers, change model weights, or override safety floor classifications.
- **NO Dynamic Threshold Alteration**: Risk policy thresholds are version-locked in immutable `config_versions`.

### Mandatory Behavior
- **Typed State**: All agent state communication occurs via `AnalysisState` (Pydantic / TypedDict).
- **Abstention as a First-Class Output**: If data quality checks fail or confidence drops below 0.20, agents must emit `INSUFFICIENT_EVIDENCE` or `ABSTAINED` with explicit missing evidence lineage.
- **LLM Mode Fallbacks**: In `LLM_MODE=off` or `LLM_MODE=template`, the system operates deterministically without external API calls.

---

## 3. Technology Stack & Local Execution
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, LightGBM, Shapley, NetworkX, OSMnx.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, MapLibre GL JS, Apache ECharts.
- **Database**: PostgreSQL with PostGIS extension. Working CRS: EPSG:32644 (UTM Zone 44N); API exchange CRS: EPSG:4326.
- **NO DOCKER**: All components run as native local processes.
