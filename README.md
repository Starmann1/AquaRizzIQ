# AquaRizzIQ — Urban Flood Early Warning Decision Support System

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-005571.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178c6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646cff.svg)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Tests Passing](https://img.shields.io/badge/tests-43%20passed-brightgreen.svg)]()
[![Execution](https://img.shields.io/badge/architecture-local--first%20(NO%20DOCKER)-success.svg)]()

> **A Technically Coherent, Local-First, Explainable Early Warning Flood Decision Support System (DSS) for Greater Chennai Corporation (GCC).**  
> Consolidates physical hydrological proxies, calibrated logistic hazard modeling, LightGBM quantile water-level forecasting, exact game-theoretic Shapley explainability, and LangGraph agentic governance — running **100% natively without Docker**.

---

## 1. Executive Summary & Problem Context

Greater Chennai Corporation (GCC) suffers from recurrent, severe urban flash-flooding (such as the 2015 floods, Cyclone Michaung in 2023, and intense northeast monsoon squalls). The catchment faces unique hydrological constraints:
- **Flat Coastal Topography:** Mean elevation between 3m and 7m MSL with sub-1° slopes.
- **Tidal Lock Backwater:** High tides in the Bay of Bengal impede gravity discharge from the Adyar River, Cooum River, and Buckingham Canal.
- **Rapid Runoff:** Severe soil sealing with urban imperviousness exceeding 70% in central commercial districts (T. Nagar, West Mambalam).
- **Subway/Underpass Flash Surcharges:** Depressed transportation corridors surcharge rapidly during intense convective cloudbursts.

**AquaRizzIQ** replaces vague, probabilistic weather alerts with an **auditable, evidence-bound decision support system** that computes actionable tactical advice (pump deployments, traffic diversions, shelter evacuations) while enforcing strict human approval gates.

---

## 2. Canonical MVP Architecture

AquaRizz is built as a **Modular Monolith** orchestrated by **LangGraph**, executing natively as host processes on the local development workstation:

```
                                [ REAL-TIME CATCHMENT TELEMETRY ]
                         (Automated Weather Stations, Radar Gauges, Ultrasonic Depth)
                                                 │
                                                 ▼
                                    [ DATA QUALITY GATE (P1-02) ]
                           (VALID, SUSPECT, STALE, OUTLIER, CONFLICTING)
                                                 │
                                                 ▼
                              [ POSTGRESQL + POSTGIS / SQLITE DUAL DIALECT ]
                                  (Analytical Grid: EPSG:32644 UTM 44N)
                                ├── 250m Regular Analytical Grid Cells
                                └── Terrain Priors (Elevation, HAND, Slope, TWI)
                                                 │
                                                 ▼
                                   [ HYDROLOGY & ML FORECASTING ]
                                ├── SCS-CN Runoff & Linear Reservoir Routing
                                ├── M1 LightGBM Static Susceptibility Prior
                                └── M2 Multi-Horizon Probabilistic Forecaster (+15..+120m)
                                                 │
                                                 ▼
                                    [ HAZARD & MATRIX-GATED RISK ]
                                ├── Calibrated Logistic Sigmoid (b₀ = -3.5)
                                ├── Risk R = Matrix-Gated (Hazard Band × Impact)
                                └── Safety Floors (F1: Surcharge ≥ 0.85 → HIGH)
                                                 │
                                                 ▼
                                  [ EXPLAINABILITY & VERIFIERS V1–V6 ]
                                ├── Exact Game-Theoretic Shapley Values (2ᴺ coalitions)
                                ├── Content-Hashed Evidence Registry (EV-...)
                                └── Safety Verifiers (V1 Grounding, V4 Uncertainty, V5 Guard)
                                                 │
                                                 ▼
                                  [ LANGGRAPH 6-AGENT ORCHESTRATOR ]
                                (Plan → Retrieve → Forecast → Risk → RCA → Policy)
                                                 │
                                                 ▼
                                   [ HUMAN REVIEW & APPROVAL GATE ]
                                (DRAFT → PENDING_REVIEW → APPROVED → DISPATCHED)
                                                 │
                                                 ▼
                                    [ DISPATCH & EVACUATION ROUTE ]
                                ├── Simulated Siren & Broadcast Gateway
                                ├── Dijkstra Risk-Penalized Shortest Path to Shelters
                                └── SHA-256 Cryptographic Audit Hash Chain
```

---

## 3. The 6 Canonical Autonomous Agents

All agent state transitions are strictly typed and immutable via `AnalysisState`:

1. **Orchestrator Agent:** Controls analysis cycles, node transitions, execution retries, and invariant enforcement.
2. **Data & Retrieval Agent:** Gathers catchment inputs, verifies sensor telemetry against bounds and freshness windows, and emits `INSUFFICIENT_EVIDENCE` or `ABSTAINED` on critical telemetry gaps.
3. **Forecasting Agent:** Executes M1 susceptibility scoring and M2 quantile regression for $\Delta h$ at $+15$, $+30$, $+60$, and $+120$ minute lead horizons.
4. **Flood Risk Analysis Agent:** Computes logistic Hazard $H$, Exposure $E$, Vulnerability $V$, Impact $I = E \times V$, applies risk matrix gating, and verifies deterministic safety floors (F1–F3).
5. **RCA & Explanation Agent:** Computes exact Shapley attribution values over all $2^N$ coalitions, generates grounded narrative explanations, and links content-hashed evidence (`EV-...`).
6. **Decision & Recommendation Agent:** Formulates tactical recommendations, runs verifiers V1–V6, and submits decision cases for operator approval.

---

## 4. Scientific & Mathematical Formulations

### A. Hydrological Surface Proxy
* **SCS-CN Runoff Model:** Computes surface excess precipitation $Q$:
  $$Q = \frac{(P - I_a)^2}{P - I_a + S} \quad \text{for } P > I_a, \quad I_a = 0.2S, \quad S = \frac{25400}{\text{CN}} - 254$$
  where curve numbers ($\text{CN}$) reflect urban land use ($85 \le \text{CN} \le 98$).
* **Linear Reservoir Routing with Tidal Backwater:**
  $$\frac{dh}{dt} = \frac{Q(t) - Q_{\text{out}}(h)}{A_{\text{channel}}}, \quad Q_{\text{out}} = k \cdot (h - h_{\text{tide}})^+$$

### B. M2 Quantile Water Level Forecaster
* Generates probabilistic quantiles ($P_{10}, P_{50}, P_{90}$) for lead times $+15\text{m}, +30\text{m}, +60\text{m}, +120\text{m}$.
* Conformal prediction intervals widen monotonically over the lead horizon to reflect genuine aleatoric and epistemic uncertainty.

### C. Calibrated Logistic Hazard Model
* Computes continuous flood hazard probability $H \in [0, 1]$:
  $$H = \sigma\left(\frac{z - b_0}{T}\right) = \frac{1}{1 + e^{-(z - b_0)/T}}$$
  with calibrated baseline intercept $b_0 = -3.5$ and temperature scaling $T = 1.0$, ensuring dry catchments yield $H \approx 0.035$ (LOW) and cloudbursts yield $H > 0.85$ (VERY_HIGH).

### D. Exact Shapley Value Attribution ($\sum \phi_i = \Delta H$)
* Evaluates all $2^N$ feature coalitions ($N \le 8$) in pure vectorized Python ($\le 2\text{ms}$ execution):
  $$\phi_i(v) = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|!(|N| - |S| - 1)!}{|N|!} \big[ v(S \cup \{i\}) - v(S) \big]$$
* **Mathematical Efficiency Axiom:** $\sum_{i=1}^n \phi_i = \Delta H = H_{\text{actual}} - H_{\text{dry baseline}}$. Zero leakage, zero double-counting, zero approximation noise.

### E. Risk-Aware Evacuation Routing
* NetworkX Dijkstra shortest path on penalized road edge weights:
  $$c_e = t_e \cdot (1 + 4 \cdot r_e)$$
  Submerged roads ($r_e \ge 0.90$) are dropped dynamically from the graph to prevent directing citizens through impassable underpasses.

### F. Immutable Cryptographic Audit Log
* Every action, approval, and dispatch is hash-chained:
  $$\text{row\_hash}_k = \text{SHA-256}(\text{row\_hash}_{k-1} + \text{JSON}(\text{details}_k))$$

---

## 5. The 12 Frontend Interface Views

The React + TypeScript + Vite web dashboard provides 12 specialized operational views:

| View | Route | Description |
| :--- | :--- | :--- |
| **Overview** | `/overview` | Catchment KPI summary cards, active storm scenario controller, monitored ward table. |
| **Flood Risk Map** | `/map` | Interactive SVG choropleth map of GCC wards with analytical breakdown ($H, E, V, I, R$). |
| **Ward Detail** | `/wards/:id` | Live telemetry gauges (ultrasonic water depth meter, 1h/3h rain gauges, rate of rise). |
| **Forecast** | `/forecast` | M2 multi-horizon (+15, +30, +60, +120m) probabilistic forecast fan chart with $P_{10}/P_{50}/P_{90}$ bands. |
| **Evidence** | `/evidence` | Content-hashed evidence registry cards (`EV-...`), SHA-256 digests, raw telemetry snapshots. |
| **RCA** | `/rca` | Exact Shapley factor attribution waterfall chart and Safety Verifier (V1–V6) compliance report. |
| **Recommendations** | `/recommendations`| Operational tactics (P1 evacuation advisories, traffic diversions, dewatering pumps, shelters). |
| **Human Review** | `/review` | Safety-critical human approval console with mandatory checklists and 60-minute validity gates. |
| **Alerts** | `/alerts` | Emergency broadcast gateway console with simulated sirens and dispatch logs. |
| **Routing** | `/routing` | Risk-aware evacuation route generator to nearest relief camps avoiding flooded corridors. |
| **Audit Trail** | `/audit` | SHA-256 hash-chained audit log with an interactive cryptographic chain verification engine. |
| **Data Quality** | `/quality` | Sensor telemetry quality matrix (`VALID`, `SUSPECT`, `STALE`, `OUTLIER`, `CONFLICTING`) & health cards. |

---

## 6. Local-First Setup & Running Guide (NO DOCKER)

AquaRizz is designed to run natively as local processes on Windows, macOS, or Linux.

### Prerequisites
- Python 3.11+ (Python 3.12 recommended)
- Node.js 18+ and npm
- PostgreSQL 16+ with PostGIS extension (or runs automatically with high-speed in-memory SQLite dual dialect)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Starmann1/AquaRizzIQ.git
cd AquaRizzIQ

# Install Python backend dependencies
pip install -r requirements.txt

# Install React frontend dependencies
cd apps/web
npm install
cd ../..
```

### 2. Run Automated Test Suite
```bash
# Executes all 43 backend tests
pytest apps/api/tests/ -v
```

### 3. Execute End-to-End Live Demonstration Script
```bash
# Simulates full dry -> storm -> surge -> LangGraph -> approval -> dispatch -> route cycle
python scripts/run_demo.py
```

### 4. Launch Local Development Servers

In **Terminal 1** (Backend FastAPI on `http://127.0.0.1:8000`):
```bash
python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000 --reload
```
* Interactive API Documentation (Swagger / OpenAPI): `http://127.0.0.1:8000/docs`

In **Terminal 2** (Frontend Dashboard on `http://localhost:5173`):
```bash
cd apps/web
npm run dev
```
* Open your browser and navigate to: `http://localhost:5173`

---

## 7. Project Structure

```
AquaRizzIQ/
├── apps/
│   ├── api/                           # FastAPI Modular Monolith Backend
│   │   ├── app/
│   │   │   ├── agents/                # LangGraph 6-Agent Orchestrator Pipeline
│   │   │   ├── api/                   # REST API Routers (Risk, Reviews, Routing, Audit, Forecasts)
│   │   │   ├── audit/                 # SHA-256 Hash-Chained Audit Logger
│   │   │   ├── db/                    # SQLAlchemy 2.0 Models, Dual-Dialect Enums & Repositories
│   │   │   ├── explainability/        # Exact Shapley Game-Theoretic Attribution & Narrator
│   │   │   ├── forecasting/           # M1 Susceptibility & M2 Quantile Water Level Models
│   │   │   ├── geospatial/            # PostGIS CRS (EPSG:32644), 250m Analytical Grid, DEM
│   │   │   ├── hydrology/             # SCS-CN Runoff, Reservoir Routing, Storm Simulator
│   │   │   ├── llm/                   # Safety Verifiers V1–V6 & Template Engine
│   │   │   ├── risk/                  # Calibrated Logistic Hazard, Matrix Gating & Safety Floors
│   │   │   ├── routing/               # NetworkX Dijkstra Risk-Penalized Shortest Path Planner
│   │   │   └── services/              # Ingestion, Data Quality Gate, Human Review Service
│   │   └── tests/                     # 43 Comprehensive Backend Unit & Integration Tests
│   └── web/                           # React 18 + TypeScript + Vite Dashboard
│       ├── src/
│       │   ├── api/                   # Typed API Client
│       │   ├── components/            # Reusable UI Badges, Spinners, Layout
│       │   ├── pages/                 # 12 Operational Dashboard Views
│       │   └── stores/                # Zustand State Store
│       └── package.json
├── configs/                           # Version-locked YAML Policies & Scenarios
│   ├── policy.yaml                    # Approval thresholds & RBAC requirements
│   ├── risk.yaml                      # Calibrated b0=-3.5 hazard weights & risk matrices
│   ├── routing.yaml                   # Road speed, flood penalty multipliers
│   ├── sensors.yaml                   # Monitored gauge coordinates & bounds
│   └── scenarios/demo-storm-01.yaml   # Deterministic convective inundation event
├── data/
│   └── fixtures/                      # GCC Wards GeoJSON (WGS84 & UTM 44N), Sensors, Users
├── docs/                              # Architecture Decision Records (ADRs) & Audit Registries
│   ├── adrs/                          # ADR-001 through ADR-005
│   └── audits/gap-resolution-log.md   # Gap registry reconciliation matrix
├── scripts/
│   ├── run_demo.py                    # Complete end-to-end deterministic demonstration
│   └── seed_data.py                   # Database seeding utility
├── Makefile                           # Local development helper targets
├── pyproject.toml                     # Python packaging configuration
└── requirements.txt                   # Pinned Python package dependencies
```

---

## 8. Safety & Policy Invariants

1. **NO DOCKER FOR PROTOTYPE:** All components run natively on developer workstations.
2. **NO AUTONOMOUS DISPATCH:** Agents can propose draft decision cases; only authenticated human operators (Emergency Coordinator role) can authorize public broadcast alerts.
3. **NO NUMERICAL HALLUCINATION:** Hazard probabilities, water depths, and risk scores are calculated deterministically by pure Python algorithms, never invented by language models.
4. **FAIL-SAFE ABSTENTION:** If telemetry data is `STALE` or sensor uncertainty exceeds thresholds, the system emits an explicit `ABSTAINED` status with full evidence lineage rather than guessing.
5. **HONEST PROVENANCE:** Synthetic and simulated data points are explicitly stamped with `is_simulated: true` and visible amber badges across the UI.

---

## 9. License

Developed for the **Dreamnnovation 2.0** Hackathon. Built under the MIT License.
