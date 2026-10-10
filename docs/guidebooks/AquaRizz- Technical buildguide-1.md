# CHENNAI URBAN FLOOD EARLY WARNING SYSTEM

**TECHNICAL BUILD GUIDE & SPECIFICATION MANUAL**

**DREAMOVATION 2.0 — DREAM-SSB-09**

Prepared for Team DREAM-SSB-09 · Version 1.0 (implementation baseline) · 9 October 2026 · Prototype location: Chennai, Tamil Nadu, India

**How to read this manual.** Sections 1–5 explain what is built and why. Sections 6–12 define data, storage, geospatial processing and the numerical engines. Sections 13–22 define agents, safety and applications. Sections 23–32 are the engineering contracts (API, repository, configuration, testing, evaluation). Sections 33–42 give scope, roadmap, code, demo and final decisions. Sections 43–46 are appendices. Every statement about an outside dataset or service carries one of these tags:

- **\[VERIFIED\]** checked against the live source on 9 October 2026 (the GCC ArcGIS service; Open-Meteo access terms as published on public pages).
- **\[TEAM DOC\]** taken from the team's dataset report or the Gemini/Grok guidebooks and not re-verified. Confirm it with the Phase 1 source probe (§35).
- **\[ASSUMPTION\]** a prototype parameter chosen by this manual. It is not an official value, it lives in configuration, and it must be calibrated or replaced.
- **\[SIM\]** simulated data or behaviour. It is labelled as simulated in storage, API and UI.

## 1. Executive Summary

This manual specifies how to build, from an empty repository, a working Chennai-centred urban-flood early-warning and decision-support prototype for DREAM-SSB-09. It turns the conceptual flow SENSE → PREDICT → ANALYZE → EXPLAIN → DECIDE → LEARN into modules, tables, endpoints, formulas, tests and a 16-step demonstration that runs from data ingestion to prediction, explanation, human approval, alert, evacuation routing, outcome comparison and a controlled learning update.

**What the system is.** A decision-support platform. It computes ward-level flood likelihood for the next 0–120 minutes, scores the consequences for people and infrastructure, explains each result with evidence IDs, drafts alerts and evacuation recommendations, and waits for an authorised person to approve anything that leaves the building. It is not an autonomous emergency-response system.

**Where the numbers come from.** Forecasts, flood likelihood, risk scores, routes and attributions come from statistical models, ML models, deterministic hydrology and geospatial calculations. Agents orchestrate those tools. A language model never produces a number, an evidence ID or a safety instruction (§3, P2).

**Ten decisions that shape the build**

1. **Units.** Decision unit = GCC ward (about 200 wards in 15 zones \[TEAM DOC\]); computation unit = 250 m grid cell inside each ward. In this manual “zone” means ward unless stated otherwise.
2. **CRS and time.** EPSG:32644 for storage and analysis (the native CRS of the GCC service \[VERIFIED\]); EPSG:4326 only at the API/UI boundary. Timestamps are UTC `timestamptz`, displayed in Asia/Kolkata.
3. **Stack.** Python 3.11+, FastAPI, PostgreSQL 16 + PostGIS, React + MapLibre, LangGraph, LightGBM, Docker Compose. No Kubernetes, Kafka, Redis or vector database in the MVP.
4. **Risk formula.** A hazard-gated weighted sum of Hazard, Exposure and Vulnerability (default weights 0.4 / 0.3 / 0.3, as in the proposal). Terrain and drainage susceptibility are folded into Hazard so that a dry day, or high ground with many residents, cannot raise an alarm by itself (§12).
5. **ML only where data supports it.** A static susceptibility model and a short-horizon water-level forecaster (both LightGBM). No deep learning in the runtime path.
6. **Agents.** Six agents, one fixed LangGraph workflow, typed contracts, explicit abstention (`INSUFFICIENT_EVIDENCE`).
7. **Explanations.** Exact Shapley attributions over the risk formula plus an evidence registry. Template text by default; an optional local LLM may paraphrase, and its output is validated (§16).
8. **Human gate.** Every alert at HIGH or above, every evacuation recommendation and every resource request needs an authorised approver. Silence is never consent.
9. **Sensors and delivery.** Drain-level sensors are simulated \[SIM\] and enter through the same HTTP endpoint real devices would use. SMS, IVRS and push delivery are simulated; email goes to a sandbox inbox.
10. **Learning.** “Learning” means controlled re-evaluation, recalibration and retraining with human-gated model promotion. Online self-learning is not claimed.

**Real, derived, simulated**

| Layer | Real or open data | Derived by the system | Simulated \[SIM\] |
| --- | --- | --- | --- |
| Rainfall | IMD daily (OpenCity / imdlib), Open-Meteo archive (ERA5-based) and forecast | Accumulations, antecedent rainfall, blended nowcast | Rain-gauge network used in the live demo |
| Water level | none assumed public at drain level | Rise rate, fill ratio, forecast | All drain sensors, faults, battery and signal |
| Terrain, drainage | DEM, GCC storm-water drains, rivers | Slope, TWI, sink depth, HAND, drain density, capacity proxy | none |
| Exposure | GCC buildings, WorldPop, OSM facilities, GCC shelters | Exposed counts, E and V scores | Emergency-resource inventory |
| History | OpenCity flood layers | Susceptibility model, similar-event retrieval | none |
| Actions | Road network (OSM) | Routes, alerts, recommendations | SMS / IVRS / push delivery |

**Verified on 9 October 2026.** The GCC ArcGIS service `GCC_COLLABORATION_LAYER/MapServer` exposes nine layers (bridge category, river, centre line, carriageway, buildings, vehicular subways, ward, zone, storm-water drain) in EPSG:32644, with GeoJSON output and pagination at 2,000 features per request \[VERIFIED\]. The drain layer carries width, depth, invert-level, status and obstacle fields; how completely they are populated is not yet measured \[VERIFIED fields / unverified completeness\]. Open-Meteo's archive and forecast endpoints are keyless and free for non-commercial use with attribution \[VERIFIED via public pages; read the current terms before use\]. Everything else is inherited from team documents and stays tagged \[TEAM DOC\] until the Phase 1 probe passes.

## 2. Prototype Scope

### 2.1 The twenty capabilities and how each is built

| # | Capability | Built as | Data basis | Section |
| --- | --- | --- | --- | --- |
| 1 | Chennai rainfall ingestion | Connectors: Open-Meteo archive, IMD daily series, simulated gauges | Reanalysis + \[SIM\] | 9 |
| 2 | Weather / forecast ingestion | Open-Meteo hourly NWP forecast connector | Model output | 9 |
| 3 | Water-level monitoring | Sensor registry, ingestion API, QC flags | \[SIM\] | 9 |
| 4 | Simulated IoT sensors | SCS-CN runoff + reservoir simulator with fault injection | \[SIM\] | 9 |
| 5 | Terrain analysis | DEM → slope, TWI, flow accumulation, sink depth, HAND | Real, derived | 8, 10 |
| 6 | Drainage analysis | GCC drains → density, proximity, capacity proxy | Real (completeness TBD) | 8, 10 |
| 7 | Historical flood analysis | OpenCity event layers, similar-event retrieval | Real | 6, 16 |
| 8 | Zone-level flood-risk prediction | Hazard H(τ) per ward at 15-minute steps to 120 minutes | Model blend | 11, 12 |
| 9 | Hazard + exposure + vulnerability | Risk engine | Derived | 12 |
| 10 | Explainable risk | Shapley attribution + evidence registry | Derived | 16 |
| 11 | Confidence / uncertainty | Data-quality score + Monte-Carlo interval | Derived | 17 |
| 12 | Recommended action | YAML policy engine | Rules | 19 |
| 13 | Human approval | Review queue, approve / modify / reject, audit chain | Process | 18 |
| 14 | Alert generation | Template-based alert drafts, CAP-style payload | Rules | 21 |
| 15 | Evacuation route | OSMnx graph, risk-weighted Dijkstra | Derived | 20 |
| 16 | Shelter recommendation | GCC shelters ranked by safe-route score | Real (capacity may be unknown) | 20 |
| 17 | Emergency-resource recommendation | Greedy matching on simulated inventory | \[SIM\] | 19 |
| 18 | Dashboard visualization | React + MapLibre, 13 views | n/a | 22 |
| 19 | Actual-event comparison | Hindcast replay vs observed layers; simulated outcome | Real labels + \[SIM\] | 27, 37 |
| 20 | Continuous-learning demonstration | Evaluate → recalibrate → candidate model → human promotion | Controlled demo | 27 |

### 2.2 Definition of “demo-complete”

The prototype is complete when one scripted run, started from a clean checkout with `docker compose up`, does all of the following without manual database edits: (1) loads Chennai wards, drains, roads, buildings, shelters and terrain features; (2) replays a historical rainfall event while the simulator drives sensors; (3) shows ward risk changing on the map; (4) produces an explanation whose every factor cites stored evidence; (5) drafts an alert, an evacuation route and a resource plan; (6) blocks dispatch until an authorised user approves; (7) records the approval in the hash-chained audit log; (8) loads an observed outcome and compares it with the prediction; (9) produces a new candidate model version and shows metrics before and after; (10) passes the automated end-to-end test (§31).

### 2.3 In scope and out of scope

**In scope:** public datasets, GCC GIS layers, historical event replay, simulated sensors, the forecasting and risk engines, six agents, explainability, policy rules, human approval, simulated delivery, risk-aware routing, dashboard, evaluation harness, controlled learning.

**Out of scope (designed for later, not built):** live GCC drain telemetry; radar QPE; hydrodynamic 1D/2D inundation modelling; real SMS/IVRS/WhatsApp/social-media delivery; integration with national alerting systems; drone/CCTV analysis; citizen-report ingestion; multi-city operation; high availability; penetration testing.

### 2.4 Geographic scope and demo area

Study area = Greater Chennai Corporation limits (about 426 km² \[TEAM DOC\]; GCC full extent in EPSG:32644 roughly E 406–428 km, N 1,421–1,464 km \[VERIFIED\]), plus a 5 km analysis buffer for terrain and catchment context. Chennai needs SRTM-style tiles N12E080 and N13E080 (1° tiles named by their south-west corner).

**Demo-area rule.** The live demonstration uses a contiguous cluster of 8–15 wards that satisfies all of: (a) at least 80 % of the cluster's drain features have parseable width and depth; (b) every ward centroid lies within 3 km of at least one official shelter (if shelter data allows); (c) the cluster overlaps at least one historical flood layer; (d) at least 100,000 residents in total (WorldPop) \[ASSUMPTION\]; (e) the road graph inside the cluster is connected. Candidate 1 is the Velachery–Pallikaranai–Adyar corridor (named in the Grok guidebook; repeated inundation reported). Candidate 2 is Ambattur–Anna Nagar West. The Gemini guidebook's “Ward 112 / Zone 9” is not adopted by default because that label originates from an illustrative diagram, not from evidence; it joins the candidate list only if it passes (a)–(e). City-wide risk is still computed for all wards; the cluster gets the detailed layers (building polygons, sensors, routes).

### 2.5 Prototype limitations (stated up front)

- **L1** No live drain telemetry exists in this build; all drain sensors are simulated.
- **L2** The water-level forecaster is trained on simulated storms. Its metrics validate the pipeline, not real-world skill.
- **L3** Public DEMs are surface models with metre-scale vertical error in terrain whose total relief is about 0–10 m \[TEAM DOC\]. Elevation features are relative and noisy; they are never shown as survey-grade heights.
- **L4** Rainfall inputs are reanalysis, NWP or simulated gauges, not rain-gauge truth. No 15-minute rainfall-nowcast skill is claimed from public data.
- **L5** Historical flood labels are few and may be points or modelled zones. Susceptibility is indicative and probabilities are uncalibrated until §27 produces calibration evidence.
- **L6** Drain capacity is a proxy from partially populated GCC attributes, not a hydraulic model.
- **L7** The footprint is an “indicative flood-prone area” built from 250 m cells. It is not inundation depth or extent.
- **L8** All thresholds and weights are prototype values, not official NDMA or GCC values.
- **L9** Alert delivery is simulated except email to a sandbox inbox. No integration with any national or municipal alert gateway is claimed.
- **L10** Shelter capacity may be unknown; the resource inventory is simulated.
- **L11** Population is a static baseline, not real-time presence.
- **L12** Open-Meteo's free tier is for non-commercial use and carries no service guarantee.
- **L13** Single machine, no high availability, no security audit.

## 3. Design Principles

| ID | Principle | How it is enforced |
| --- | --- | --- |
| P1 | Decision support, not autonomy | Policy rules carry `requires_approval`; the dispatcher refuses any alert not in state APPROVED; tests assert this |
| P2 | Numbers come from models and calculations, never from an LLM | Agent contracts give the LLM adapter no write access to numeric fields; a narrative guard rejects text containing numbers or IDs not present in the input facts |
| P3 | Evidence or silence | Every explanation factor lists `evidence_ids` that exist in `evidence_items`; otherwise the explanation is rejected |
| P4 | Abstain rather than guess | State `INSUFFICIENT_EVIDENCE` when data quality is too low; risk fields are null; a review request is raised instead of an alert |
| P5 | Simulated is never shown as real | `is_simulated` flows from observation → evidence → explanation → alert → UI badge |
| P6 | Deterministic core, optional LLM | The full test suite passes with `LLM_PROVIDER=none` |
| P7 | One path for real and simulated data | The simulator posts to the same ingestion endpoint and writes the same tables as a real device would |
| P8 | Space and time are explicit | `CHECK (ST_SRID(geom)=32644)` on spatial columns; only timezone-aware timestamps are accepted; tests cover both |
| P9 | Prototype thresholds are not official thresholds | Separate `policy.prototype.yaml` and an empty `policy.official.yaml`; UI footer states which is active |
| P10 | Reproducibility | Every risk run stores config hash, model versions and input snapshot IDs |
| P11 | Fail visibly, degrade safely | Every external dependency has a fallback and a user-visible state (§28) |
| P12 | Boring technology; thin slice first | A walking skeleton on fake data exists before real data work; no component without a named purpose |

## 4. Final Architecture

### 4.1 Logical architecture: twelve layers

```
 L1  DATA SOURCES      GCC GIS · DEM · OpenCity · IMD/Open-Meteo · WorldPop · OSM · SIMULATOR
        │  pulls (worker)                              │ pushes (sensors, HTTP)
 L2  INGEST+VALIDATE   connector → schema check → QC flags → idempotent upsert
        ▼
 L3  DATA PLATFORM     PostgreSQL 16 + PostGIS (EPSG:32644) · data/ files + checksum manifest
        ▼
 L4  GEOSPATIAL        offline precompute (terrain, grid, zonal stats) · online PostGIS joins
        ▼
 L5  FORECAST / ML     rainfall blend · water-level LightGBM · susceptibility LightGBM
        ▼
 L6  RISK ENGINE       trigger T · susceptibility S · drain stress D → H ; E ; V → R, level, time-to-impact
        ▼
 L7  AGENTS            LangGraph: orchestrator ▸ data ▸ forecast ▸ risk ▸ RCA ▸ decision
        ▼
 L8  EXPLAIN + POLICY  Shapley attribution · evidence registry · narrative guard · YAML policy
        ▼
 L9  HUMAN GATE        review queue · approve / modify / reject · hash-chained audit
        ▼
 L10 ALERT·ROUTE·RESPONSE  alert manager · simulated gateway · route planner · shelters · resources
        ▼
 L11 APPLICATIONS      REST API · React dashboard (13 views) · citizen view
        ▲
 L12 LEARNING          outcomes → metrics → recalibrate / retrain → candidate model → human promotion
```

### 4.2 Layer responsibilities

| Layer | Responsibility | Python package / folder | Key technology |
| --- | --- | --- | --- |
| L1 Data sources | Authoritative inputs and the simulator | `ews.simulation`, `data/raw/` | GCC ArcGIS REST, OpenCity files, Open-Meteo, WorldPop, DEM, OSM |
| L2 Ingestion & validation | Pull or accept data, check schema and plausibility, set QC flags, upsert idempotently | `ews.ingest`, `ews.quality` | httpx, Pydantic, APScheduler |
| L3 Data platform | Durable storage, provenance, evidence snapshots | `ews.db`, `database/` | PostgreSQL 16 + PostGIS |
| L4 Geospatial processing | CRS handling, grid, terrain derivatives, zonal statistics, spatial joins | `ews.geo` | GeoPandas, rasterio, pysheds, PostGIS |
| L5 Forecasting / ML | Rainfall blend, water-level forecast, susceptibility, model registry | `ews.models` | LightGBM, scikit-learn |
| L6 Flood risk engine | Trigger, drain stress, hazard, exposure, vulnerability, risk, footprint, uncertainty | `ews.risk` | NumPy; pure functions |
| L7 Multi-agent intelligence | Orchestrated workflow, tool calls, contracts, abstention | `ews.agents` | LangGraph, Pydantic |
| L8 Explainability & policy | Attribution, evidence registry, narrative guard, rules | `ews.explain`, `ews.policy` | YAML rules |
| L9 Human oversight | Review queue, approvals, audit chain | `ews.oversight` | FastAPI, PostgreSQL |
| L10 Alerts / routing / response | Alert drafting and simulated dispatch, routes, shelters, resources | `ews.alerts`, `ews.routing`, `ews.response` | OSMnx, NetworkX, SMTP sandbox |
| L11 Applications | REST API and web UI | `ews.api`, `web/` | FastAPI, React, MapLibre |
| L12 Continuous learning | Outcome capture, metrics, recalibration, retraining, promotion | `ews.learning` | scikit-learn, LightGBM |

### 4.3 Physical architecture

```
 Laptop or single VM — Docker Compose
 ├─ db       postgis/postgis:16-3.4              :5432   volume pgdata
 ├─ api      FastAPI (uvicorn)                   :8000   mounts ./config ./models ./data
 ├─ worker   APScheduler: connectors · simulator · analysis cycle · learning jobs
 ├─ web      React build behind nginx            :8080   (dev: Vite :5173)
 ├─ mailpit  profile demo  SMTP :1025 · UI :8025         real SMTP, sandbox inbox
 ├─ ollama   profile llm   :11434                        optional local model
 └─ prometheus + grafana   profile obs                   optional
```

### 4.4 Software architecture

One repository, one Python package (`ews`), organised as a modular monolith. Rules that keep it testable:

- `ews.risk`, the model `predict` functions and `ews.explain.attribution` are **pure** (no database, no network).
- `ews.agents` call only typed wrappers in `ews.tools`; agents never write SQL.
- `ews.api` validates, authenticates and delegates to `ews.services`; it holds no business logic.
- Only `ews.ingest` (and the LLM adapter, and one-off data-build scripts) may touch the internet.
- Configuration is loaded once by `ews.config`; its hash is stored with every run.

### 4.5 Where every number and sentence comes from

| Output | Produced by | Type | LLM involved? |
| --- | --- | --- | --- |
| Rainfall forecast | Open-Meteo NWP blended with a persistence nowcast | Statistical / model output | No |
| Water-level forecast (+ interval) | LightGBM point and quantile models | ML | No |
| Susceptibility S | LightGBM on terrain/drainage/land-cover features | ML + geospatial | No |
| Trigger T, drain stress D | Ramp functions, SCS-CN runoff, sensor fill ratio | Deterministic | No |
| Hazard H, risk R, level, time-to-impact | Risk engine | Deterministic | No |
| Confidence | Formula over data quality, interval width, agreement | Deterministic | No |
| Contribution of each factor | Exact Shapley values over the risk formula | Deterministic | No |
| Similar historical events | Nearest neighbours on standardised event features | Statistical | No |
| Routes and safe-route score | Dijkstra on OSM graph with risk-weighted edges | Algorithm | No |
| Explanation text | Templates (default) or optional LLM paraphrase of structured facts, then validated | Text | Optional, fenced |
| Alert text | Pre-approved English and Tamil templates | Text | No |
| Workflow routing | Fixed LangGraph graph with rule-based conditional edges | Control flow | No |

### 4.6 Other architecture views

| View | Where it is specified |
| --- | --- |
| Data architecture | §6 (datasets), §7 (schema), §9 (pipeline) |
| AI architecture | §11, §12, §16, §17 |
| Geospatial architecture | §8 |
| Agent architecture | §13–§15 |
| Deployment architecture | §33 (MVP), §34 (production), §38 (deployment) |

### 4.7 Deliberate departures from the conceptual diagrams

The diagrams are accepted as requirements for behaviour (agents, human gate, evidence, learning loop). They are not accepted as a technology list.

| Diagram element | Decision | Reason |
| --- | --- | --- |
| Kafka / MQTT / Flink / Spark | HTTP ingestion + PostgreSQL + APScheduler | About 50 sensors and one city; brokers add failure modes without adding capability |
| Vector database, embeddings | Not used | “Similar events” is nearest-neighbour search on numeric event features |
| Feature store (Feast-style) | `feature_snapshots` rows referenced by evidence + Parquet files | Same auditability, no extra service |
| LLM-driven agents | Deterministic agents, fixed graph, LLM optional and fenced | Reproducibility; principle P2 |
| Kubernetes, ELK | Docker Compose, structured JSON logs | Single-machine MVP |
| Zone = Ward 112 as the example | Zones are real GCC wards chosen by the demo-area rule | The example label is illustrative |
| Risk = 0.4H + 0.3E + 0.3V | Same weights, but gated by hazard, with susceptibility inside H | Plain weighted sums let exposure and vulnerability alone produce a high score (§12.2) |
| Example figures (92 mm/hr, +18 cm in 10 min, 82 %, 87 % accuracy, IoU 0.76, 11,800 people) | Treated as illustrations only | They are not measured results. The conceptual example H 0.85, E 0.75, V 0.70 with weights 0.4/0.3/0.3 gives 0.775, not the 0.82 printed |
| Mobile app, WhatsApp, X, social media, IVRS | Responsive “citizen view” plus simulated gateway | No credentials, no DLT-style registrations, no partnerships in a hackathon |
| Knowledge graph updates | Tables, YAML rules and versioned documents | No graph database is needed to meet any stated requirement |

## 5. Technology Stack

### 5.1 Selection rule

A technology is selected only if (i) the team can run it on a laptop, (ii) it removes a named risk, (iii) it has a documented fallback and (iv) it has an upgrade path to production. Popularity is not a criterion. “Proto” = prototype complexity, “Prod” = production scalability.

| Component | Selected (MVP / Prod) | Why | Alternative considered → why not | Proto · Prod |
| --- | --- | --- | --- | --- |
| Language and API | Python 3.11+, FastAPI, Pydantic v2 (yes / yes) | One language for API, models, geospatial and agents; typed contracts shared by all layers; OpenAPI generated | Django REST (ORM and admin not needed, slower to iterate); Node/Express (splits ML code from API code) | Low · High |
| Database | PostgreSQL 16 + PostGIS 3.4 (yes / yes) | One store for relational, spatial and time-series data at MVP volume; SQL DDL is a deliverable | MongoDB (weak spatial joins); SQLite/SpatiaLite (concurrency, roles); separate GeoServer (extra service) | Low · High |
| Time series | Plain PostgreSQL tables with btree on (sensor\_id, observed\_at); TimescaleDB later (yes / later) | Under about 10 million rows in the MVP; one fewer extension; hypertable conversion is an in-place migration | TimescaleDB now (extra image and operations risk, no MVP benefit); InfluxDB (second database, no spatial joins) | Low · High |
| Object storage | Local `data/` volumes + SHA-256 manifest behind a `BlobStore` interface (yes / MinIO or S3) | Single machine; a manifest gives provenance without a service | MinIO (adds nothing on one box); cloud S3 (accounts, cost) | Low · High |
| Cache and queue | None. PostgreSQL + in-process APScheduler (yes / Redis only if measured) | Nothing in the MVP needs a shared sub-second cache; dashboard polling every 5–10 s is enough | Redis + Celery (two more services); RabbitMQ | Low · Medium |
| Messaging | HTTP ingestion endpoints now; Mosquitto MQTT as a stretch adapter; Kafka production-only (yes / MQTT, Kafka) | The same endpoint serves simulator and future gateways; no broker to babysit during a demo | Kafka cluster now (over-engineered for about 50 sensors); Redis Streams (extra service) | Low · High |
| Geospatial libraries | GeoPandas 1.x, Shapely 2, pyproj, rasterio, rioxarray + xarray, installed from wheels (yes / yes) | Covers vector, raster and CRS work; wheels avoid system GDAL builds | GDAL command line only (hard to test); ArcPy (licence) | Medium · High |
| Terrain hydrology | pysheds: fill depressions, resolve flats, D8 flow direction and accumulation, HAND (yes / yes) | Pure-Python wheels; the Chennai raster is small (about 1.9 million cells at 30 m with buffer) | WhiteboxTools (binary dependency); GRASS/QGIS processing (heavy); RichDEM (platform build issues) | Medium · Medium |
| GIS inspection | QGIS desktop, QA only (yes / n/a) | Visual check of every derived layer; not a runtime dependency | none needed | Low · n/a |
| Web map | MapLibre GL JS via react-map-gl (yes / yes) | Data-driven styling for about 200 wards and a 250 m grid; vector rendering; no access token | Leaflet (raster-centric, weaker data-driven styling); Mapbox GL (token and licence); deck.gl (only if heatmaps or 3D are needed) | Medium · High |
| Basemap | Configurable style URL (OSM-derived, for example OpenFreeMap or self-hosted tiles); offline fallback = ward and road GeoJSON on a blank background (yes / yes) | Demo survives without internet; check the provider's terms before use | Mapbox or Google tiles (keys, cost) | Low · Medium |
| Charts | Recharts (yes / yes) | Time series with threshold lines in React | Plotly (bundle size); ECharts (more configuration than needed) | Low · High |
| Frontend | React + Vite + TypeScript, Tailwind CSS + shadcn/ui, TanStack Query (yes / yes) | Client-side app, role-aware UI, fast iteration | Next.js (SSR unnecessary); Streamlit/Dash (limited map UX and approval workflow) | Medium · High |
| Classical ML | scikit-learn + LightGBM; SHAP only for the susceptibility model's offline report (yes / yes) | Strong on small tabular data; quantile objective for intervals; fast to train | XGBoost (equivalent; one boosted-tree library is enough); Random Forest only as a baseline | Low · High |
| Deep learning | GRU in a notebook as a comparison only; PyTorch if used (no / optional) | Honest model comparison without a runtime dependency | TensorFlow (second DL stack); ConvLSTM and Transformers (no data to justify them) | Medium · High |
| Hydrology / hydraulics | SCS Curve Number runoff + linear-reservoir routing + Manning capacity proxy, written in the repository (yes / replaced where data allow) | Deterministic, explainable, milliseconds per run, needs only data we have | HEC-RAS 2D (needs calibrated terrain and boundary conditions; long runs); SWMM/PySWMM (needs a connected pipe network with inverts and diameters; GCC fields are partial) | Low · Medium |
| Agent orchestration | LangGraph: fixed graph, conditional edges (yes / yes) | Explicit states and routing, drawable graph, checkpointing available | Plain state machine (no tooling); CrewAI, AutoGen, LangChain agents (LLM-driven control flow conflicts with P1 and P2) | Medium · High |
| LLM | Provider-agnostic adapter with `TemplateNarrator` (default, no LLM) and `OpenAICompatibleNarrator` (local Ollama endpoint or any hosted provider). Demo default: LLM off; optional local 7–9 B instruct model (yes / yes) | Zero marginal cost, works offline, no key in the repository; the fenced role needs little capability. Hosted pricing and free tiers were not verified for this manual and are not relied on | Hosted frontier API as a hard dependency (cost, keys, connectivity); fine-tuning (no data, no need) | Low · High |
| Routing | OSMnx graph + NetworkX with custom edge weights (yes / move to ORS, GraphHopper or pgRouting) | Dynamic flood penalties are a few lines; no extra service | OSRM (precomputed profile, awkward dynamic penalties); OpenRouteService or GraphHopper (heavy services or rate-limited hosts) | Medium · Medium |
| Containers | Docker + Compose (yes / Compose, then Kubernetes) | Reproducible laptop-to-VM deployment | Kubernetes now (operational weight, no MVP benefit); bare venv (environment drift) | Low · Medium |
| CI | GitHub Actions: lint, unit, integration (PostGIS service container), frontend build, image build (yes / yes) | Free for public repositories; matches the Git workflow | Jenkins, GitLab CI (extra setup) | Low · High |
| Observability | structlog JSON logs + prometheus-client `/metrics`; Prometheus and Grafana as an optional compose profile (yes / yes) | Auditable logs and key metrics without running a stack | ELK or Loki (services); full OpenTelemetry (later) | Low · High |
| Authentication | JWT (HS256) for users; hashed API keys for sensors and services (yes / Keycloak or Auth0) | Simple, testable RBAC | Keycloak or Auth0 now (setup cost) | Low · High |
| Scheduler | APScheduler inside the `worker` container (yes / yes) | In-process, no broker | Celery beat; cron (less visible to tests) | Low · Medium |
| Packaging | `uv` with `pyproject.toml` and a lock file (yes / yes) | Fast, reproducible installs | Poetry, pip-tools, conda (heavier) | Low · High |
| Code quality | ruff (lint and format); mypy on `ews.risk`, `ews.agents`, `ews.api` (yes / yes) | Catches contract errors early | pylint, flake8, black stack | Low · High |
| Testing | pytest with markers (unit, integration, geo, model, agent, sim, e2e); Hypothesis for monotonicity properties; one Playwright smoke test (yes / yes) | Layers map to §31 | unittest; Selenium | Low · High |
| Alert email | Mailpit sandbox (SMTP 1025, UI 8025) (yes / real SMTP provider) | Real SMTP path, no real recipients | Real provider now (cost, spam rules); MailHog (largely unmaintained) | Low · Medium |
| SMS, IVRS, push | `SimulatedGateway` implementing `NotificationGateway` (yes / real providers) | No registrations needed; real providers plug in later | Real SMS API now (needs sender and template registration) | Low · High |
| Dataset versioning | `data/MANIFEST.yaml`: source URL, retrieval date, licence, CRS, SHA-256; DVC later (yes / DVC) | Provenance without a tool | DVC or lakeFS now (learning curve) | Low · High |
| Experiment tracking and registry | `model_versions` table + `runs/*.jsonl` + artifact folder; MLflow in production (yes / MLflow) | Auditable and sufficient for three models | MLflow now (another service) | Low · High |

### 5.2 FINAL RECOMMENDED STACK

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 Core with psycopg 3 (synchronous), httpx, APScheduler, structlog. Spatial columns are handled with plain SQL (`ST_Transform`, `ST_AsGeoJSON`); no ORM mapping of geometry types.
- **Data:** PostgreSQL 16 + PostGIS 3.4 in plain tables; numbered SQL migrations applied by a small runner; files under `data/` with a checksum manifest.
- **Geospatial:** GeoPandas, Shapely 2, pyproj, rasterio, rioxarray/xarray, pysheds, osmnx, networkx.
- **ML:** scikit-learn, LightGBM, joblib, Hypothesis; SHAP offline only.
- **Agents:** LangGraph, Pydantic contracts, LLM adapter (off by default).
- **Frontend:** React, Vite, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, MapLibre GL JS, Recharts.
- **Operations:** Docker Compose, GitHub Actions, Mailpit; optional Ollama and Prometheus/Grafana profiles.
- **Versions:** pin exact versions at repository initialisation (lock files committed) and upgrade only for security fixes during the build.

Evaluated and **not selected** for the MVP: HEC-RAS, SWMM, Kafka, Redis, MinIO, Mapbox, TensorFlow, Transformers, ConvLSTM, Next.js, OSRM, OpenRouteService, GraphHopper, Kubernetes, a vector database. Section 41 lists what must not be built and why.

## 6. Data Architecture

### 6.1 Rules

1. **Raw is immutable.** Downloads go to `data/raw/<id>/<retrieval-date>/`; processing writes to `data/processed/` and to PostGIS. Raw files are never edited.
2. **Every dataset has provenance.** One row in `data_sources` and one entry in `data/MANIFEST.yaml` (source URL, retrieval date, version, licence, CRS, row count, SHA-256, verification status).
3. **Simulated data is flagged at the source row** (`is_simulated`), not only in documentation.
4. **As-of semantics.** Observations carry `observed_at`; forecasts carry `issued_at` and `valid_at`; features are always computed as of a timestamp. This is the basis of the leakage rules in §6.5.
5. **Licences are tracked.** OSM is ODbL; Open-Meteo free tier is non-commercial with attribution; GCC and OpenCity licences must be confirmed per layer before redistribution.

Manifest entry (YAML):

```
- id: gcc_swd
  name: GCC storm-water drains (layer 8)
  url: https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/GCC_COLLABORATION_LAYER/MapServer/8
  retrieved_at: 2026-10-09T10:00:00Z
  licence: UNKNOWN - confirm with GCC or OpenCity before redistribution
  crs: EPSG:32644
  rows: null            # filled by the ingestion script
  sha256: null
  status: VERIFIED_FIELDS_ONLY
```

### 6.2 Dataset registry

Status tags: \[VERIFIED\] live check on 9 Oct 2026; \[TEAM DOC\] not re-verified; \[SIM\] simulated. Storage is PostGIS unless stated.

| ID · Dataset | Source and access | Raw → processed | Update | Validation | Transformation · CRS · time | Derived features |
| --- | --- | --- | --- | --- | --- | --- |
| D01 GCC wards | ArcGIS `MapServer/6/query`, f=geojson, `outSR=32644`, paged at 2,000 \[VERIFIED\]. Fields: `pro_z_no`, `pro_ward_n` (numeric), area, perimeter | GeoJSON → GeoPackage → `zones` | Static; re-pull quarterly | Valid polygons; no duplicate ward numbers; area within 5 % of `st_area(shape)` | `make_valid`; cast numbers to int; stay in 32644 | area, centroid, neighbours |
| D02 GCC zones | `MapServer/7` \[VERIFIED layer; fields to profile\] | as D01 → `zones` (level GCC\_ZONE) | Static | 15 zones expected \[TEAM DOC\] | Link wards to zones by zone number | none |
| D03 GCC storm-water drains | `MapServer/8` \[VERIFIED fields\]: zone, ward, location, drain\_type, cover, drain\_len, drain\_wid, drain\_dep, drain\_size, water\_flow, status, invert\_sp, invert\_ep, obstacles, start/end easting-northing, dlen\_km. Most are text fields | Paged GeoJSON → cleaned GeoPackage → `drainage_edges`, `drainage_nodes` | Static | Count per ward; percentage of rows with parseable width, depth and inverts; length vs `dlen_km` | Parse numbers (strip units, handle NA); snap end points within 2 m to make nodes; flow direction from invert\_sp to invert\_ep when both are valid | drain density, nearest-drain distance, Manning capacity proxy, obstacle flags |
| D04 GCC buildings | `MapServer/4` \[VERIFIED\]: ward\_number, zone\_number, locality, area\_name; no use or height field | City-wide counts per ward through `outStatistics`; polygons paged for the demo cluster only → `buildings` | Static | Valid polygons; counts sanity-checked against WorldPop | Counts and footprint area per cell | building count, built-up area |
| D05 GCC vehicular subways | `MapServer/5` \[VERIFIED\]: road\_name, locality, category, road\_id | → `roads.is_underpass`, `critical_facilities` (kind SUBWAY) | Static | Snap to road graph within 15 m | Underpasses receive a flood penalty (§20) | underpass flag per edge |
| D06 GCC river and bridges | `MapServer/1` and `/0` \[VERIFIED layers; fields not inspected\] | → waterbody lines, bridge flags | Static | Valid lines | none | distance to river |
| D07 GCC centre line, carriageway | `MapServer/2` and `/3` \[VERIFIED layers\] | QA overlay only in the MVP | Static | none | Compare with OSM coverage | none |
| D08 DEM | Copernicus DEM GLO-30 (access conditions changed in 2026 \[TEAM DOC\]); fallback SRTM 30 m, then GLO-90 | GeoTIFF tiles → clipped, reprojected 30 m GeoTIFF in 32644 (file) | Static | Voids filled; elevation range plausible; cross-check with a second DEM | Bilinear reprojection; depression handling in §8 | elevation, slope, TWI, flow accumulation, sink depth, HAND |
| D09 Population | WorldPop India 100 m, 2025 total and age-sex bands \[TEAM DOC\] | GeoTIFF → clipped → cell and ward sums → `population_grids` | Annual | Non-negative; city total plausible against census scale | Zonal **sum**, never mean | population, vulnerable-age fraction (0–4 and 65+) if bands exist |
| D10 Land cover | ESA WorldCover 2021, 10 m \[TEAM DOC\] | GeoTIFF → class fractions per cell → `terrain_features` | Static | Valid class codes | Categorical resampling (nearest or majority) | built-up, tree, water fractions |
| D11 OSM roads and facilities | OSMnx / Overpass for the GCC polygon plus buffer \[TEAM DOC\] | GraphML + GeoPackage → `roads`, `critical_facilities`; file `chennai_drive.graphml` | Monthly | Largest strongly connected component holds at least 95 % of nodes; deduplicated facilities | Simplify graph; edge length in metres in 32644; speeds from `maxspeed` or class defaults | road length per cell, facility counts, nearest facility |
| D12 OpenCity flood layers | KML: inundation points with depth, 2015 points, hazard zones by return period, 2005 and 2020 events \[TEAM DOC\] | KML → GeoJSON → `historical_flood_events`, `flood_extents` | Static | Inspect each layer for geometry type, date, depth unit (inches) | Inches to cm; reproject; keep per-feature provenance | historical flood frequency, event labels, event features |
| D13 Shelters, relief centres | OpenCity, GCC source \[TEAM DOC\] | CSV or KML → `shelters` | Static | Inside GCC; capacity may be null and is never imputed | Reproject; deduplicate | shelter distance, access gap |
| D14 Chennai daily rainfall | OpenCity, IMD-derived \[TEAM DOC\] | CSV → `rainfall_observations` (interval P1D) | Static | Missing (-999) → null; non-negative; IMD day taken as 24 h ending 08:30 IST \[ASSUMPTION: verify product note\] | Convert to UTC intervals | climatology percentiles, antecedent sums |
| D15 IMD gridded rainfall | `imdlib` package, IMD Pune, 0.25° daily \[TEAM DOC\] | binary → xarray → daily CSV for nearby cells | Annual | Cross-check against D14 | Nearest cell to ward centroids | bias anchor for hourly shape |
| D16 Open-Meteo archive | `archive-api.open-meteo.com/v1/archive`, hourly, ERA5-based, from 1940; keyless, non-commercial, attribution \[VERIFIED\] | JSON → Parquet → `rainfall_observations` (kind REANALYSIS, P1H) | On demand | Non-negative; request `timezone=UTC` | Scale hourly shape so daily totals match D14/D15 \[ASSUMPTION: prototype bias correction\] | hyetographs, R60, R180, A72 |
| D17 Open-Meteo forecast | `api.open-meteo.com/v1/forecast`, hourly NWP, same terms \[VERIFIED\] | JSON → `rainfall_forecasts` | Hourly pull | Valid time after issue time; reject stale pulls | One request with all ward centroids; UTC | F60, F180, anomaly vs climatology |
| D18 NASA GPM IMERG | Earthdata and PPS registration, 0.1°, 30 min \[TEAM DOC\] | HDF5/NetCDF → clipped → `rainfall_observations` (SATELLITE\_ESTIMATE) | Optional (Early run about 4 h latency) | Unit mm per hour; half-hour start timestamps in UTC \[verify\] | optional | optional sub-hourly sums |
| D19 Simulated rain gauges | `ews.simulation` \[SIM\] | API → `rainfall_observations` (SIM\_GAUGE) | Per scenario | Same validators as real data | Spatial noise on a replayed series | none |
| D20 Simulated drain sensors | `ews.simulation` \[SIM\] | API → `water_level_observations` (`is_simulated`) | 1 min of simulated time | QC flags (§9) | none | rise rate, fill ratio, acceleration |
| D21 CWC / India-WRIS gauges | Portal, access-dependent \[TEAM DOC\] | Manual CSV only | Optional | Not on the critical path | none | upstream context |
| D22 Tide | Simulated sinusoid in the simulator; any real source (INCOIS) unverified \[TEAM DOC\] | none | none | none | none | tide factor on outflow |
| D23 Emergency resources | Simulated inventory \[SIM\] | YAML → `emergency_resources` | Static | none | none | none |

### 6.3 Schema index

The full DDL is in §7. This index shows which table carries which entity.

| Entity | Tables | Key columns | Space and time |
| --- | --- | --- | --- |
| Rainfall | `stations`, `rainfall_observations` | station\_id, observed\_at, interval, depth\_mm, kind | UTC; interval start and end |
| Weather forecast | `rainfall_forecasts` | station\_id, issued\_at, valid\_at, depth\_mm, model | UTC; issue vs valid time |
| Water level and sensor | `water_level_sensors`, `water_level_observations` | sensor\_id, observed\_at, level\_cm, qc\_flags | SRID 32644; UTC |
| Terrain | `grid_cells`, `terrain_features` | cell\_id, elevation, slope, twi, hand | 250 m cells |
| Drainage | `drainage_nodes`, `drainage_edges` | node\_id, edge\_id, width, depth, inverts | SRID 32644 |
| Flood event and extent | `historical_flood_events`, `flood_extents` | event\_id, extent\_id, geom, depth\_cm | SRID 32644; UTC dates |
| Roads, buildings | `roads`, `buildings` | road\_id, building\_id, is\_underpass | SRID 32644 |
| Population | `population_grids` | cell\_id, pop\_total, vuln\_frac | per cell |
| Shelters, hospitals, critical infrastructure | `shelters`, `critical_facilities` | shelter\_id, facility\_id, kind, capacity (nullable) | SRID 32644 |
| Risk zones | `zones`, `zone_static_features` | zone\_id | SRID 32644 |
| Risk, explanation | `risk_predictions`, `risk_factors`, `evidence_items`, `explanations` | risk\_id, evidence\_id | UTC |
| Alerts, actions, review | `alerts`, `alert_recipients`, `recommended_actions`, `human_reviews`, `response_actions`, `evacuation_routes` | alert\_id, action\_id | UTC |
| Outcomes and learning | `prediction_outcomes`, `feedback`, `model_versions` | prediction key, model\_id | UTC |

### 6.4 Where the source documents disagree, and the resolution used here

| Topic | Disagreement | Resolution in this manual |
| --- | --- | --- |
| DEM access | Grok: Copernicus GLO-30 is available from a public cloud bucket without sign-in. Dataset report: GLO-30 access conditions changed in 2026 | Try the public bucket first; fall back to SRTM 30 m, then GLO-90; decided by the Phase 1 probe |
| Drain attributes | Grok: capacity and condition are generally not published. The live GCC drain layer has width, depth, invert, status and obstacle fields \[VERIFIED fields\] | Treat the fields as present but possibly sparse; measure completeness in Phase 1; use the Manning proxy only where complete |
| Drain coverage | Grok: SWD KML covers 114+ wards. Gemini: 10,308 drain segments across the wards \[TEAM DOC\] | Count per ward from the live layer; the demo-area rule (§2.4) requires coverage |
| Shelter capacity | Gemini: capacities are mapped per ward. Grok: capacity frequently missing | Capacity is nullable; unknown capacity is shown as unknown, never estimated |
| Demo ward | Gemini: Ward 112 (because the diagrams mention it). Grok: Velachery–Pallikaranai–Adyar corridor | Data-driven demo-area rule (§2.4) |
| Flood labels | Gemini: Global Flood Database covers 2015 and 2023. Dataset report: GFD v1 covers 2000–2018 | 2023 labels need another source (for example Sentinel-1 processing); not assumed available |
| Forecast horizon | Proposal: 15–120 minutes. Grok: public data realistically supports 3–24 h forecasts without radar | Risk is evaluated at 15-minute steps to 120 minutes using sensor dynamics, simulated gauges and hourly NWP; no 15-minute rainfall-nowcast skill is claimed |
| Tide | Both guidebooks mention an INCOIS tide API; its existence is unverified | Tide is a simulator driver only; any real feed is optional |
| IMD API portal | Grok mentions a registration-based IMD API portal | Not used; unverified |
| 2015 radar archive | Gemini: archived 2015 radar could replay a live feed | Not used; unverified |

### 6.5 Training, validation and runtime separation

| Purpose | Data | Rules |
| --- | --- | --- |
| Train susceptibility (M1) | Terrain, drainage and land-cover features against historical flood labels | Spatial block cross-validation; the replayed event is excluded from training whenever it is used for evaluation |
| Train water-level forecaster (M3) | Simulated storms | Split by storm, never by row; test on a different simulator parameter range (§11) |
| Calibrate trigger T | IMD daily and ERA5-based hourly series for flood and non-flood heavy-rain days | Hold out whole events |
| Backtest | Event layers (2005, 2015, 2020 where usable) | Leave one event out; report per-event results |
| Runtime | Latest observations, forecasts, sensor stream, static layers | Never use data with `observed_at` or `valid_at` later than the analysis time; stale data lowers confidence |

Leakage controls: forecasts are joined by `issued_at <= analysis_time`; post-event polygons are never used before the event end date; the same event never appears in both training and test; spatial neighbours of test cells are excluded from training folds.

## 7. Database Specification

### 7.1 Conventions

- PostgreSQL 16 with PostGIS 3.4. Every geometry column is typed `geometry(Type,32644)`; the type modifier enforces the SRID and gives the guarantee P8 asks for (a test fails if any geometry column has no type modifier).
- Time: `timestamptz` only. Rainfall observations use `period_start` / `period_end`; the “observed\_at” of a rainfall record is `period_end`.
- Enumerations are `text` with `CHECK` constraints (cheap to migrate). Runtime entities use `uuid` keys; reference data uses natural text keys (`zone_id` = `WARD-112`) or integers.
- Zone IDs: `WARD-<ward_no>` and `GCC-ZONE-<zone_no>`, zero-padded to three and two digits.
- Migrations are numbered SQL files applied in order by `scripts/migrate.py`; the DDL below is split into those files.
- Nullable means “unknown”, never “zero”. Shelter capacity, drain width and rainfall gaps are nullable on purpose.

### 7.2 DDL

**001\_core.sql**

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE data_sources (
  source_id    text PRIMARY KEY,
  name         text NOT NULL,
  url          text,
  licence      text,
  version      text,
  retrieved_at timestamptz,
  crs          text,
  row_count    bigint,
  sha256       text,
  status       text NOT NULL CHECK (status IN ('VERIFIED','VERIFIED_FIELDS_ONLY','TEAM_DOC','SIMULATED','FAILED_PROBE')),
  notes        text
);

CREATE TABLE users (
  user_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text UNIQUE NOT NULL,
  display_name  text NOT NULL,
  role          text NOT NULL CHECK (role IN ('CITIZEN','MUNICIPAL_OPERATOR','EMERGENCY_COORDINATOR','ADMIN','RESEARCHER','SYSTEM_SERVICE')),
  password_hash text,
  api_key_hash  text,
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE model_versions (
  model_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                  text NOT NULL,
  version               text NOT NULL,
  kind                  text NOT NULL CHECK (kind IN ('ML','RULESET','CALIBRATION')),
  status                text NOT NULL CHECK (status IN ('CANDIDATE','ACTIVE','RETIRED','REJECTED')),
  artifact_path         text,
  artifact_sha256       text,
  dataset_manifest_hash text,
  git_sha               text,
  params                jsonb NOT NULL DEFAULT '{}',
  metrics               jsonb NOT NULL DEFAULT '{}',
  trained_on_simulated  boolean NOT NULL DEFAULT false,
  created_at            timestamptz NOT NULL DEFAULT now(),
  promoted_by           uuid REFERENCES users(user_id),
  promoted_at           timestamptz,
  UNIQUE (name, version)
);
CREATE UNIQUE INDEX one_active_model_per_name ON model_versions (name) WHERE status = 'ACTIVE';

CREATE TABLE sim_runs (
  scenario_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id     text NOT NULL,
  seed            integer NOT NULL,
  speed           real NOT NULL DEFAULT 1,
  sim_start       timestamptz NOT NULL,
  sim_clock       timestamptz,
  status          text NOT NULL CHECK (status IN ('PENDING','RUNNING','PAUSED','STOPPED','COMPLETED','FAILED')),
  params          jsonb NOT NULL DEFAULT '{}',
  started_by      uuid REFERENCES users(user_id),
  created_at      timestamptz NOT NULL DEFAULT now()
);
```

**002\_geo.sql**

```sql
CREATE TABLE zones (
  zone_id        text PRIMARY KEY,
  level          text NOT NULL CHECK (level IN ('WARD','GCC_ZONE')),
  ward_no        integer,
  gcc_zone_no    integer,
  name           text,
  parent_zone_id text REFERENCES zones(zone_id),
  area_km2       double precision,
  geom           geometry(MultiPolygon,32644) NOT NULL,
  centroid       geometry(Point,32644) NOT NULL,
  in_demo_aoi    boolean NOT NULL DEFAULT false,
  source_id      text REFERENCES data_sources(source_id),
  UNIQUE NULLS NOT DISTINCT (level, ward_no, gcc_zone_no)
);
CREATE INDEX zones_geom_gix ON zones USING gist (geom);

CREATE TABLE grid_cells (
  cell_id  integer PRIMARY KEY,
  ix       integer NOT NULL,
  iy       integer NOT NULL,
  zone_id  text NOT NULL REFERENCES zones(zone_id),
  geom     geometry(Polygon,32644) NOT NULL,
  centroid geometry(Point,32644) NOT NULL,
  UNIQUE (ix, iy)
);
CREATE INDEX grid_cells_geom_gix ON grid_cells USING gist (geom);
CREATE INDEX grid_cells_zone_idx ON grid_cells (zone_id);

CREATE TABLE terrain_features (
  cell_id                  integer PRIMARY KEY REFERENCES grid_cells(cell_id),
  elev_mean_m real, elev_min_m real, elev_p10_m real,
  slope_deg real, twi real, flow_acc_cells real, sink_depth_m real, hand_m real,
  dist_drain_m real, dist_river_m real,
  built_frac real CHECK (built_frac BETWEEN 0 AND 1),
  tree_frac real, water_frac real,
  drain_density_m_km2 real, drain_capacity_proxy_m3s real,
  building_count integer, road_length_m real,
  hist_flood_freq real,
  susceptibility real CHECK (susceptibility BETWEEN 0 AND 1),
  susceptibility_model_id uuid REFERENCES model_versions(model_id),
  feature_version text NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE zone_static_features (
  zone_id text PRIMARY KEY REFERENCES zones(zone_id),
  s_mean real, s_p90 real, s_ward real,
  elev_mean_m real, built_frac real, drain_density_m_km2 real,
  drain_capacity_index real, swd_coverage_frac real, hist_flood_freq real,
  pop_total integer, pop_vulnerable_frac real,
  building_count integer, road_length_km real,
  n_hospitals integer, n_schools integer, n_critical integer, n_shelters integer,
  dist_nearest_shelter_m real,
  exposure_score real CHECK (exposure_score BETWEEN 0 AND 1),
  vulnerability_score real CHECK (vulnerability_score BETWEEN 0 AND 1),
  feature_version text NOT NULL,
  computed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE drainage_nodes (
  node_id bigint PRIMARY KEY,
  kind    text NOT NULL DEFAULT 'JUNCTION' CHECK (kind IN ('JUNCTION','OUTFALL','INLET','UNKNOWN')),
  zone_id text REFERENCES zones(zone_id),
  geom    geometry(Point,32644) NOT NULL
);
CREATE INDEX drainage_nodes_gix ON drainage_nodes USING gist (geom);

CREATE TABLE drainage_edges (
  edge_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  gcc_objectid       bigint,
  source_node        bigint REFERENCES drainage_nodes(node_id),
  target_node        bigint REFERENCES drainage_nodes(node_id),
  zone_id            text REFERENCES zones(zone_id),
  drain_type         text,
  width_m            real,
  depth_m            real,
  invert_start_m     real,
  invert_end_m       real,
  length_m           real NOT NULL,
  status             text,
  obstacles          text,
  capacity_proxy_m3s real,
  attrs_complete     boolean NOT NULL DEFAULT false,
  raw_attrs          jsonb NOT NULL DEFAULT '{}',
  geom               geometry(LineString,32644) NOT NULL
);
CREATE INDEX drainage_edges_gix ON drainage_edges USING gist (geom);
CREATE INDEX drainage_edges_zone_idx ON drainage_edges (zone_id);

CREATE TABLE roads (
  road_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  osm_way_ids  bigint[],
  u_node       bigint NOT NULL,
  v_node       bigint NOT NULL,
  edge_key     integer NOT NULL DEFAULT 0,
  name         text,
  highway      text,
  oneway       boolean,
  maxspeed_kph real,
  length_m     real NOT NULL,
  is_underpass boolean NOT NULL DEFAULT false,
  is_bridge    boolean NOT NULL DEFAULT false,
  zone_id      text REFERENCES zones(zone_id),
  geom         geometry(LineString,32644) NOT NULL,
  UNIQUE (u_node, v_node, edge_key)
);
CREATE INDEX roads_gix ON roads USING gist (geom);

CREATE TABLE buildings (
  building_id bigint PRIMARY KEY,
  gcc_gis_id  text,
  zone_id     text REFERENCES zones(zone_id),
  area_m2     real,
  geom        geometry(MultiPolygon,32644) NOT NULL
);
CREATE INDEX buildings_gix ON buildings USING gist (geom);
CREATE INDEX buildings_zone_idx ON buildings (zone_id);

CREATE TABLE population_grids (
  cell_id      integer NOT NULL REFERENCES grid_cells(cell_id),
  vintage_year smallint NOT NULL,
  pop_total    real NOT NULL CHECK (pop_total >= 0),
  pop_age_0_4  real,
  pop_age_65p  real,
  source_id    text REFERENCES data_sources(source_id),
  PRIMARY KEY (cell_id, vintage_year)
);

CREATE TABLE critical_facilities (
  facility_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kind        text NOT NULL CHECK (kind IN ('HOSPITAL','CLINIC','SCHOOL','FIRE_STATION','POLICE','POWER','WATER','SUBWAY','OTHER')),
  name        text,
  osm_id      bigint,
  zone_id     text REFERENCES zones(zone_id),
  geom        geometry(Point,32644) NOT NULL,
  source_id   text REFERENCES data_sources(source_id)
);
CREATE INDEX facilities_gix ON critical_facilities USING gist (geom);
CREATE INDEX facilities_kind_idx ON critical_facilities (kind);

CREATE TABLE shelters (
  shelter_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        text NOT NULL,
  zone_id     text REFERENCES zones(zone_id),
  geom        geometry(Point,32644) NOT NULL,
  capacity    integer CHECK (capacity IS NULL OR capacity >= 0),
  is_official boolean NOT NULL DEFAULT true,
  status      text NOT NULL DEFAULT 'UNKNOWN' CHECK (status IN ('OPEN','CLOSED','FULL','UNKNOWN')),
  source_id   text REFERENCES data_sources(source_id)
);
CREATE INDEX shelters_gix ON shelters USING gist (geom);

CREATE TABLE historical_flood_events (
  event_id         text PRIMARY KEY,
  name             text NOT NULL,
  start_date       date,
  end_date         date,
  trigger          text,
  peak_rain_mm_24h real,
  label_quality    text CHECK (label_quality IN ('OBSERVED_POINTS','OBSERVED_POLYGON','MODELLED_ZONE','SAR_DERIVED','UNKNOWN')),
  source_id        text REFERENCES data_sources(source_id),
  notes            text
);

CREATE TABLE flood_extents (
  extent_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id         text NOT NULL REFERENCES historical_flood_events(event_id),
  geom_type        text NOT NULL CHECK (geom_type IN ('POINT','POLYGON')),
  geom             geometry(Geometry,32644) NOT NULL,
  depth_cm         real,
  return_period_yr integer,
  hazard_class     text CHECK (hazard_class IN ('HIGH','MODERATE','LOW')),
  source_id        text REFERENCES data_sources(source_id)
);
CREATE INDEX flood_extents_gix ON flood_extents USING gist (geom);
CREATE INDEX flood_extents_event_idx ON flood_extents (event_id);

CREATE TABLE event_features (
  event_id text NOT NULL REFERENCES historical_flood_events(event_id),
  zone_id  text NOT NULL REFERENCES zones(zone_id),
  rain_max_1h_mm real, rain_max_3h_mm real, rain_24h_mm real, antecedent_72h_mm real,
  flooded_frac real CHECK (flooded_frac BETWEEN 0 AND 1),
  label_flooded boolean,
  PRIMARY KEY (event_id, zone_id)
);
```

**003\_observations.sql**

```sql
CREATE TABLE stations (
  station_id   text PRIMARY KEY,
  kind         text NOT NULL CHECK (kind IN ('RAIN_GAUGE_SIM','IMD_GRID','NWP_POINT','SATELLITE_GRID','CITY_SERIES')),
  name         text,
  zone_id      text REFERENCES zones(zone_id),
  geom         geometry(Point,32644),
  is_simulated boolean NOT NULL DEFAULT false,
  source_id    text REFERENCES data_sources(source_id)
);
CREATE INDEX stations_gix ON stations USING gist (geom);

CREATE TABLE rainfall_observations (
  obs_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  station_id      text NOT NULL REFERENCES stations(station_id),
  period_start    timestamptz NOT NULL,
  period_end      timestamptz NOT NULL,
  depth_mm        real CHECK (depth_mm IS NULL OR depth_mm >= 0),
  kind            text NOT NULL CHECK (kind IN ('GAUGE','SIM_GAUGE','REANALYSIS','NWP_ANALYSIS','SATELLITE_ESTIMATE','CITY_DAILY','GRIDDED_DAILY')),
  qc_flags        text[] NOT NULL DEFAULT '{}',
  quality         real CHECK (quality BETWEEN 0 AND 1),
  is_simulated    boolean NOT NULL DEFAULT false,
  source_id       text REFERENCES data_sources(source_id),
  scenario_run_id uuid REFERENCES sim_runs(scenario_run_id),
  received_at     timestamptz NOT NULL DEFAULT now(),
  CHECK (period_end > period_start),
  UNIQUE (station_id, period_start, period_end, kind)
);
CREATE INDEX rain_obs_idx ON rainfall_observations (station_id, period_end DESC);

CREATE TABLE rainfall_forecasts (
  fc_id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  station_id      text NOT NULL REFERENCES stations(station_id),
  model           text NOT NULL,
  issued_at       timestamptz NOT NULL,
  valid_start     timestamptz NOT NULL,
  valid_end       timestamptz NOT NULL,
  depth_mm        real CHECK (depth_mm IS NULL OR depth_mm >= 0),
  is_simulated    boolean NOT NULL DEFAULT false,
  source_id       text REFERENCES data_sources(source_id),
  scenario_run_id uuid REFERENCES sim_runs(scenario_run_id),
  CHECK (valid_end > valid_start AND valid_start >= issued_at - interval '1 hour'),
  UNIQUE (station_id, model, issued_at, valid_start)
);
CREATE INDEX rain_fc_idx ON rainfall_forecasts (station_id, issued_at DESC, valid_start);

CREATE TABLE water_level_sensors (
  sensor_id      text PRIMARY KEY,
  drain_edge_id  bigint REFERENCES drainage_edges(edge_id),
  zone_id        text NOT NULL REFERENCES zones(zone_id),
  geom           geometry(Point,32644) NOT NULL,
  drain_depth_cm real NOT NULL CHECK (drain_depth_cm > 0),
  depth_source   text NOT NULL CHECK (depth_source IN ('GCC_ATTRIBUTE','CLASS_DEFAULT','ASSUMPTION')),
  warning_cm     real NOT NULL,
  critical_cm    real NOT NULL,
  is_simulated   boolean NOT NULL DEFAULT true,
  status         text NOT NULL DEFAULT 'OK' CHECK (status IN ('OK','DEGRADED','STUCK','OFFLINE','LOW_BATTERY','ANOMALY')),
  installed_at   timestamptz,
  api_key_hash   text,
  attrs          jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX sensors_gix ON water_level_sensors USING gist (geom);
CREATE INDEX sensors_zone_idx ON water_level_sensors (zone_id);

CREATE TABLE water_level_observations (
  obs_id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sensor_id        text NOT NULL REFERENCES water_level_sensors(sensor_id),
  observed_at      timestamptz NOT NULL,
  received_at      timestamptz NOT NULL DEFAULT now(),
  level_cm         real,
  rise_rate_cm_min real,
  battery_pct      real CHECK (battery_pct BETWEEN 0 AND 100),
  signal_dbm       real,
  device_status    text,
  qc_flags         text[] NOT NULL DEFAULT '{}',
  quality          real CHECK (quality BETWEEN 0 AND 1),
  is_simulated     boolean NOT NULL DEFAULT false,
  scenario_run_id  uuid REFERENCES sim_runs(scenario_run_id),
  UNIQUE (sensor_id, observed_at)
);
CREATE INDEX wl_obs_idx ON water_level_observations (sensor_id, observed_at DESC);
```

**004\_risk.sql**

```sql
CREATE TABLE agent_runs (
  run_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trigger         text NOT NULL CHECK (trigger IN ('SCHEDULE','INGEST_EVENT','MANUAL','SIMULATION')),
  as_of           timestamptz NOT NULL,
  scenario_run_id uuid REFERENCES sim_runs(scenario_run_id),
  config_hash     text NOT NULL,
  status          text NOT NULL CHECK (status IN ('RUNNING','COMPLETED','ABSTAINED','FAILED')),
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz,
  trace           jsonb NOT NULL DEFAULT '[]',
  error           text
);

CREATE TABLE risk_predictions (
  risk_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id             uuid NOT NULL REFERENCES agent_runs(run_id),
  zone_id            text NOT NULL REFERENCES zones(zone_id),
  as_of              timestamptz NOT NULL,
  horizon_min        smallint NOT NULL CHECK (horizon_min BETWEEN 0 AND 120),
  state              text NOT NULL CHECK (state IN ('ASSESSED','INSUFFICIENT_EVIDENCE')),
  hazard_h           real CHECK (hazard_h BETWEEN 0 AND 1),
  exposure_e         real CHECK (exposure_e BETWEEN 0 AND 1),
  vulnerability_v    real CHECK (vulnerability_v BETWEEN 0 AND 1),
  risk_score         real CHECK (risk_score BETWEEN 0 AND 1),
  risk_level         text CHECK (risk_level IN ('LOW','MEDIUM','HIGH','VERY_HIGH')),
  h_p10 real, h_p90 real,
  time_to_impact_min smallint,
  confidence         real CHECK (confidence BETWEEN 0 AND 1),
  confidence_level   text CHECK (confidence_level IN ('HIGH','MEDIUM','LOW')),
  data_quality       real CHECK (data_quality BETWEEN 0 AND 1),
  calibration_status text NOT NULL DEFAULT 'UNCALIBRATED' CHECK (calibration_status IN ('UNCALIBRATED','HINDCAST_CALIBRATED','OUTCOME_CALIBRATED')),
  evidence_tier      text CHECK (evidence_tier IN ('R','S','E','MIXED')),
  uses_simulated_inputs boolean NOT NULL DEFAULT false,
  impact_estimate    jsonb,
  footprint_cell_ids integer[],
  config_hash        text NOT NULL,
  model_ids          uuid[] NOT NULL DEFAULT '{}',
  created_at         timestamptz NOT NULL DEFAULT now(),
  CHECK (state = 'INSUFFICIENT_EVIDENCE' OR (risk_score IS NOT NULL AND risk_level IS NOT NULL))
);
CREATE INDEX risk_zone_time_idx ON risk_predictions (zone_id, as_of DESC, horizon_min);
CREATE INDEX risk_run_idx ON risk_predictions (run_id);

CREATE TABLE risk_factors (
  factor_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  risk_id          uuid NOT NULL REFERENCES risk_predictions(risk_id) ON DELETE CASCADE,
  factor_key       text NOT NULL,
  value            double precision,
  unit             text,
  normalised       real,
  shapley_value    real,
  contribution_pct real,
  direction        text CHECK (direction IN ('INCREASES','DECREASES','NEUTRAL')),
  rank             smallint NOT NULL,
  evidence_ids     text[] NOT NULL DEFAULT '{}'
);
CREATE INDEX risk_factors_risk_idx ON risk_factors (risk_id);

CREATE TABLE evidence_items (
  evidence_id   text PRIMARY KEY,
  run_id        uuid NOT NULL REFERENCES agent_runs(run_id),
  zone_id       text REFERENCES zones(zone_id),
  evidence_type text NOT NULL CHECK (evidence_type IN ('RAINFALL','FORECAST','WATER_LEVEL','TERRAIN','DRAINAGE','HISTORICAL_EVENT','EXPOSURE','MODEL_OUTPUT','CONFIG')),
  observed_at   timestamptz,
  value         jsonb NOT NULL,
  source_table  text NOT NULL,
  source_keys   jsonb NOT NULL,
  quality       real CHECK (quality BETWEEN 0 AND 1),
  is_simulated  boolean NOT NULL DEFAULT false,
  content_hash  text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX evidence_run_idx ON evidence_items (run_id, zone_id);

CREATE TABLE explanations (
  explanation_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  risk_id               uuid NOT NULL UNIQUE REFERENCES risk_predictions(risk_id) ON DELETE CASCADE,
  where_text            text NOT NULL,
  when_text             text NOT NULL,
  why                   jsonb NOT NULL,
  historical_similarity jsonb,
  action_summary        text,
  narrative             text NOT NULL,
  narrative_source      text NOT NULL CHECK (narrative_source IN ('TEMPLATE','LLM_VALIDATED')),
  validation            jsonb NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now()
);
```

**005\_alerts.sql**

```sql
CREATE TABLE alerts (
  alert_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  risk_id               uuid NOT NULL REFERENCES risk_predictions(risk_id),
  zone_id               text NOT NULL REFERENCES zones(zone_id),
  severity              text NOT NULL CHECK (severity IN ('ADVISORY','WARNING','URGENT')),
  status                text NOT NULL CHECK (status IN ('DRAFT','AI_GENERATED','PENDING_REVIEW','REQUEST_CHANGES','REANALYSIS','APPROVED','REJECTED','DISPATCHED','ACTIVE','RESOLVED','EXPIRED','CANCELLED')),
  requires_approval     boolean NOT NULL DEFAULT true,
  payload               jsonb NOT NULL,
  locale_texts          jsonb NOT NULL,
  low_confidence        boolean NOT NULL DEFAULT false,
  uses_simulated_inputs boolean NOT NULL DEFAULT false,
  version               integer NOT NULL DEFAULT 1,
  created_at            timestamptz NOT NULL DEFAULT now(),
  expires_at            timestamptz NOT NULL,
  dispatched_at         timestamptz
);
CREATE INDEX alerts_status_idx ON alerts (status, created_at DESC);
CREATE INDEX alerts_zone_idx ON alerts (zone_id, created_at DESC);

CREATE TABLE human_reviews (
  review_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id      uuid NOT NULL REFERENCES alerts(alert_id),
  alert_version integer NOT NULL,
  reviewer_id   uuid NOT NULL REFERENCES users(user_id),
  decision      text NOT NULL CHECK (decision IN ('APPROVE','APPROVE_WITH_CHANGES','REQUEST_CHANGES','REJECT')),
  checklist     jsonb NOT NULL,
  modifications jsonb,
  note          text,
  decided_at    timestamptz NOT NULL DEFAULT now(),
  CHECK (decision NOT IN ('APPROVE','APPROVE_WITH_CHANGES')
         OR (COALESCE((checklist->>'evidence_reviewed')::boolean, false)
         AND COALESCE((checklist->>'risk_reviewed')::boolean, false)
         AND COALESCE((checklist->>'recommendations_reviewed')::boolean, false)))
);

CREATE TABLE alert_recipients (
  recipient_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  alert_id        uuid NOT NULL REFERENCES alerts(alert_id) ON DELETE CASCADE,
  channel         text NOT NULL CHECK (channel IN ('DASHBOARD','MUNICIPAL_DASHBOARD','EMAIL','SMS_SIM','IVRS_SIM','PUSH_SIM')),
  audience        text NOT NULL CHECK (audience IN ('CITIZENS_IN_ZONE','MUNICIPAL','EMERGENCY_TEAMS','HEALTHCARE','TRAFFIC_POLICE')),
  address_hash    text,
  delivery_status text NOT NULL DEFAULT 'QUEUED' CHECK (delivery_status IN ('QUEUED','SIMULATED_DELIVERED','SENT_SANDBOX','FAILED','SKIPPED')),
  attempted_at    timestamptz,
  detail          jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE evacuation_routes (
  route_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  risk_id          uuid NOT NULL REFERENCES risk_predictions(risk_id),
  alert_id         uuid REFERENCES alerts(alert_id),
  origin_zone_id   text NOT NULL REFERENCES zones(zone_id),
  shelter_id       bigint NOT NULL REFERENCES shelters(shelter_id),
  rank             smallint NOT NULL,
  length_m         real NOT NULL,
  eta_min          real NOT NULL,
  safe_route_score real NOT NULL CHECK (safe_route_score BETWEEN 0 AND 1),
  max_edge_risk    real,
  blocked_edges    integer NOT NULL DEFAULT 0,
  warnings         text[] NOT NULL DEFAULT '{}',
  geom             geometry(LineString,32644) NOT NULL,
  graph_version    text NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX routes_gix ON evacuation_routes USING gist (geom);

CREATE TABLE recommended_actions (
  action_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  risk_id           uuid NOT NULL REFERENCES risk_predictions(risk_id),
  alert_id          uuid REFERENCES alerts(alert_id),
  action_type       text NOT NULL CHECK (action_type IN ('MONITOR','NOTIFY_OPERATORS','PUBLIC_WARNING','PREPARE_ROUTES','OPEN_SHELTERS','EVACUATION_RECOMMENDATION','DEPLOY_PUMPS','DEPLOY_RESCUE','MEDICAL_STANDBY','TRAFFIC_DIVERSION','REQUEST_MORE_DATA')),
  priority          smallint NOT NULL,
  target            jsonb NOT NULL,
  rationale         jsonb NOT NULL,
  policy_version    text NOT NULL,
  requires_approval boolean NOT NULL,
  status            text NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','APPROVED','REJECTED','IN_PROGRESS','DONE','CANCELLED')),
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE emergency_resources (
  resource_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kind         text NOT NULL CHECK (kind IN ('PUMP','RESCUE_BOAT','RESCUE_TEAM','AMBULANCE','RELIEF_TEAM','TRAFFIC_UNIT')),
  label        text NOT NULL,
  home_zone_id text REFERENCES zones(zone_id),
  geom         geometry(Point,32644) NOT NULL,
  capacity     integer,
  available    boolean NOT NULL DEFAULT true,
  is_simulated boolean NOT NULL DEFAULT true
);

CREATE TABLE response_actions (
  response_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_id    uuid NOT NULL REFERENCES recommended_actions(action_id),
  resource_id  bigint REFERENCES emergency_resources(resource_id),
  status       text NOT NULL CHECK (status IN ('ASSIGNED','EN_ROUTE','ON_SITE','COMPLETED','CANCELLED')),
  assigned_at  timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  detail       jsonb NOT NULL DEFAULT '{}',
  is_simulated boolean NOT NULL DEFAULT true
);
```

**006\_learning\_audit.sql**

```sql
CREATE TABLE prediction_outcomes (
  outcome_id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  risk_id                  uuid NOT NULL REFERENCES risk_predictions(risk_id),
  zone_id                  text NOT NULL REFERENCES zones(zone_id),
  observed_flooded         boolean,
  observed_flood_frac      real CHECK (observed_flood_frac BETWEEN 0 AND 1),
  observed_first_impact_at timestamptz,
  observed_max_level_cm    real,
  observed_extent_geom     geometry(MultiPolygon,32644),
  outcome_source           text NOT NULL CHECK (outcome_source IN ('HISTORICAL_LAYER','SIM_GROUND_TRUTH','OPERATOR_REPORT','SATELLITE','CITIZEN_REPORT')),
  is_simulated             boolean NOT NULL DEFAULT false,
  lead_time_min            real,
  iou real, precision_score real, recall_score real,
  captured_at              timestamptz NOT NULL DEFAULT now(),
  UNIQUE (risk_id, outcome_source)
);

CREATE TABLE feedback (
  feedback_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  feedback_type text NOT NULL CHECK (feedback_type IN ('OUTCOME','OPERATOR','FALSE_ALARM','MISSED_EVENT','DATA_ISSUE')),
  risk_id       uuid REFERENCES risk_predictions(risk_id),
  alert_id      uuid REFERENCES alerts(alert_id),
  zone_id       text REFERENCES zones(zone_id),
  submitted_by  uuid REFERENCES users(user_id),
  body          jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit_logs (
  audit_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  actor_id    uuid REFERENCES users(user_id),
  actor_role  text,
  action      text NOT NULL,
  entity_type text NOT NULL,
  entity_id   text NOT NULL,
  detail      jsonb NOT NULL DEFAULT '{}',
  prev_hash   text NOT NULL,
  row_hash    text NOT NULL
);
CREATE INDEX audit_entity_idx ON audit_logs (entity_type, entity_id, occurred_at);
```

**007\_views\_triggers.sql**

```sql
CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER audit_logs_immutable BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER human_reviews_immutable BEFORE UPDATE OR DELETE ON human_reviews
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

CREATE OR REPLACE FUNCTION require_approval_before_dispatch() RETURNS trigger AS $$
BEGIN
  IF NEW.status IN ('DISPATCHED','ACTIVE') AND NEW.requires_approval THEN
    IF NOT EXISTS (SELECT 1 FROM human_reviews r
                   WHERE r.alert_id = NEW.alert_id AND r.alert_version = NEW.version
                     AND r.decision IN ('APPROVE','APPROVE_WITH_CHANGES')) THEN
      RAISE EXCEPTION 'alert % cannot be dispatched without an approving review', NEW.alert_id;
    END IF;
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER alerts_dispatch_guard BEFORE INSERT OR UPDATE OF status ON alerts
  FOR EACH ROW EXECUTE FUNCTION require_approval_before_dispatch();

CREATE VIEW v_latest_risk AS
  SELECT DISTINCT ON (zone_id, horizon_min) *
  FROM risk_predictions ORDER BY zone_id, horizon_min, as_of DESC;

CREATE VIEW v_sensor_latest AS
  SELECT DISTINCT ON (sensor_id) *
  FROM water_level_observations ORDER BY sensor_id, observed_at DESC;
```

### 7.3 Relationships, constraints and safety guards

| Relationship | Rule |
| --- | --- |
| zones → grid\_cells → terrain\_features | A cell belongs to the ward that contains its centroid; features are 1:1 with cells |
| zones → zone\_static\_features | One row per ward; recomputed when any static layer changes (`feature_version`) |
| sensors → drainage\_edges, zones | A sensor sits on a drain edge and inside one ward |
| agent\_runs → risk\_predictions → risk\_factors, explanations | A run produces one row per ward per horizon; every explanation is 1:1 with a risk row |
| risk\_predictions → alerts → human\_reviews | An alert references the risk row that justified it; reviews are append-only |
| alerts → alert\_recipients, evacuation\_routes, recommended\_actions | Created at draft time; delivery fields change only after approval |
| risk\_predictions → prediction\_outcomes | At most one outcome per source per prediction |
| model\_versions | Exactly one `ACTIVE` row per model name (partial unique index) |
| Database-level safety | `alerts_dispatch_guard` blocks DISPATCHED or ACTIVE without a matching approving review for the same alert version; `audit_logs` and `human_reviews` are append-only |

### 7.4 Performance, retention and seed data

- All spatial joins use GiST indexes. Nearest-drain queries use the KNN operator: `ORDER BY e.geom <-> c.centroid LIMIT 1`.
- Expected MVP volume: 48 sensors × 1 reading per minute ≈ 69,000 rows per simulated day; risk rows 200 wards × 9 horizons × one run per 10 simulated minutes ≈ 260,000 per simulated day. Plain tables are sufficient. If a table passes about 20 million rows, convert it to a TimescaleDB hypertable or partition by month.
- Retention: simulated rows are deleted with their `scenario_run_id`; real observations are kept; `audit_logs` are never deleted.
- Seed data (`database/seed/`): one user per role, `data_sources` rows, scenario definitions, the emergency-resource inventory \[SIM\].

## 8. Geospatial Architecture

### 8.1 Coordinate reference systems

| CRS | Use | Never use it for |
| --- | --- | --- |
| EPSG:4326 (WGS 84, degrees) | API input and output (GeoJSON), sensor latitude/longitude, Open-Meteo requests | Distance, area, buffers, nearest-neighbour ranking |
| EPSG:32644 (WGS 84 / UTM zone 44N, metres) | All stored geometry; all distance, area, buffer and zonal operations; the analysis grid | Anything outside the study area |
| EPSG:3857 (Web Mercator) | Map tile rendering inside MapLibre | Stored geometry or any measurement |

Why a projected CRS: at 13°N one degree of longitude is about 108 km and one degree of latitude about 111 km, so degree-based distances are anisotropic and wrong. UTM zone 44N covers 78°–84°E; Chennai lies at about 80.2°E and the scale error across the study area is below 0.1 %. The GCC service already publishes in EPSG:32644 \[VERIFIED\].

**CRS rules.** (R1) Inputs are transformed at the boundary: `ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 32644)`. (R2) Outputs are transformed at the API: `ST_AsGeoJSON(ST_Transform(geom, 4326), 6)` (six decimals is about 0.1 m). (R3) Rasters are resampled onto the analysis grid with a method chosen by data type (§8.3). (R4) Never mix `geography` and `geometry` in one query without an explicit cast. (R5) Area in km² is `ST_Area(geom) / 1e6`. (R6) Geometry from any new source is checked with `ST_IsValid`, repaired with `ST_MakeValid`, and its SRID asserted before loading.

**Time rules.** Stored timestamps are UTC `timestamptz`. The API rejects timestamps without an offset. The UI displays Asia/Kolkata (UTC+05:30, no daylight saving). IMD daily totals cover 24 hours ending 08:30 IST \[ASSUMPTION: verify in the product note\]. Open-Meteo hourly precipitation is a sum over the preceding hour \[verify in its documentation\]; request `timezone=UTC`.

### 8.2 Spatial hierarchy

GCC zone (15) → ward (about 200) → 250 m grid cell (about 6,800 cells at 426 km²). Cells are aligned to multiples of 250 m in EPSG:32644 coordinates, so `ix = floor(x / 250)` and `iy = floor(y / 250)`; a cell belongs to the ward containing its centroid. Wards are the decision and alert unit. Cells are the computation unit for terrain, susceptibility, exposure and the indicative footprint.

### 8.3 Processing rules by data type

| Data | Method | Why |
| --- | --- | --- |
| Elevation | Resample the DEM to 25 m on the 250 m-aligned grid (bilinear); derive terrain at 25 m; reduce each 10 × 10 block to the 250 m cell | Block alignment makes cell statistics exact and fast |
| Land cover (categorical) | Reproject with nearest neighbour to a 10 m aligned grid; count classes per 25 × 25 block | Categories must never be interpolated |
| Population (counts) | Split each 100 m pixel into 2 × 2 pixels holding a quarter of its count, then sum 5 × 5 blocks | Preserves totals; interpolation would not |
| Rainfall (points to wards) | Open-Meteo requested at ward centroids; simulated gauges interpolated to ward centroids by inverse-distance weighting (power 2, three nearest) | Simple and explainable |
| Buildings, facilities | Counts by centroid-in-cell; city-wide counts per ward from server-side statistics | Avoids loading about a million polygons |
| Roads | Length per cell from OSM edges clipped to cells | Road exposure |
| Drains | Nearest-drain distance by KNN; density = drain length per km² | Drainage proximity and density |

### 8.4 Workflow code

Paged download from the GCC service. The code requests WGS 84 because GeoJSON consumers assume it and reprojects locally; this supersedes the `outSR` note in §6.2.

```python
import httpx, geopandas as gpd, pandas as pd

BASE = 'https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/GCC_COLLABORATION_LAYER/MapServer'

def fetch_layer(layer_id: int, where: str = '1=1', page: int = 2000) -> gpd.GeoDataFrame:
    frames, offset = [], 0
    with httpx.Client(timeout=60) as client:
        while True:
            r = client.get(f'{BASE}/{layer_id}/query', params={
                'where': where, 'outFields': '*', 'returnGeometry': 'true',
                'outSR': 4326, 'f': 'geojson', 'orderByFields': 'objectid',
                'resultOffset': offset, 'resultRecordCount': page})
            r.raise_for_status()
            feats = r.json().get('features', [])
            if not feats:
                break
            frames.append(gpd.GeoDataFrame.from_features(feats, crs=4326))
            offset += len(feats)
            if len(feats) < page:
                break
    gdf = pd.concat(frames, ignore_index=True) if frames else gpd.GeoDataFrame()
    return gdf.set_crs(4326).to_crs(32644) if len(gdf) else gdf
```

Grid creation and ward assignment:

```python
import numpy as np
from shapely.geometry import box

CELL = 250.0

def build_grid(wards: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    xmin, ymin, xmax, ymax = wards.total_bounds
    xs = np.arange(np.floor(xmin / CELL) * CELL, xmax + CELL, CELL)
    ys = np.arange(np.floor(ymin / CELL) * CELL, ymax + CELL, CELL)
    cells = [(int(x // CELL), int(y // CELL), box(x, y, x + CELL, y + CELL)) for x in xs for y in ys]
    grid = gpd.GeoDataFrame(cells, columns=['ix', 'iy', 'geometry'], crs=32644)
    centroids = grid.copy()
    centroids['geometry'] = grid.geometry.centroid
    joined = gpd.sjoin(centroids, wards[['zone_id', 'geometry']], predicate='within', how='inner')
    return grid.loc[joined.index].assign(zone_id=joined['zone_id'].values).reset_index(drop=True)
```

Terrain derivatives (pysheds; verify method names against the installed version):

```python
from pysheds.grid import Grid
import numpy as np

grid = Grid.from_raster('data/processed/dem_25m_32644.tif')
dem = grid.read_raster('data/processed/dem_25m_32644.tif')
filled = grid.fill_depressions(grid.fill_pits(dem))
flat_free = grid.resolve_flats(filled)
fdir = grid.flowdir(flat_free)
acc = grid.accumulation(fdir)
sink_depth = np.asarray(filled) - np.asarray(dem)          # ponding depth, metres
dy, dx = np.gradient(np.asarray(dem, dtype='float64'), 25.0)
slope = np.arctan(np.hypot(dx, dy))                        # radians
twi = np.log((np.asarray(acc) + 1.0) * 25.0 / np.tan(np.maximum(slope, 0.001)))

def block_reduce(a, k=10, fn=np.nanmean):
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    return fn(a[:h, :w].reshape(h // k, k, w // k, k), axis=(1, 3))
```

Height above nearest drain (`hand_m`) is `elev_mean_m` minus the DEM elevation sampled at the nearest GCC drain vertex; urban channels are better known from the GCC layer than from a 25 m DEM. Nearest-drain distance per cell (PostGIS):

```sql
UPDATE terrain_features t SET dist_drain_m = d.dist
FROM (SELECT c.cell_id,
             (SELECT ST_Distance(c.centroid, e.geom) FROM drainage_edges e
              ORDER BY e.geom <-> c.centroid LIMIT 1) AS dist
      FROM grid_cells c) d
WHERE t.cell_id = d.cell_id;
```

### 8.5 Spatial quality checks (run in Phase 3, enforced by tests)

SRID is 32644 everywhere; no invalid or empty geometries; ward areas match the source area field within 5 %; the 250 m cells tile the study area without overlap; every cell has a ward; raster transforms align to multiples of 25 m; population totals before and after aggregation agree within 0.5 %; building and facility counts per ward are non-negative and reconcile with the source.

## 9. Data Ingestion

### 9.1 Pipeline

```
Source ► Connector ► Validate ► Normalise ► Spatial join ► Store ► Features ► Model input
```

| Stage | Module | What it does | On failure |
| --- | --- | --- | --- |
| Connector | `ews.ingest.connectors.*` | Pulls (worker) or accepts (API push); no business logic | Three retries with exponential backoff; keep last good data; mark the source STALE |
| Validate | `ews.quality.validators` | Schema, range, timestamp, duplicate and plausibility checks | Reject malformed items; flag suspicious ones; never silently fix |
| Normalise | `ews.ingest.normalise` | Units (mm, cm, m), UTC, identifiers, null handling | Null stays null |
| Spatial join | `ews.geo.join` | Transform to EPSG:32644; assign ward and cell; snap sensors to drains | Items outside the study area are stored with `OUTSIDE_AOI` and not used |
| Store | `ews.db.repositories` | Idempotent upsert with provenance columns | One transaction per batch |
| Features | `ews.features` | As-of feature builders (§10) | Missing inputs give null features and a missing-data flag |
| Model input | `ews.models.inputs` | Arrays for the forecasters and the risk engine | Insufficient inputs lead to abstention (§17) |

### 9.2 Connectors

| Connector | Trigger | Endpoint | Writes | Fallback |
| --- | --- | --- | --- | --- |
| `gcc_arcgis` | On demand (static layers) | `MapServer/0` to `/8` \[VERIFIED\] | zones, drains, roads flags, building counts | Cached GeoPackage in `data/raw/` |
| `open_meteo_forecast` | Hourly | `api.open-meteo.com/v1/forecast`, one request for all ward centroids \[VERIFIED\] | `rainfall_forecasts`; past hours as `NWP_ANALYSIS` | Last good pull up to 6 h old, flagged STALE; then scenario or persistence |
| `open_meteo_archive` | On demand | `archive-api.open-meteo.com/v1/archive` \[VERIFIED\] | `rainfall_observations` (REANALYSIS) | Cached Parquet |
| `imd_daily` | On demand | OpenCity CSV or `imdlib` \[TEAM DOC\] | `rainfall_observations` (CITY\_DAILY, GRIDDED\_DAILY) | Cached CSV |
| `imerg` (optional) | 30–60 min | NASA Earthdata \[TEAM DOC\] | `rainfall_observations` (SATELLITE\_ESTIMATE) | Skip |
| `osm` | Monthly | OSMnx / Overpass \[TEAM DOC\] | roads, critical\_facilities | Cached GraphML |
| `gauge_http` (push) | Every 5 min per gauge | `POST /api/v1/data/rainfall` | `rainfall_observations` | none |
| `sensor_http` (push) | Every 60 s per sensor | `POST /api/v1/data/water-level` | `water_level_observations` | none |

Forecast request (verify the response shape in Open-Meteo's documentation; several coordinates return one object per location):

```python
params = {'latitude': ','.join(lats), 'longitude': ','.join(lons),
          'hourly': 'precipitation', 'timezone': 'UTC',
          'past_days': 1, 'forecast_days': 2}
r = httpx.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=30)
```

In a historical replay no real forecast exists for the past, so the replay publishes a **scenario forecast**: the true future rainfall multiplied by a smooth random error (mean 1, standard deviation 0.25 \[ASSUMPTION\]), stored with `model = 'scenario-sim'` and `is_simulated = true`.

### 9.3 Data contracts for the two ingestion endpoints

| Item | Rainfall `POST /api/v1/data/rainfall` | Water level `POST /api/v1/data/water-level` |
| --- | --- | --- |
| Input | `readings[]` (max 1,000): station\_id, period\_start, period\_end, depth\_mm, kind, scenario\_run\_id | `readings[]` (max 1,000): sensor\_id, observed\_at, level\_cm, rise\_rate\_cm\_min, battery\_pct, signal\_dbm, device\_status |
| Auth | Role SYSTEM\_SERVICE or the station's API key | The sensor's API key (`X-Sensor-Key`) |
| Validation | Station exists; timestamps carry an offset; period\_end after period\_start; period at most 24 h; period\_end not later than clock + 5 min; depth 0–300 mm per hour-equivalent | Sensor exists; key matches; level between -5 cm and drain depth + 100 cm; battery 0–100; signal -130 to 0 dBm; observed\_at not later than received + 2 min |
| Output | `accepted`, `rejected`, `flagged`, and one status per item (`CREATED`, `UPDATED`, `DUPLICATE_IGNORED`, `REJECTED`) with reason | Same shape |
| Errors | 422 schema error; 401 / 403 auth; 207-style partial acceptance is returned as 200 with per-item status | Same |
| Timestamps | Stored UTC; late arrivals (received - period\_end above 15 min) flagged `LATE` | Late above 10 min flagged `LATE`; future above 2 min flagged `CLOCK_SKEW` |
| Missing values | `depth_mm: null` stored as null with `MISSING`; never coerced to 0 | `level_cm: null` stored as null with `MISSING` |
| Duplicates | Unique on (station, period\_start, period\_end, kind); same value ignored; different value updates and flags `REVISED` | Unique on (sensor, observed\_at); same rule |
| Outliers | Above 150 mm per hour-equivalent flagged `OUT_OF_RANGE_HIGH`, kept | Spike and stuck rules in §9.4; flagged, kept, excluded from features |

Water-level payload example:

```json
{"readings": [{"sensor_id": "SNS-017", "observed_at": "2026-10-09T09:15:00+05:30",
  "level_cm": 42.5, "rise_rate_cm_min": 0.8, "battery_pct": 87,
  "signal_dbm": -92, "device_status": "OK"}]}
```

### 9.4 QC flags and the observation quality score

Flags: `MISSING`, `OUT_OF_RANGE`, `SPIKE`, `STUCK`, `LATE`, `CLOCK_SKEW`, `REVISED`, `LOW_BATTERY`, `WEAK_SIGNAL`, `NEIGHBOUR_DISAGREE`, `OUTSIDE_AOI`. Raw values are never edited; flags decide what the features and the risk engine may use.

- **Spike (causal Hampel).** Compare x(t) with the median of the previous five valid readings. Flag when |x - median| exceeds 3 × 1.4826 × MAD (MAD floored at 1 cm) and the step is above 15 cm per minute and no neighbour sensor within 1.5 km rose by at least 30 % of it.
- **Stuck.** Identical value (within 0.05 cm) for 30 consecutive readings while the ward received more than 2 mm in the last 30 minutes.
- **Neighbour disagreement.** Fill ratio differs from the median of neighbours within 1.5 km by more than 0.5 for more than 10 minutes.
- **Quality score** `q_obs`: 1.0 by default; 0 if OUT\_OF\_RANGE, SPIKE or STUCK; multiplied by 0.6 for LOW\_BATTERY or WEAK\_SIGNAL, 0.7 for NEIGHBOUR\_DISAGREE, 0.8 for LATE \[ASSUMPTION\]. Observations with `q_obs` of 0 are stored but never used.
- **Rainfall checks.** Range, staleness, and a spatial check (a gauge reporting more than five times the median of its neighbours while the neighbours report almost nothing is flagged `NEIGHBOUR_DISAGREE`).

### 9.5 Simulated IoT sensor system \[SIM\]

Dense live drain telemetry is not assumed to exist publicly. The simulator is a **prototype simulation**: behaviourally plausible, not physically perfect, and labelled `is_simulated = true` in storage and `SIMULATED` in the UI.

**Sensor record (registry and payload):** `sensor_id`, `drain_edge_id`, `timestamp`, `latitude`, `longitude`, `water_level_cm`, `rise_rate_cm_min`, `battery_percent`, `signal_strength` (dBm), `status` (OK, DEGRADED, STUCK, OFFLINE, LOW\_BATTERY, ANOMALY).

**Placement.** Default 48 sensors: one per GCC zone (15) at the highest-weight candidate in the zone, plus three per ward inside the demo cluster. Candidates are drain edges with a parseable depth (or the class default); weight = (0.5 + ward susceptibility) × (1 + historical flood frequency); selection is greedy with at least 500 m between sensors; the sensor sits at the edge midpoint; the seed is fixed so placement is reproducible.

**Behaviour model** (per sensor, one-minute Euler step, all parameters in `config/sensors.yaml`, all \[ASSUMPTION\]):

1. Rainfall at the sensor: replayed ward rainfall × a per-storm spatial factor (log-normal, sigma 0.1) with small temporal noise; cumulative P(t) in mm.
2. SCS Curve Number runoff: `CN = 60 + 38 × built_fraction`; `S = 25400 / CN - 254`; `Ia = 0.2 S`; cumulative runoff `Q = (P - Ia)^2 / (P - Ia + S)` for `P > Ia`, else 0; runoff rate `q(t) = dQ/dt`.
3. Inflow to the drain: `i(t) = kappa × q(t - L)` in cm per minute, with kappa uniform 0.4–1.6 cm per mm and lag L uniform 5–25 minutes.
4. Level: `dh/dt = i(t) - k × h × (1 - b) × tide(t)` with outflow constant k uniform 0.01–0.04 per minute, blockage b from a Beta(2, 10) draw (plus 0.2 if the GCC `obstacles` field is non-empty), and a tide factor `1 - 0.3 × max(0, sin(2π t / 12.42 h + phase))` for sensors within 3 km of the coast or a river.
5. Overflow: when `h` exceeds the drain depth D, the excess is held as ponding `p` that decays with a constant of 0.02 per minute; reported level is `h + p`. An overflow minute sets `sim_flooded = true` for the ward (ground truth, §27).
6. Chain: rainfall rises → runoff rises → level rises → fill ratio rises → hazard rises.

**Normal behaviour.** Dry baseline 0–5 cm with 0.5 cm Gaussian noise, 0.1 cm quantisation and slow drift. **Rain event.** The model above. **Rapid rise.** A scenario can impose an intensity step (for example 15 to 90 mm per hour in 10 minutes). **Recession.** Exponential decay through k.

**Fault injection (config-driven):**

| Fault | Model |
| --- | --- |
| Missing packets | Bursty Markov dropout: entry probability 0.003 per minute, mean burst 5 minutes |
| Communication outage | Zone-wide silence of 5–20 minutes at scheduled times |
| Stuck sensor | Value frozen from a scheduled minute for a set duration |
| Spike outliers | Probability 0.002 per reading, magnitude plus or minus 30–80 cm |
| Drift | Bias of plus or minus 2 cm per hour on selected sensors |
| Battery | Starts 60–100 %; drains 0.01–0.03 % per hour; below 15 % the dropout rate triples; at 0 % the sensor goes offline |
| Signal | Random walk between -60 and -110 dBm; below -105 dBm the dropout rate doubles |
| Clock skew | Rare offsets of 1–3 minutes |

**Engine.** `ews.simulation.engine.SimulationEngine` uses `numpy.random.default_rng(seed)` so a run is reproducible from `(scenario_id, seed)`. It advances a simulated clock at `speed` times real time, posts batches through the **same HTTP endpoints** with each sensor's API key, updates `sim_runs.sim_clock`, and supports start, pause, resume and stop. Scenario file:

```
id: chennai_2015_replay
rainfall:
  source: open_meteo_archive      # hourly ERA5-based series, bias-corrected to IMD daily totals
  window_start: 2015-11-30T18:30:00Z
  window_end:   2015-12-02T18:30:00Z
  scale: 1.0
  forecast: scenario_sim          # true future rainfall x smooth error, labelled simulated
sensors:
  background_per_gcc_zone: 1
  per_demo_ward: 3
faults:
  - {type: stuck,  sensor: auto_pick_demo_ward, start_min: 360, duration_min: 90}
  - {type: outage, scope: demo_gcc_zone, start_min: 540, duration_min: 12}
  - {type: spike_rate, p: 0.002}
speed: 120
seed: 42
```

## 10. Feature Engineering

### 10.1 Rules

- **As-of only.** Every builder takes `as_of` and reads observations with `observed_at <= as_of` and forecasts with `issued_at <= as_of`. Windows are half-open: (t - w, t\].
- **No zero-filling.** A rainfall window with more than 20 % missing sub-intervals returns null and flags `MISSING_RAIN`. Water-level readings are forward-filled for at most 3 minutes (flag `FFILL`), then null.
- **One code path.** Training and runtime import the same builders from `ews.features`, so there is no train/serve skew.
- **Versioning and snapshots.** `feature_version` is the first 12 hex characters of SHA-256 over (code version, `config/features.yaml`, input manifest hashes). Each analysis run writes `runs/<run_id>/features.parquet` and stores its SHA-256 in an `evidence_items` row of type MODEL\_OUTPUT. These are the “feature snapshots” mentioned in §4.7; there is no feature-store service.

### 10.2 Catalogue

| Group | Feature | Definition | Used by |
| --- | --- | --- | --- |
| Rainfall (ward) | `r15_mm`, `r60_mm`, `r180_mm` | Rainfall sums over (t-15 min, t\], (t-60 min, t\], (t-180 min, t\] from the 15-minute blended timeline | trigger T, forecaster |
|  | `i_now_mmh` | 4 × `r15_mm` | display |
|  | `a72_mm` | Sum over (t-72 h, t-3 h\] (antecedent wetness) | T' |
|  | `f60_mm`, `f180_mm` | Forecast sums over (t, t+60 min\] and (t, t+180 min\] | T(τ), forecaster |
|  | `rain_pctile` | Percentile of `r60_mm` in the NE-monsoon hourly climatology | explanation |
| Water level (sensor) | `level_cm`, `fill_ratio` | Level; level divided by drain depth (φ) | D |
|  | `rise_5`, `rise_10`, `rise_15` | Least-squares slope (cm per minute) over the last 5, 10, 15 minutes of valid readings | D, forecaster |
|  | `accel` | `rise_5` minus `rise_5` ten minutes earlier | forecaster |
|  | `t_full_min` | (depth - level) / `rise_10` when `rise_10` > 0.05, else null | explanation |
| Ward aggregates | `n_valid`, `phi_max`, `rise_max`, `q_top` | Valid sensors in the ward and neighbours within 1.5 km; maximum fill ratio; maximum rise; quality of the driving sensor | D, confidence |
| Static (cell and ward) | `elev_mean_m`, `elev_p10_m`, `slope_deg`, `twi`, `sink_depth_m`, `hand_m` | §8.4 | S |
|  | `dist_drain_m`, `drain_density_m_km2`, `drain_capacity_proxy_m3s` | §8.4, §10.3 | S, D\_est |
|  | `built_frac`, `tree_frac`, `water_frac` | WorldCover class fractions | S, D\_est, simulator |
|  | `hist_flood_freq` | Fraction of known events whose labels touch the cell | prior only; excluded from M1 inputs (label leakage) |
|  | population, vulnerable-age fraction, buildings, road length, facility counts, shelter distance | §6.2 | E, V |
| Forecaster site | `CN`, `depth_cm`, `S_ward`, `built_frac` | Static properties of the sensor site | M3 |

### 10.3 Drain capacity proxy (Manning)

For a drain edge with width w (m), depth d (m) and invert levels at both ends: slope s = (invert\_start - invert\_end) / length, clamped to at least 0.0005; area A = w × d; wetted perimeter P = w + 2d for an open channel or 2(w + d) for a covered one; hydraulic radius R = A / P; capacity Q = (1 / n) × A × R^(2/3) × s^(1/2) with n = 0.015 (concrete) \[ASSUMPTION\]. If any input is missing or not positive, `capacity_proxy_m3s` is null and `attrs_complete` is false. A ward's `drain_capacity_index` is the percentile rank, across wards, of (sum of Q over complete edges per km²) multiplied by the fraction of drain length that is complete. The proxy ranks wards; it is not a design calculation.

## 11. Forecasting Engine

The engine is split into four separate problems: **A** rainfall, **B** water level, **C** flood probability (the hazard score of §12) and **D** flood extent (§12.6). Each model below has a stated input, target and evaluation, and an evidence tier: **R** validated against real observations, **S** validated only against the simulator, **E** expert assumption, not validated.

### 11.1 A. Rainfall (what is and is not built)

- **Built:** NWP ingestion (Open-Meteo hourly), disaggregated uniformly to 15-minute steps, blended with a persistence nowcast: `rain_hat(τ) = w(τ) × persist + (1 - w(τ)) × nwp(τ)`, where `persist` is an exponentially weighted mean of the last 30 minutes of intensity (half-life 20 minutes) and `w(τ) = exp(-τ / 45 min)` for τ up to 120 minutes \[ASSUMPTION\].
- **Uncertainty:** the forecast part of the timeline is scaled by 0.7, 1.0 and 1.4 to give low, central and high scenarios \[ASSUMPTION\].
- **Not built:** radar nowcasting, optical-flow or ConvLSTM models, satellite advection. No radar data is assumed (§6.4), and training such models on public hourly data would not be defensible.
- **Honest status:** the blend weights are not validated, because archived forecasts for past events are not available. Tier E. No forecast-skill figure is claimed.

### 11.2 B. Water-level forecaster (M3)

| Item | Specification |
| --- | --- |
| Target | Δh(τ) = level(t + τ) - level(t) for τ = 15, 30, 60 minutes (direct strategy, one model per horizon) |
| Inputs | Lags of level (1, 5, 10, 15, 30, 60 min), `rise_5/10/15`, `accel`, rainfall sums (5, 15, 30, 60, 180 min), forecast rainfall (next 15, 30, 60 min), minutes since rain onset, site features (CN, depth, S\_ward, built\_frac) |
| Lookback / horizon | 60 minutes / up to 60 minutes. Beyond 60 minutes the risk engine uses the rainfall-based drain-stress estimate (§12.3), because longer sensor forecasts trained on simulated data would not be justified |
| Data | About 300 simulated storms (triangular and bimodal hyetographs, peak 10–120 mm per hour, duration 1–10 h) plus about 10 replay windows scaled 0.5–1.5, across 48 sensors, sampled every 5 minutes: roughly one million rows |
| Split | By storm, never by row: 60 % train, 20 % validation, 20 % test. A second test set shifts simulator parameters (kappa, k, lag) by plus or minus 30 %, uses new seeds and turns fault injection on (domain-shift test) |
| Intervals | Quantile LightGBM models at 0.1 and 0.9 |
| Constraints | Predicted level clipped to \[0, depth + 100 cm\]; predictions violating the clip are flagged |
| Metrics | MAE and RMSE (cm) per horizon; R² on Δh (not on level, which persistence already scores highly); skill score SS = 1 - RMSE\_model / RMSE\_persistence; peak-level error and peak-timing error; F1 and median lead time for “level reaches warning within 30 minutes”; MAPE only for peaks above 20 cm |
| Tier | S. Results are simulation benchmarks and are reported as such |

Candidates compared by the same script:

| Model | Role | Decision |
| --- | --- | --- |
| Persistence (Δ = 0) | Reference | Always computed |
| Linear extrapolation (`rise_10` × τ, clipped) | Reference | Always computed |
| Ridge regression | Interpretable baseline | Compared |
| Random Forest | Tree baseline | Compared |
| XGBoost | Equivalent boosted trees | Not used; one boosted-tree library is enough |
| LightGBM | **Selected MVP model** (point and quantile) | Runtime |
| LSTM / GRU | Advanced | Notebook only (`notebooks/04_gru_comparison.ipynb`) |

**Deep-learning gate.** A GRU is promoted to runtime only if (a) it is trained on real telemetry covering at least six months from at least 20 sensors, and (b) it beats LightGBM by at least 10 % RMSE on held-out real storms. On simulated data it stays a notebook comparison.

**Promotion gate for M3 candidates** (no performance number is assumed): SS is above zero against both persistence and linear extrapolation at every horizon on the domain-shift test, and RMSE is not more than 5 % worse than the current ACTIVE model.

### 11.3 C. Static flood susceptibility (M1)

| Item | Specification |
| --- | --- |
| Unit and target | 250 m cell; flooded (1) or not (0) in historical labels |
| Inputs | `elev_mean_m`, `elev_p10_m`, `slope_deg`, `twi`, `sink_depth_m`, `hand_m`, `dist_drain_m`, `dist_river_m`, `built_frac`, `drain_density_m_km2`, `drain_capacity_proxy_m3s` (nullable). **Not** `hist_flood_freq`: it comes from the labels |
| Labels | Positive: a cell containing at least one inundation point (2015, 2005, 2020 layers) or intersecting a flood polygon. Negative: cells at least 750 m from any positive and outside HIGH hazard-zone polygons. Label provenance is stored per feature. The inventory is presence-only, so negatives are pseudo-absences and this is stated wherever M1 is shown |
| Gate | At least 150 positive cells after quality control; otherwise use the fallback index below (tier E) |
| Models | Logistic regression (baseline) and LightGBM (selected) |
| Validation | Spatial block cross-validation (5 km blocks, 5 folds); leave-one-event-out when two or more events have independent labels; ROC-AUC, PR-AUC, Brier score; the OpenCity hazard-zone layers serve as an independent overlap check |
| Output | Predicted probability converted to a **percentile rank across the study area**, giving S in \[0, 1\]. Rank scaling removes the effect of the pseudo-absence sampling ratio on absolute probabilities |
| Explanation | SHAP summary in the offline report; runtime attribution does not use SHAP |
| Tier | R for the cross-validated skill; the use of rank S inside H is tier E |

Fallback index: `S_index = sum of w_j × rank01(feature_j)` with weights low elevation 0.25, low HAND 0.20, sink depth 0.15, TWI 0.10, built fraction 0.10, inverse drain proximity 0.10, inverse drain density 0.10 \[ASSUMPTION\].

### 11.4 Training artefacts and registry

`scripts/train_waterlevel.py` and `scripts/train_susceptibility.py` write `models/<name>/<version>/*.joblib`, `metrics.json` and `params.json`, then insert a `model_versions` row with status CANDIDATE and `trained_on_simulated` set correctly. Promotion to ACTIVE is a human action (§27).

## 12. Flood Risk Engine

### 12.1 Definitions

For ward w, analysis time t and horizon τ (0 to 120 minutes in 15-minute steps): **H** is flood likelihood (hazard), **E** is exposure, **V** is vulnerability, **R** is the risk score. `ramp(x; lo, hi) = clip((x - lo) / (hi - lo), 0, 1)`. `rank01(x)` is the percentile rank of x across wards, scaled to \[0, 1\].

### 12.2 Is a plain weighted sum sufficient? No

The proposal's `R = 0.4H + 0.3E + 0.3V` is compensatory: high E and V can offset a hazard of zero. A dense, vulnerable ward on a dry day scores 0.54 or more, which is a false alarm. The same problem appears on high ground in a storm if hazard is treated as the same everywhere. The engine therefore (1) puts terrain and drainage susceptibility inside the hazard term so that identical rain gives different likelihood in different wards, (2) gates the whole score by hazard, and (3) applies hazard floors to the top levels. The proposal's weights are kept.

### 12.3 Exact formulas

1. **Trigger.** `T(τ) = max(ramp(R60(τ); 20, 90), ramp(R180(τ); 50, 200))`, where R60(τ) and R180(τ) are 60- and 180-minute sums ending at t + τ on the blended timeline (observed up to t, forecast after). Antecedent amplification: `T'(τ) = min(1, T(τ) × (1 + 0.25 × ramp(A72; 30, 150)))`.
2. **Susceptibility modulation.** `g(S) = 0.25 + 0.75 × S_w`, with `S_w = 0.5 × mean(S_cell) + 0.5 × p90(S_cell)` over the ward's cells.
3. **Drain stress from sensors** (τ up to 60 minutes, using the M3 forecast of fill ratio φ and rise ρ): `D_s = max(ramp(φ; 0.5, 1.0), ramp(ρ; 0.3, 2.0) × ramp(φ; 0.25, 0.7))`, taken as the maximum over valid sensors in the ward and neighbours within 1.5 km. Sensor confidence `c_s = q_top × min(1, 0.6 + 0.2 × n_valid)`.
4. **Drain stress from a model** (no valid sensor, or τ above 60 minutes): `D_est = ramp(c_w × i(τ) / (i_design × (1 - b)); 0.6, 1.2)` with `c_w = 0.15 + 0.75 × built_frac`, i(τ) the maximum 15-minute intensity in mm per hour over the hour ending at t + τ, i\_design = 50 mm per hour and blockage b = 0.15 \[ASSUMPTION\].
5. **Effective drain stress.** `D_eff = c_s × D_s` when sensors are valid and τ is at most 60 minutes; otherwise `D_eff = 0.7 × D_est`.
6. **Hazard.** `H(τ) = 1 - (1 - T'(τ) × g(S_w)) × (1 - D_eff(τ))` (a probabilistic OR of two routes to flooding: rainfall on susceptible ground, and drain surcharge). The two routes are correlated, so H errs high; the Monte-Carlo interval of §17 reflects this.
7. **Exposure and vulnerability** (static, §12.5): E and V in \[0, 1\].
8. **Gated risk.** `G(H) = ramp(H; 0.10, 0.40)` and `R(τ) = G(H) × (0.4 H + 0.3 E + 0.3 V)`.
9. **Level.** LOW below 0.25; MEDIUM 0.25 to below 0.50; HIGH 0.50 to below 0.85; VERY\_HIGH 0.85 and above. Floors: HIGH needs H of at least 0.40; VERY\_HIGH needs H of at least 0.70 and confidence not LOW. A level that fails its floor is lowered one step at a time.
10. **Time to impact.** `τ* = min {τ : H(τ) >= 0.60}`; 0 means ongoing; null means none within 120 minutes.
11. **Probability field.** `probability = H`. It is a likelihood index until reliability calibration exists; `calibration_status` is UNCALIBRATED, HINDCAST\_CALIBRATED or OUTCOME\_CALIBRATED, and the UI says “index” unless calibrated (§27).

**Worked cases** (T' = 0.90, c\_s = 0.9; unit-test fixtures):

| Case | S | D (sensor) | E | V | H | R gated | Level | Plain weighted sum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A dry day, low-lying, dense (T' = 0) | 0.90 | 0.05 | 0.90 | 0.90 | 0.045 | 0.000 | LOW | 0.558, HIGH |
| B storm, high ground, dense | 0.10 | 0.10 | 0.90 | 0.50 | 0.356 | 0.480 | MEDIUM | 0.563, HIGH |
| C storm, low-lying, dense, drains full | 0.90 | 0.85 | 0.80 | 0.70 | 0.961 | 0.834 | HIGH | 0.834, HIGH |
| D storm, moderate susceptibility | 0.50 | 0.40 | 0.50 | 0.50 | 0.720 | 0.588 | HIGH | 0.588, HIGH |

Case C stays below VERY\_HIGH because R is under 0.85; VERY\_HIGH is reserved for extreme hazard in dense, vulnerable wards. The example in the proposal diagrams (H 0.85, E 0.75, V 0.70) gives 0.775 under the same weights, not the printed 0.82.

### 12.4 Parameters, normalisation and weighting

Dynamic inputs are normalised with piecewise-linear ramps: transparent, monotone, tunable, with no distribution assumptions. Static inputs use `rank01` across wards, which is robust to outliers. All parameters live in `config/risk.yaml` (§25) and are **\[ASSUMPTION\]** until calibrated.

| Parameter | Value | Meaning |
| --- | --- | --- |
| R60 ramp, R180 ramp | 20–90 mm, 50–200 mm | Accumulations scoring 0 to 1 |
| Antecedent ramp, boost | 30–150 mm, up to +25 % | Wet-antecedent amplification |
| Fill ramp, rise ramp, rise gate | 0.5–1.0, 0.3–2.0 cm per min, fill 0.25–0.7 | Sensor drain stress |
| i\_design, blockage b | 50 mm per hour, 0.15 | Placeholders: replace i\_design with a GCC value or a Manning-derived value |
| D\_est ramp, model trust | 0.6–1.2, 0.7 | Rainfall-based drain stress |
| s0 | 0.25 | Hazard floor for low-susceptibility wards |
| Gate | 0.10–0.40 | Hazard below 0.10 gives zero risk |
| Weights (H, E, V) | 0.4, 0.3, 0.3 | From the proposal |
| Level cuts, floors | 0.25 / 0.50 / 0.85; H 0.40 and 0.70 | Prototype thresholds, not official |
| Impact onset | H 0.60 | Defines time to impact |

**Sensitivity and calibration.** The engine can run 200 Monte-Carlo draws with every weight and ramp bound perturbed by plus or minus 20 %. The spread of H gives the interval in §17, and the rank stability of wards (Spearman correlation) is reported in the Model Performance view. When at least three events have usable labels, ramp bounds and s0 are fitted by minimising the Brier score under leave-one-event-out; until then the parameters stay as stated.

### 12.5 Exposure and vulnerability (static)

Counts are taken over the ward's **susceptible cells** (S\_cell of at least 0.5). `E = 0.35 rank01(population) + 0.15 rank01(buildings) + 0.15 rank01(road km) + 0.15 rank01(hospitals and clinics) + 0.10 rank01(schools) + 0.10 rank01(other critical facilities)`. `V = 0.5 rank01(vulnerable-age fraction) + 0.3 rank01(distance to nearest official shelter) + 0.2 rank01(evacuation difficulty)`, where evacuation difficulty = 1 - min(1, road density / ward road-density p90). If a component is unavailable, the remaining weights are renormalised and the coverage is recorded. **Impact estimate** (dynamic, for alerts and resources): population, buildings, road km, hospitals, schools and critical facilities inside the current footprint (§12.6).

### 12.6 What the prototype predicts: probability, zone risk and an indicative footprint

Chosen outputs: **zone risk (D)** and **likelihood (A)** per ward, plus an **indicative flood-prone footprint**. Depth and a true inundation polygon are not predicted: no calibrated hydraulic model or high-resolution terrain exists in the build, and pretending otherwise would be false. The footprint is a hybrid of ML susceptibility, terrain and drainage constraints, and historical flood layers: the cells of the ward with `S_cell >= s*`, where `s* = clip(0.90 - 0.60 × H, 0.30, 0.90)`, so higher hazard admits more cells. It is displayed as 250 m blocks labelled “indicative flood-prone area, not inundation depth”, and its overlap with observed event layers is reported as IoU at cell level (§32).

### 12.7 Auditability and overrides

Every risk row stores `config_hash`, model IDs, weights (through the config), input evidence IDs, feature timestamps, confidence and calculation time. Declarative overrides in `risk.yaml` are limited to: (1) a hospital inside the footprint raises MEDIUM to HIGH for human review; (2) low confidence caps the level at HIGH and marks the alert LOW-CONFIDENCE. Overrides are listed in the explanation.

## 13. Multi-Agent Architecture

### 13.1 Roster and shared rules

Six agents, each a Python class with a typed `run()` method that returns an `AgentResponse` and stores its typed result in the run context. Shared rules: (1) agents call tools through `ews.tools` and never write SQL; (2) the only memory is the run-scoped `RunContext` (persisted in `agent_runs.trace`) plus database reads, with no long-term free-text memory; (3) no agent may fabricate or silently substitute a value, and every missing input is listed; (4) no agent decides control flow with an LLM. Three components are **services, not agents**: the human-oversight service (§18), the alert dispatcher (§21) and the learning service (§27).

### 13.2 Agent specifications

**1. Orchestrator Agent.** *Purpose:* plan and control one analysis cycle. *Inputs:* `AgentRequest` (trigger, `as_of`, zone scope, scenario run). *Outputs:* run summary, final `agent_runs` state. *Tools:* the LangGraph engine, the policy gate, the run store. *Memory:* run context. *Allowed:* choose the next node by rule, retry a failed node once, skip nodes when no ward reaches MEDIUM, invoke fallbacks, route to human review. *Forbidden:* computing any number, editing evidence, approving, dispatching, bypassing policy, using an LLM to choose a route. *Failure:* a node that exceeds 30 s is marked FAILED; the run continues in degraded mode only if the lost output is not safety-critical, otherwise it ends FAILED and notifies administrators. *Insufficient evidence:* ends ABSTAINED and raises a review request. *Abstains when:* no valid rainfall source and no valid sensor exist for any ward. *Confidence:* passes on the minimum confidence of upstream agents and never raises it.

**2. Data & Retrieval Agent.** *Purpose:* assemble validated, as-of inputs and historical context. *Inputs:* `as_of`, zones. *Outputs:* a data bundle (rain timeline, sensor features, static features, per-source quality, evidence items) and `data_quality`. *Tools:* repositories, validators, connector fallbacks, the analog-event retriever. *Memory:* run context. *Allowed:* read the database, trigger one fallback refresh, compute QC and quality scores. *Forbidden:* filling gaps with invented or interpolated values, calling an LLM, writing risk fields. *Failure:* connector errors follow the fallback chain in §28. *Insufficient evidence:* returns `missing_inputs` and a lowered quality score. *Abstains when:* a ward has neither a valid rainfall source nor a valid sensor (that ward becomes INSUFFICIENT\_EVIDENCE). *Confidence:* sets the data-quality factor q (§17).

**3. Forecasting Agent.** *Purpose:* produce the blended rainfall timeline and water-level forecasts with intervals. *Inputs:* the data bundle. *Outputs:* `ForecastResult` per ward (rainfall) and per sensor (water level). *Tools:* rainfall blend, M3 `predict`, reference baselines. *Memory:* none. *Allowed:* run models, flag extrapolation. *Forbidden:* writing risk, using an LLM, forecasting sensors beyond 60 minutes. *Failure:* a missing model file falls back to linear extrapolation, flagged `FALLBACK_MODEL` (tier E). *Insufficient evidence:* with fewer than 10 minutes of valid sensor history it returns no water-level forecast and the risk engine uses the model-based drain stress. *Abstains:* never; it returns null forecasts. *Confidence:* returns interval width and model tier.

**4. Flood Risk Analysis Agent.** *Purpose:* compute H, E, V, R, level, time to impact, footprint, impact estimate and uncertainty. *Inputs:* data bundle, forecasts, the active risk configuration. *Outputs:* `RiskResult` per ward and horizon. *Tools:* the risk engine, footprint generator, Monte-Carlo sampler. *Memory:* none. *Allowed:* pure computation. *Forbidden:* an LLM, changing configuration, writing outside the repository layer. *Failure:* an engine exception marks that ward FAILED while others continue. *Insufficient evidence:* state INSUFFICIENT\_EVIDENCE with no score. *Abstains when:* data quality q is below 0.25 or required static features are missing. *Confidence:* computes C (§17).

**5. RCA & Explanation Agent.** *Purpose:* explain where, when, why and what action, with evidence. *Inputs:* `RiskResult`, data bundle, analog events. *Outputs:* `Explanation`. *Tools:* Shapley attribution, evidence registry, similar-event retriever, template renderer, optional narrator plus guard. *Memory:* none. *Allowed:* restate structured facts in words. *Forbidden:* adding facts, numbers or IDs, recommending actions, any claim without evidence. *Failure:* LLM unavailable or rejected by the guard falls back to the template. *Insufficient evidence:* says the evidence is incomplete and lists the gaps. *Abstains when:* fewer than two factors can cite evidence; alert drafting is then blocked for that ward. *Confidence:* carries the risk confidence unchanged.

**6. Decision & Recommendation Agent.** *Purpose:* turn risk and policy into drafts: alert, routes, shelters, resources. *Inputs:* `RiskResult`, `Explanation`, the policy file, road graph, shelters, resource inventory. *Outputs:* `Recommendation` list and `AlertDraft`. *Tools:* policy engine, route planner, shelter ranker, resource matcher, template alert writer. *Memory:* none. *Allowed:* draft only. *Forbidden:* dispatching, approving, changing risk, inventing shelters or capacities, writing free-text safety instructions. *Failure:* routing unavailable gives an approximate nearest-official-shelter list flagged APPROXIMATE. *Insufficient evidence:* emits a `REQUEST_MORE_DATA` action. *Abstains when:* the explanation is unavailable. *Confidence:* a VERY\_HIGH draft needs confidence of at least MEDIUM; LOW confidence caps the draft at WARNING and tags it LOW-CONFIDENCE.

## 14. Agent Contracts

Agents exchange only the Pydantic v2 models below (`ews/contracts.py`). All models forbid extra fields and are immutable. Timestamps must be timezone-aware (`AwareDatetime`).

```python
from __future__ import annotations
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class RiskLevel(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    VERY_HIGH = 'VERY_HIGH'


class ConfidenceLevel(str, Enum):
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW = 'LOW'


class AssessmentState(str, Enum):
    ASSESSED = 'ASSESSED'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'


class Evidence(Strict):
    evidence_id: str                      # EV-<TYPE>-<ZONE>-<YYYYMMDDTHHMM>-<hash8>
    evidence_type: Literal['RAINFALL', 'FORECAST', 'WATER_LEVEL', 'TERRAIN', 'DRAINAGE',
                           'HISTORICAL_EVENT', 'EXPOSURE', 'MODEL_OUTPUT', 'CONFIG']
    zone_id: str | None = None
    observed_at: AwareDatetime | None = None
    value: dict
    source_table: str
    source_keys: dict
    quality: float = Field(ge=0, le=1)
    is_simulated: bool = False
    content_hash: str


class AgentRequest(Strict):
    request_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    trigger: Literal['SCHEDULE', 'INGEST_EVENT', 'MANUAL', 'SIMULATION']
    as_of: AwareDatetime
    zone_ids: list[str] | None = None            # None = all wards
    scenario_run_id: UUID | None = None
    horizons_min: list[int] = [0, 15, 30, 45, 60, 75, 90, 105, 120]


class AgentResponse(Strict):
    request_id: UUID
    agent: Literal['orchestrator', 'data', 'forecast', 'risk', 'rca', 'decision']
    status: Literal['OK', 'DEGRADED', 'ABSTAINED', 'FAILED']
    started_at: AwareDatetime
    finished_at: AwareDatetime
    warnings: list[str] = []
    missing_inputs: list[str] = []
    payload_key: str | None = None               # key of the typed result in the run context


class SeriesPoint(Strict):
    horizon_min: int = Field(ge=0, le=120)
    value: float
    p10: float | None = None
    p90: float | None = None


class ForecastResult(Strict):
    target: Literal['RAINFALL_MM_15MIN', 'WATER_LEVEL_CM']
    subject_id: str                              # zone_id or sensor_id
    issued_at: AwareDatetime
    input_as_of: AwareDatetime
    points: list[SeriesPoint]
    model_version: str
    model_tier: Literal['R', 'S', 'E']
    is_simulated_input: bool
    fallback_used: bool = False
    warnings: list[str] = []


class KeyFactor(Strict):
    factor_key: str
    value: float | None
    unit: str | None = None
    contribution_pct: float | None = None
    direction: Literal['INCREASES', 'DECREASES', 'NEUTRAL']
    evidence_ids: list[str]


class RiskResult(Strict):
    zone_id: str
    timestamp: AwareDatetime
    horizon_min: int = Field(ge=0, le=120)
    state: AssessmentState
    risk_score: float | None = Field(default=None, ge=0, le=1)
    risk_level: RiskLevel | None = None
    probability: float | None = Field(default=None, ge=0, le=1)       # = hazard H
    calibration_status: Literal['UNCALIBRATED', 'HINDCAST_CALIBRATED', 'OUTCOME_CALIBRATED'] = 'UNCALIBRATED'
    time_to_impact_min: int | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_level: ConfidenceLevel | None = None
    hazard_score: float | None = None
    exposure_score: float | None = None
    vulnerability_score: float | None = None
    h_p10: float | None = None
    h_p90: float | None = None
    data_quality: float | None = None
    key_factors: list[KeyFactor] = []
    evidence_ids: list[str] = []
    impact_estimate: dict | None = None
    footprint_cell_ids: list[int] = []
    evidence_tier: Literal['R', 'S', 'E', 'MIXED'] = 'MIXED'
    uses_simulated_inputs: bool = False
    model_version: str                           # model ids joined with the risk-config version
    config_hash: str

    @model_validator(mode='after')
    def _state_matches_content(self):
        if self.state == AssessmentState.ASSESSED and None in (self.risk_score, self.risk_level, self.confidence):
            raise ValueError('ASSESSED results need score, level and confidence')
        if self.state == AssessmentState.INSUFFICIENT_EVIDENCE and self.risk_score is not None:
            raise ValueError('an abstaining result must not carry a score')
        return self


class AnalogEvent(Strict):
    event_id: str
    similarity: float = Field(ge=0, le=1)
    flooded_frac: float | None = None
    evidence_ids: list[str]


class Explanation(Strict):
    risk_id: UUID
    where: str
    when: str
    why: list[KeyFactor]
    historical_similarity: list[AnalogEvent] = []
    action_summary: str | None = None
    narrative: str
    narrative_source: Literal['TEMPLATE', 'LLM_VALIDATED']
    validation: dict

    @model_validator(mode='after')
    def _every_factor_cites_evidence(self):
        if any(not f.evidence_ids for f in self.why):
            raise ValueError('every factor must cite evidence')
        return self


class Recommendation(Strict):
    action_type: Literal['MONITOR', 'NOTIFY_OPERATORS', 'PUBLIC_WARNING', 'PREPARE_ROUTES', 'OPEN_SHELTERS',
                         'EVACUATION_RECOMMENDATION', 'DEPLOY_PUMPS', 'DEPLOY_RESCUE', 'MEDICAL_STANDBY',
                         'TRAFFIC_DIVERSION', 'REQUEST_MORE_DATA']
    priority: int = Field(ge=1, le=5)
    target: dict                                 # shelter, route, resource and road IDs
    rule_ids: list[str]
    evidence_ids: list[str]
    requires_approval: bool
    policy_version: str


class AlertDraft(Strict):
    risk_id: UUID
    zone_id: str
    severity: Literal['ADVISORY', 'WARNING', 'URGENT']
    status: Literal['DRAFT', 'AI_GENERATED', 'PENDING_REVIEW']
    locale_texts: dict[str, str]                 # from approved templates only
    cap_payload: dict
    low_confidence: bool
    uses_simulated_inputs: bool
    expires_at: AwareDatetime
    recommendations: list[Recommendation]


class HumanReview(Strict):
    alert_id: UUID
    alert_version: int
    reviewer_id: UUID
    decision: Literal['APPROVE', 'APPROVE_WITH_CHANGES', 'REQUEST_CHANGES', 'REJECT']
    checklist: dict[str, bool]
    modifications: dict | None = None
    note: str | None = None
    decided_at: AwareDatetime

    @model_validator(mode='after')
    def _approval_needs_full_checklist(self):
        needed = ('evidence_reviewed', 'risk_reviewed', 'recommendations_reviewed')
        if self.decision in ('APPROVE', 'APPROVE_WITH_CHANGES') and not all(self.checklist.get(k) for k in needed):
            raise ValueError('approval requires the full checklist')
        return self


class OutcomeFeedback(Strict):
    risk_id: UUID
    zone_id: str
    outcome_source: Literal['HISTORICAL_LAYER', 'SIM_GROUND_TRUTH', 'OPERATOR_REPORT', 'SATELLITE', 'CITIZEN_REPORT']
    observed_flooded: bool | None = None
    observed_flood_frac: float | None = Field(default=None, ge=0, le=1)
    observed_first_impact_at: AwareDatetime | None = None
    observed_max_level_cm: float | None = None
    is_simulated: bool
    note: str | None = None
```

**Contract rules.** (1) Evidence IDs have the form `EV-<TYPE>-<ZONE>-<YYYYMMDDTHHMM>-<hash8>`, where `hash8` is the first eight hex characters of the evidence `content_hash`. (2) The LLM adapter receives only a facts dictionary and the list of allowed evidence IDs; it returns text only and has no handle on any model above. (3) Contracts are versioned by the repository tag; a breaking change requires a migration note in `docs/CONTRACTS.md`. (4) Every agent response is validated on exit; a validation error marks the response FAILED and is logged with the run ID.

## 15. Orchestration

### 15.1 Design: two graphs and a database gate

`analysis_graph` runs one cycle and ends by saving drafts with status PENDING\_REVIEW. It never waits in memory for a human. The human decision is a state change made through the API (`POST /api/v1/alerts/{id}/approve`), which writes `human_reviews` and `audit_logs` and then starts `dispatch_graph`, which runs only for APPROVED alerts. This survives restarts and keeps the approval auditable.

```
analysis_graph
 START → plan → retrieve → qa_gate → forecast → risk → triage
                 │ missing                          │ no ward at MEDIUM or above → log_only → END
                 ▼                                  ▼
             fallback_data ─(retry once)─► qa_gate   explain → decide → policy_check → persist_drafts → END
                 │ still missing                                                       (awaiting human)
                 ▼
             abstain → review_request → END

dispatch_graph (only for APPROVED alerts)
 START → load_approved → routes_and_resources → notify (simulated gateway) → schedule_outcome_capture → END
```

### 15.2 Nodes

| Node | Agent or tool | Result |
| --- | --- | --- |
| `plan` | Orchestrator | Zone scope, horizons, run record, config hash |
| `retrieve` | Data & Retrieval | Data bundle, quality scores, evidence items |
| `qa_gate` | Orchestrator rules | Pass, or list of missing inputs |
| `fallback_data` | Data & Retrieval | One fallback refresh (cached forecast up to 6 h, neighbour sensors) |
| `forecast` | Forecasting | `ForecastResult` set |
| `risk` | Flood Risk Analysis | `RiskResult` per ward and horizon |
| `triage` | Orchestrator rules | Wards at MEDIUM or above continue |
| `explain` | RCA & Explanation | `Explanation` per continuing ward |
| `decide` | Decision & Recommendation | Recommendations and `AlertDraft` |
| `policy_check` | Policy engine | Sets `requires_approval`, applies confidence caps |
| `persist_drafts` | Repository | `alerts` in PENDING\_REVIEW, `recommended_actions`, routes |
| `abstain`, `review_request` | Orchestrator | ABSTAINED run and an operator task |

### 15.3 Conditional routing

| Condition | Route |
| --- | --- |
| No rainfall from any source | `fallback_data`; if still missing, abstain for the affected wards |
| Sensor failure in a ward | Use valid neighbours within 1.5 km, otherwise the model-based drain stress; confidence is lowered |
| Model confidence LOW | Cap the level at HIGH, tag LOW-CONFIDENCE, require human review |
| Risk below MEDIUM everywhere | `log_only`: no alert, no explanation, metrics only |
| HIGH or VERY\_HIGH with confidence of at least MEDIUM | Draft a critical alert |
| Any critical action | `requires_approval = true`, always |
| LLM unavailable or the guard rejects its text | `TemplateNarrator` |
| Routing unavailable | Approximate nearest-official-shelter list, flagged APPROXIMATE |

### 15.4 Triggers, cadence and run control

- **Triggers:** `SCHEDULE` every 10 minutes of (simulated) time; `INGEST_EVENT` when a ward's `r15_mm` passes 5 mm, a sensor's fill ratio passes 0.5 or its `rise_5` passes 0.3 cm per minute (debounced for 60 s); `MANUAL` through `POST /api/v1/risk/analyze`; `SIMULATION` from the engine on each cycle.
- **Control:** one RUNNING run per scenario (PostgreSQL advisory lock); node timeout 30 s; run timeout 120 s; one retry per node; every node appends an event (name, start, end, status, input hash) to `agent_runs.trace`.
- **Idempotency:** `persist_drafts` skips a ward that already has an open alert for the same severity and zone, and instead appends the new risk row as evidence to it.

## 16. Explainability

### 16.1 What every prediction explains

WHERE (ward, footprint), WHEN (as-of time, time to impact), WHY (ranked factors with evidence) and WHAT ACTION (recommendations). For every risk row the explanation contains: risk level and score, likelihood, time to impact, top contributing factors, evidence IDs, confidence, historical similarity and recommended action. Illustrative shape (values invented to show the structure, not a result):

```json
{"zone_id": "WARD-XXX", "where": "Ward XXX, GCC Zone NN; 14 of 31 cells susceptible",
 "when": "As of 2026-10-09T09:15+05:30; likelihood reaches 0.60 within 45 min",
 "risk": {"level": "HIGH", "score": 0.71, "probability": 0.78,
          "calibration": "UNCALIBRATED", "confidence": "MEDIUM"},
 "why": [{"factor": "observed_rainfall", "contribution_pct": 34, "direction": "INCREASES",
          "value": "r60 = 68 mm", "evidence_ids": ["EV-RAINFALL-WARD-XXX-20261009T0345-1a2b3c4d"]}],
 "historical_similarity": [{"event_id": "CHN-2015-12", "similarity": 0.71, "flooded_frac": 0.35}],
 "recommended_actions": ["PUBLIC_WARNING", "PREPARE_ROUTES", "OPEN_SHELTERS"]}
```

### 16.2 Attribution: exact Shapley values over the risk formula

Because the risk engine is an explicit function, contributions are computed exactly rather than approximated. The factor set has nine members: observed rainfall, forecast rainfall, antecedent rainfall, sensor fill ratio, sensor rise rate, model-based drain stress, susceptibility S, exposure E and vulnerability V. The baseline sets rainfall, antecedent, fill, rise and model stress to 0 and S, E, V to the city median. The value function v(C) is R computed with the factors in coalition C at their actual values and the rest at baseline. Shapley value of factor i: `phi_i = sum over C not containing i of |C|! (n - |C| - 1)! / n! × [v(C + i) - v(C)]`. With n = 9 this is 512 evaluations per ward and horizon, a few milliseconds. The values sum to R(actual) - R(baseline). `contribution_pct` is each positive phi divided by the sum of positive phi; negative values are reported as mitigating factors with direction DECREASES.

### 16.3 Evidence registry and validation

During `retrieve` and `risk`, every value that enters a calculation is registered as an `evidence_items` row: rainfall windows (station keys, sums), sensor readings (sensor IDs, timestamps, QC flags), static feature snapshots, the configuration hash, model outputs, analog events. Each factor lists the evidence IDs that support it. `validate_explanation()` rejects an explanation unless: **V1** every cited ID exists and belongs to the same run and ward; **V2** the cited evidence type matches the factor type; **V3** every number in the narrative equals, at the displayed precision, a number in the supplied facts; **V4** no place name appears that is not in the facts; **V5** no sentence matches the instruction patterns (evacuate, avoid, move, stay, do not and similar), because instructions come only from approved templates. A failed validation falls back to the template and is logged.

### 16.4 Historical similarity

Features per event and ward: maximum 1 h, maximum 3 h and 24 h rainfall, 72 h antecedent rainfall (`event_features`), standardised across the event set, plus S\_w. Distance is Euclidean; `similarity = 1 / (1 + distance)`; the top three are returned with the event's observed flooded fraction for that ward. The text always states how many events the comparison rests on, because there are only a handful.

### 16.5 Narrative generation

`TemplateNarrator` fills a fixed template from the facts (ward, level, likelihood, time to impact, the top three factors with values, the confidence statement, the similarity sentence). `OpenAICompatibleNarrator` may rewrite the same facts in at most 90 words under a system prompt that forbids adding numbers, places, advice or certainty. Its output is accepted only if §16.3 passes. The explanation record stores `narrative_source` (`TEMPLATE` or `LLM_VALIDATED`) and the validation result. The action summary is added by the Decision agent after policy evaluation, from a template.

## 17. Uncertainty

### 17.1 Five kinds, kept separate

| Kind | Meaning | Measure | Shown as |
| --- | --- | --- | --- |
| Model confidence | How much the models behind the number can be trusted | Evidence tier (R, S, E), calibration status | `evidence_tier`, `calibration_status` |
| Data quality | Coverage, freshness and validity of inputs | q in \[0, 1\] | `data_quality` |
| Sensor confidence | How far the sensing evidence can be trusted | c\_s in \[0, 1\] | inside hazard and confidence |
| Forecast uncertainty | Spread of rainfall and water-level forecasts | Rainfall scenarios 0.7 / 1.0 / 1.4; M3 quantiles | part of the H interval |
| Prediction uncertainty | Sensitivity of H to parameters | 200 Monte-Carlo draws, plus or minus 20 % on weights and ramp bounds | `h_p10`, `h_p90` |

### 17.2 Formulas

- `q = min(q_cov, q_fresh, q_valid)`: data quality is only as good as its weakest part.
- `q_cov = 0.5 × rain_ok + 0.5 × sensor_cov`, where `rain_ok` is 1 if at least one valid, fresh rainfall source exists and `sensor_cov = min(1, n_valid / 2)`, or 0.4 when the ward relies on the model-based stress alone \[ASSUMPTION\].
- `q_fresh = min over used sources of exp(-age / tau)`, with tau = 20 min for rainfall observations, 120 min for forecasts and 5 min for sensors \[ASSUMPTION\].
- `q_valid = 1 - (flagged readings used in the last 15 min) / (readings in the last 15 min)`.
- `w_int = H_p90 - H_p10` over the union of Monte-Carlo draws and the three rainfall scenarios.
- Agreement `a_ev`: 1.0 if rainfall and sensor evidence agree (`|T' g(S) - D_eff|` at most 0.3) or both are low; 0.8 if only one evidence type exists; 0.6 if they conflict (difference above 0.5 and one side at least 0.6).
- `C = q × (1 - min(1, w_int)) × a_ev`. Levels: **HIGH** 0.70 and above, **MEDIUM** 0.40 to below 0.70, **LOW** below 0.40 \[ASSUMPTION\].

### 17.3 How confidence changes decisions

| Confidence | Effect |
| --- | --- |
| HIGH | Normal drafting under policy |
| MEDIUM | All levels allowed; the draft carries a “verify” note and the reviewer sees the uncertainty panel first |
| LOW | Level capped at HIGH; alert tagged LOW-CONFIDENCE; human review mandatory even for MEDIUM advisories; no resource-deployment suggestions |
| INSUFFICIENT\_EVIDENCE | No alert; an operator task is created with the abstention message below |

Abstention message (from the diagram specification): “Cannot confidently determine risk. Reason: \<specific reason>. Missing inputs: \<list>. Recommended action: human review or obtain additional data.” Uncertainty is never converted into a confident-looking score.

### 17.4 Display rules

The UI labels `probability` as “flood likelihood index” with an UNCALIBRATED chip until §27 produces a reliability result; the chip then reads “calibrated on N events”. Every risk card shows the interval (`h_p10` to `h_p90`), the confidence level and a SIMULATED badge when `uses_simulated_inputs` is true.

## 18. Human Oversight

### 18.1 What needs a human

Critical actions are: any public alert at WARNING or URGENT; any evacuation recommendation; any resource-deployment request; promotion of a model to ACTIVE; any change to policy files. An ADVISORY (risk MEDIUM) is an operator acknowledgement, not a public alert. Nothing in the system treats elapsed time as consent.

### 18.2 Alert state machine

States follow the diagram specification: DRAFT → AI\_GENERATED → PENDING\_REVIEW → APPROVED → DISPATCHED → ACTIVE → RESOLVED, with REJECTED, REQUEST\_CHANGES → REANALYSIS, EXPIRED and CANCELLED as side paths.

| From → To | Done by | Condition |
| --- | --- | --- |
| DRAFT → AI\_GENERATED | System | Agents have filled content and evidence |
| AI\_GENERATED → PENDING\_REVIEW | System | `policy_check` passed |
| PENDING\_REVIEW → APPROVED | EMERGENCY\_COORDINATOR (WARNING, URGENT); MUNICIPAL\_OPERATOR (ADVISORY) | Review recorded with the full checklist |
| PENDING\_REVIEW → REJECTED | Same roles | Reason required |
| PENDING\_REVIEW → REQUEST\_CHANGES → REANALYSIS | Same roles, then system | Note required; the system re-runs analysis for the ward and creates version + 1 in PENDING\_REVIEW |
| APPROVED → DISPATCHED | System (`dispatch_graph`) | Database guard checks an approving review for the same version |
| DISPATCHED → ACTIVE | System | First successful (or simulated) delivery |
| ACTIVE → RESOLVED | EMERGENCY\_COORDINATOR | The system proposes it after two consecutive cycles below MEDIUM |
| Open state → EXPIRED | System | `expires_at` passed (default 30 minutes for a draft) |
| Open state → CANCELLED | EMERGENCY\_COORDINATOR or ADMIN | Reason required |

### 18.3 Review workflow

Draft alert → evidence review → risk review → recommendation review → approve, modify or reject → dispatch. The review screen shows, in this order: the abstention or confidence banner and the SIMULATED badge; the risk card with interval; the Shapley factors with links to each evidence item; the footprint and impact estimate; the proposed routes, shelters and resources; the exact text that would be sent in each language and channel. Approval needs three ticked boxes (evidence, risk, recommendations reviewed); the API and the database both enforce this.

**Modify** (decision `APPROVE_WITH_CHANGES`) allows: lowering severity, narrowing the area, removing channels or recipients, shortening expiry, and choosing among template variants. It does not allow raising severity above the draft or inserting free text into public messages. A modification creates `version + 1`, and the approving review refers to that version.

### 18.4 Audit

Every state change, approval, model promotion, configuration change and login writes an `audit_logs` row. The log is hash-chained: `row_hash = SHA-256(prev_hash || canonical_json(entry))`, with canonical JSON using sorted keys and no whitespace. `scripts/verify_audit_chain.py` recomputes the chain and fails on any break. The table rejects updates and deletes (§7.2). Production would add dual approval for URGENT alerts; the MVP uses a single approver by design and says so in the UI footer.

## 19. Decision Engine

### 19.1 Actions by level (prototype)

| Level | Posture | Drafted actions | Approval |
| --- | --- | --- | --- |
| LOW | Monitor | Log only | none |
| MEDIUM | Prepare | Notify operators; prepare candidate routes; flag vulnerable assets | Operator acknowledgement |
| HIGH | Warn | Public WARNING for the ward; open-shelter list; routes prepared; traffic diversion if an underpass is in the footprint | Coordinator |
| VERY\_HIGH | Urgent | URGENT warning; evacuation recommendation with routes and shelters; resource deployment request; medical standby if a hospital is in the footprint | Coordinator (dual approval in production) |

Modifiers: LOW confidence caps the draft at WARNING and tags it LOW-CONFIDENCE; INSUFFICIENT\_EVIDENCE creates no alert. **Prototype thresholds are not official.** The thresholds in §12 and the actions above are design choices for this prototype. `config/policy.prototype.yaml` carries `official: false`; `config/policy.official.yaml` is an empty template to be filled only with values supplied by the competent authority. The UI footer states which file is active.

### 19.2 Policy file

```
policy_version: proto-0.1
official: false            # prototype thresholds; not NDMA or GCC values
rules:
  - id: P-LOW
    when: {level: LOW}
    actions: [{type: MONITOR, priority: 5, approval: none}]
  - id: P-MED
    when: {level: MEDIUM}
    actions:
      - {type: NOTIFY_OPERATORS, priority: 4, approval: operator_ack}
      - {type: PREPARE_ROUTES, priority: 4, approval: none}
  - id: P-HIGH
    when: {level: HIGH}
    actions:
      - {type: PUBLIC_WARNING, priority: 2, approval: coordinator}
      - {type: PREPARE_ROUTES, priority: 2, approval: none}
      - {type: OPEN_SHELTERS, priority: 2, approval: coordinator}
      - {type: TRAFFIC_DIVERSION, priority: 3, approval: coordinator, if: underpass_in_footprint}
  - id: P-VHIGH
    when: {level: VERY_HIGH, min_confidence: MEDIUM}
    actions:
      - {type: PUBLIC_WARNING, priority: 1, approval: coordinator}
      - {type: EVACUATION_RECOMMENDATION, priority: 1, approval: coordinator}
      - {type: OPEN_SHELTERS, priority: 1, approval: coordinator}
      - {type: DEPLOY_RESCUE, priority: 1, approval: coordinator}
      - {type: DEPLOY_PUMPS, priority: 2, approval: coordinator}
      - {type: MEDICAL_STANDBY, priority: 2, approval: coordinator, if: hospital_in_footprint}
```

Evaluation is deterministic: select the rule whose `when` matches the level and confidence; evaluate each action's `if` against footprint flags computed by the risk agent; the draft's `requires_approval` is true if any action needs more than `none`; conflicts resolve by lowest priority number. Every action stores the rule ID and evidence IDs (`recommended_actions.rationale`).

### 19.3 Emergency-resource recommendation

Inputs: the impact estimate, the footprint area, `emergency_resources` \[SIM\]. Demand uses placeholder ratios in `config/response.prototype.yaml` (for example pumps per square kilometre of footprint, rescue teams per 1,000 exposed residents) labelled **PLACEHOLDER: to be replaced by GCC or NDRF norms**; no operational ratio is claimed. Matching is greedy: for each demanded unit, take the nearest available resource by routed travel time (straight-line distance when routing is unavailable, flagged APPROXIMATE). The output lists resource, ETA and the ward served, and every row is marked simulated.

## 20. Evacuation Routing

### 20.1 Graph

OSMnx drive network for the GCC boundary plus a 2 km buffer, stored as `data/processed/chennai_drive.graphml` and mirrored in `roads`; `graph_version` is the SHA-256 prefix of the file. Edge attributes: `length_m`, `speed_kph` (from `maxspeed`, else class defaults), `travel_time_s`, `is_underpass` (a GCC vehicular-subway line within 15 m of the edge, or OSM `tunnel` or negative `layer`), `is_bridge`. Only the largest strongly connected component is kept.

### 20.2 Dynamic edge risk and cost

For each edge, `r_e` is the maximum over the footprint cells it crosses of the ward's risk value (LOW 0, MEDIUM 0.4, HIGH 0.7, VERY\_HIGH 1.0), assigned only to footprint cells. Underpass edges take at least 0.6 when the ward is at MEDIUM or above and are blocked at HIGH or above \[ASSUMPTION\]. An overflow reading from a sensor within 50 m sets `r_e = 1`. Cost = `travel_time_s × (1 + 4 × r_e)`; an edge with `r_e` of 0.9 or more is removed.

### 20.3 Algorithm

1. Origin = footprint centroid of the ward (or a user-chosen point), snapped to the nearest graph node.
2. Candidates = official shelters with status OPEN or UNKNOWN within 8 km (candidate, non-official shelters are excluded unless `allow_candidate_shelters` is set).
3. Run Dijkstra from the origin with a weight function that returns `None` for blocked edges (NetworkX hides those edges).
4. For the five nearest candidates by cost, keep the best route; for the best candidate, also compute an alternative by multiplying the first route's edge costs by 1.5 and re-running.
5. Score and return the top three routes.

### 20.4 Safe route score

`SRS = 1 - (0.35 × tau + 0.45 × rho + 0.20 × kappa)`, in \[0, 1\], higher is better, where `tau = min(1, ETA_min / 30)`; `rho = 0.5 × (length-weighted mean of r_e) + 0.5 × (maximum r_e)`; `kappa = max(risk at the shelter's own location, status penalty)` with status penalty 0 for OPEN, 0.3 for UNKNOWN and 1 for FULL \[ASSUMPTION\]. Capacity is **not** a term: it is often unknown, and unknown values are never invented; the route card says “capacity unknown”. If no unblocked route exists, the system returns “no safe route found” and raises a human task.

### 20.5 Limits

Driving routes only; no live traffic; no turn restrictions beyond OSM; pedestrian evacuation is not modelled; accuracy of flooded-edge flags depends on the indicative footprint (§12.6).

## 21. Alert System

### 21.1 Channels

| Channel | MVP | Real in MVP? | Production path |
| --- | --- | --- | --- |
| Citizen web view | Responsive page: active approved alerts, nearest official shelter, route | Yes | Same, plus PWA push |
| Municipal dashboard | Alert queue, risk map, sensor status | Yes | Same |
| Email | SMTP to the Mailpit sandbox | Real SMTP, sandbox recipients | Transactional email provider |
| SMS | `SimulatedGateway` stores the message and shows it on a phone mock | **Simulated** | Licensed SMS gateway; sender and template registration required |
| IVRS | Script generated and shown; no call placed | **Simulated** | Telephony provider |
| Mobile push | Entry shown in the phone mock | **Simulated** | Push service |
| Public address, social media | Not built | No | Municipal integration |

The system never claims real SMS or IVRS delivery. Delivery rows read `SIMULATED_DELIVERED` or `SENT_SANDBOX`.

### 21.2 Payload (CAP-aligned)

The stored `payload` uses field names aligned with OASIS CAP 1.2 so a gateway adapter can be written later; no integration with any national alerting system is claimed. In the prototype, `status` is always `Exercise`.

| Internal severity | CAP severity | CAP urgency | CAP certainty |
| --- | --- | --- | --- |
| ADVISORY | Minor | Future | Possible |
| WARNING | Moderate | Expected | Likely |
| URGENT | Severe | Immediate | Likely |

Other fields: `identifier` (alert ID and version), `sender`, `sent`, `status`, `msgType` (Alert, Update, Cancel), `scope`, `event` (“Urban flood warning”), `onset`, `expires`, `headline`, `description`, `instruction`, `areaDesc`, `polygon` (WGS 84 latitude,longitude pairs), `parameter` (risk ID, confidence, `uses_simulated_inputs`).

### 21.3 Text

Public text comes only from approved templates in `config/alert_templates/{en,ta}.yaml` with placeholders (`{ward_name}`, `{time_window}`, `{shelter_name}`, `{route_summary}`). Tamil text is authored and reviewed by a Tamil-speaking team member and by the authority before any real use; it is never machine-translated at runtime. Instruction wording in the prototype is a placeholder pending GCC- or NDMA-approved text.

### 21.4 Dispatch, updates and suppression

`dispatch_graph` iterates recipient groups (citizens in ward, municipal, emergency teams, healthcare, traffic police), calls the gateway, and writes one `alert_recipients` row per channel and audience, idempotent on (alert, channel, audience), with three retries. Severity changes create a new version and go through review again. A ward receives at most one new alert per 30 minutes unless severity rises. Delivery success rate and latency are metrics (§30).

## 22. Frontend

### 22.1 Layout and rules

React + Vite + TypeScript SPA. Layout: left navigation (13 views), top bar (Asia/Kolkata clock with UTC tooltip, scenario status and controls, role badge, a **PROTOTYPE POLICY** badge when `official: false`), main panel, right drawer for ward details. Data comes from TanStack Query with 5–10 s polling; map state (view, layers, horizon) lives in the URL so a demo state can be shared. A public **citizen view** (`/citizen`, no login, English and Tamil) shows approved active alerts for a chosen ward or the browser's location, the nearest official shelter and the route.

**Safety rules in the UI.** Never show “safe”: show “no elevated risk assessed” with timestamp, data age and confidence. Always show the interval and confidence. A SIMULATED badge appears wherever `uses_simulated_inputs` or `is_simulated` is true. Approve stays disabled until the three checklist boxes are ticked; URGENT needs an extra confirmation dialog. Colours are never the only signal (labels and patterns accompany them). The legend states that colours are prototype risk levels, not IMD colour-coded warnings.

### 22.2 Views

| # | View | Contents | Main endpoints | Roles |
| --- | --- | --- | --- | --- |
| 1 | City Overview | KPI strip (wards per level, active alerts, sensors online %, data freshness), ward risk map, alert ticker, scenario clock | `GET /risk`, `/alerts`, `/health` | All (citizen sees a simplified card) |
| 2 | Live Rainfall | Gauge list, ward rainfall map, observed vs forecast hyetograph with scenarios, source chips (SIM, NWP, REANALYSIS) | `GET /data/rainfall`, `POST /forecast` | Operator and above |
| 3 | Water Levels | Sensor map by fill ratio, level chart with warning and critical lines and forecast band, sensor health table (battery, signal, QC flags) | `GET /data/water-level`, `/sensors` | Operator and above |
| 4 | Flood Risk Map | Layer toggles (risk level, hazard, exposure, vulnerability, susceptibility), horizon slider 0–120 min, footprint overlay, routes and shelters | `GET /risk`, `/zones` | All |
| 5 | Zone Details | Risk card (score, level, likelihood index, interval, confidence, tier chips), H/E/V bars, risk-vs-horizon timeline, impact estimate | `GET /risk/{zone_id}` | Operator and above |
| 6 | Explainability | Shapley bars, evidence table with IDs, similar events, narrative with source chip, validation status | `GET /explanations/{risk_id}` | Operator, researcher |
| 7 | Alerts | Queue by status, review panel with checklist, approve or reject, delivery log, phone mock for simulated SMS | `GET /alerts`, `POST /alerts/{id}/approve`, `/reject` | Operator, coordinator |
| 8 | Evacuation Routes | Ward select, ranked routes with safe-route score, ETA, warnings, map lines | `GET /routes` | Operator and above; citizen (approved only) |
| 9 | Shelters | Table and map: name, capacity (“unknown” flagged), status, distance | `GET /shelters` | All |
| 10 | Emergency Resources | Simulated inventory, assignments, ETAs | `GET /resources` | Operator and above |
| 11 | Historical Events | Event list, layers, event rainfall chart, replay launcher | `GET /events`, `POST /sim/scenario` | All |
| 12 | Model Performance | Metrics tables (target vs achieved), reliability diagram, hindcast per event, sensitivity, model versions | `GET /models` | Researcher, admin, operator |
| 13 | Continuous Learning | Prediction vs outcome table, outcome loader, before/after metrics, candidate model, promotion button | `POST /feedback`, `/learning/run`, `GET /models` | Admin, coordinator, researcher |

### 22.3 Components

`RiskMap`, `HorizonSlider`, `LayerToggle`, `RiskCard`, `ConfidenceBadge`, `TierChip`, `SimBadge`, `RainChart`, `LevelChart`, `ShapleyBars`, `EvidenceTable`, `AlertQueue`, `ReviewPanel`, `RouteList`, `ShelterTable`, `PhoneMock`, `ScenarioControls`, `ModelTable`, `ReliabilityChart`, `OutcomeLoader`, `AuditViewer`, `PolicyBadge`, `LanguageToggle`.

**Map layers (MapLibre):** wards filled by risk level (green, yellow, orange, red; grey hatch for INSUFFICIENT\_EVIDENCE); footprint cells as outlines; sensors as circles coloured by fill ratio with a ring for simulated; routes as lines; shelters as icons. Basemap style comes from `VITE_BASEMAP_STYLE_URL`; if it fails to load, the app renders wards and roads from GeoJSON on a blank background.

## 23. API Specification

### 23.1 Conventions

Base path `/api/v1`; JSON; timestamps are ISO 8601 with an offset (naive timestamps are rejected with 422). OpenAPI is generated at `/openapi.json` and `/docs`. Authentication: `Authorization: Bearer <JWT>` (HS256, 60-minute expiry, claims `sub` and `role`) for users; `X-Sensor-Key` for sensors; `X-Service-Key` for internal services; passwords are hashed with Argon2. Error body: `{"error": {"code": "VALIDATION_ERROR", "message": "...", "details": [], "request_id": "..."}}`. Lists accept `limit` (default 100, maximum 1,000) and `cursor`. Geometry in responses is GeoJSON in WGS 84 (RFC 7946). Standard errors: 401 unauthenticated, 403 role not allowed, 404 not found, 409 state or version conflict, 422 validation, 429 rate limit, 503 dependency unavailable.

Shared schemas: **IngestResult** `{accepted, rejected, flagged, items: [{index, status, reason?, flags?}]}`; **RainfallBatch** and **WaterLevelBatch** as in §9.3; **RiskResult**, **Explanation**, **ForecastResult**, **HumanReview** as in §14.

### 23.2 Endpoints

| Method and path | Auth (roles) | Request | Response | Errors |
| --- | --- | --- | --- | --- |
| `POST /auth/login` | none | `{email, password}` | `{access_token, role, expires_at}` | 401 |
| `GET /health` | none | none | `{status, db, models, sources: [{id, status, age_s}], scenario, version}` | 503 if the database is down |
| `POST /data/rainfall` | SYSTEM\_SERVICE or station key | RainfallBatch | IngestResult | 401, 403, 422 |
| `POST /data/water-level` | Sensor key | WaterLevelBatch | IngestResult | 401, 403, 422 |
| `GET /data/rainfall` | OPERATOR, COORDINATOR, RESEARCHER, ADMIN | `station_id?`, `zone_id?`, `from`, `to`, `kind?` | list of observations with QC flags | 422 |
| `GET /data/water-level` | Same | `sensor_id?`, `zone_id?`, `from`, `to`, `include_flags?` | list of observations | 422 |
| `GET /sensors` | Same | `zone_id?` | sensors with latest status and quality (GeoJSON optional) | none |
| `GET /zones` | none | `level?`, `format=json or geojson`, `with_risk?` | zones (geometry optional) | 422 |
| `GET /zones/{zone_id}` | none | none | zone and static features | 404 |
| `POST /forecast` | SYSTEM\_SERVICE, OPERATOR | `{as_of?, zone_ids?, sensor_ids?, targets}` | list of ForecastResult | 422 |
| `GET /risk` | All (citizen: level and time window only) | `horizon_min?`, `as_of?`, `min_level?` | list of latest RiskResult | 422 |
| `GET /risk/{zone_id}` | All | `horizon_min?`, `as_of?` | RiskResult per horizon and a timeline | 404 |
| `POST /risk/analyze` | OPERATOR and above, SYSTEM\_SERVICE | `{zone_ids?, as_of?, scenario_run_id?}` | `{run_id, status, summary}` (202 when started asynchronously) | 409 run in progress, 422 |
| `GET /explanations/{risk_id}` | OPERATOR, COORDINATOR, RESEARCHER, ADMIN | none | Explanation | 404 |
| `POST /alerts` | OPERATOR and above | `{risk_id, severity?, note?}` (manual draft) | Alert in DRAFT | 422 |
| `GET /alerts`, `GET /alerts/{id}` | OPERATOR and above; citizen sees only public ACTIVE alerts | `status?`, `zone_id?` | Alert with payload, recipients, recommendations, reviews | 404 |
| `POST /alerts/{id}/approve` | COORDINATOR (WARNING, URGENT); OPERATOR (ADVISORY) | `{alert_version, checklist, modifications?, note?}` | Alert (APPROVED then DISPATCHED) | 403, 409 version mismatch, 422 checklist |
| `POST /alerts/{id}/reject` | Same | `{alert_version, reason}` | Alert (REJECTED) | 403, 409 |
| `GET /routes` | OPERATOR and above; citizen (approved alerts only) | `zone_id` or `from_lat`, `from_lon`; `to_shelter_id?`, `max_routes?` | list of routes (GeoJSON, ETA, safe-route score, warnings) | 404, 503 (approximate fallback returned in the body) |
| `GET /shelters` | none | `zone_id?`, `near=lat,lon`, `radius_m?` | shelters (capacity nullable) | 422 |
| `GET /resources` | OPERATOR and above | `kind?`, `available?` | simulated resources | none |
| `GET /events` | none | `from?`, `to?`, `event_id?` | historical events (GeoJSON optional) | 404 |
| `POST /feedback` | OPERATOR and above, SYSTEM\_SERVICE | OutcomeFeedback, or `{feedback_type, body}` | `{feedback_id, outcome_id?}` | 422 |
| `GET /models` | OPERATOR, RESEARCHER, ADMIN | `name?`, `status?` | model versions with metrics | none |
| `POST /models/{id}/promote` | ADMIN, COORDINATOR | `{reason}` | model version (ACTIVE) | 403, 409 gate failed |
| `POST /learning/run` | ADMIN, SYSTEM\_SERVICE | `{mode: evaluate, recalibrate or retrain}` | `{job_id, summary}` | 409, 422 |
| `POST /sim/scenario` | ADMIN, OPERATOR | `{scenario_id, seed?, speed?}` | sim run | 409 run active, 422 |
| `POST /sim/{run_id}/control` | ADMIN, OPERATOR | `{action: pause, resume, stop or speed, speed?}` | sim run | 404, 409 |
| `GET /sim/status` | OPERATOR and above | none | active sim run and clock | none |

The first seventeen groups in the original brief are all present: ingestion (rainfall, water level), zones, risk (list and detail), explanations, forecast, risk analysis, alerts (create, approve, reject), routes, shelters, events, feedback, models and health. Worked JSON examples for each are in Appendix 44.

**Validation and idempotency.** Pydantic validates every request; ingestion endpoints are idempotent on their natural keys; `approve` and `reject` require the current `alert_version` and return 409 if it is stale; `POST /risk/analyze` takes the advisory lock and returns 409 if a run is already active.

## 24. Repository Structure

One repository, `chennai-flood-ews`, laid out by responsibility rather than by technology so that each folder maps to a layer in §4.

```
chennai-flood-ews/
├─ README.md                      quick start, architecture picture, data and licence notes
├─ pyproject.toml, uv.lock        dependency groups: api, geo, ml, agents, dev
├─ .env.example                   template only; .env is git-ignored
├─ docker-compose.yml             db, api, worker, web; profiles: demo, llm, obs
├─ Makefile                       up, seed, test, e2e, lint, repro
├─ .github/workflows/ci.yml
├─ config/
│  ├─ app.yaml  risk.yaml  features.yaml  models.yaml  sensors.yaml  data_sources.yaml
│  ├─ policy.prototype.yaml  policy.official.yaml (empty template)  response.prototype.yaml
│  ├─ alert_templates/en.yaml  ta.yaml
│  └─ scenarios/chennai_2015_replay.yaml  synthetic_cloudburst.yaml
├─ database/
│  ├─ migrations/001_core.sql ... 007_views_triggers.sql
│  └─ seed/users.sql  data_sources.sql  resources.yaml
├─ data/                          git-ignored except MANIFEST.yaml
│  └─ MANIFEST.yaml  raw/  processed/
├─ models/                        git-ignored artefacts: <name>/<version>/
├─ runs/                          git-ignored: features.parquet per run, experiments.jsonl
├─ src/ews/
│  ├─ config.py  contracts.py  logging.py  timeutil.py
│  ├─ db/          connection.py  repositories/  migrate.py
│  ├─ ingest/      connectors/{gcc_arcgis,open_meteo,imd,imerg,osm}.py  normalise.py  scheduler.py
│  ├─ quality/     validators.py  qc.py  scoring.py
│  ├─ geo/         crs.py  grid.py  terrain.py  zonal.py  join.py  footprint.py
│  ├─ features/    rainfall.py  waterlevel.py  static.py  builders.py
│  ├─ models/      waterlevel.py  susceptibility.py  rainfall_blend.py  registry.py  calibration.py
│  ├─ risk/        engine.py  params.py  uncertainty.py  confidence.py
│  ├─ explain/     attribution.py  evidence.py  similarity.py  narrators.py  guard.py
│  ├─ policy/      engine.py  rules.py  resources.py
│  ├─ routing/     graph.py  edge_risk.py  planner.py  score.py
│  ├─ alerts/      drafts.py  cap.py  gateway.py  dispatcher.py  templates.py
│  ├─ oversight/   reviews.py  state_machine.py  audit.py
│  ├─ agents/      orchestrator.py  data_agent.py  forecast_agent.py  risk_agent.py
│  │               rca_agent.py  decision_agent.py  graph.py
│  ├─ tools/       thin typed wrappers used by agents
│  ├─ learning/    outcomes.py  metrics.py  recalibrate.py  retrain.py  promotion.py
│  ├─ simulation/  engine.py  hydrology.py  faults.py  placement.py  scenarios.py
│  ├─ services/    business operations called by the API
│  └─ api/         main.py  deps.py  auth.py  routers/
├─ scripts/        probe_sources.py  fetch_gcc.py  build_grid.py  build_terrain.py
│                  build_static_features.py  build_event_table.py  build_road_graph.py
│                  train_susceptibility.py  train_waterlevel.py  evaluate.py
│                  run_demo.py  e2e_demo.py  verify_audit_chain.py  migrate.py
├─ notebooks/      01_data_profiling  02_labels_and_leakage  03_susceptibility
│                  04_gru_comparison  05_calibration
├─ tests/          unit/ integration/ geo/ model/ agent/ api/ sim/ e2e/ fixtures/
├─ web/            package.json  vite.config.ts  src/{routes,components,api,hooks,styles}
├─ docs/           ARCHITECTURE.md  CONTRACTS.md  DATA.md  LIMITATIONS.md  DEMO.md  RUNBOOK.md
└─ docker/         api.Dockerfile  web.Dockerfile  nginx.conf
```

| Folder | Responsibility |
| --- | --- |
| `config/` | All tunable numbers, thresholds, templates and scenarios; nothing numeric is hard-coded in `src/` |
| `database/` | Authoritative schema and seed data |
| `data/` | Large inputs and processed layers (never committed); `MANIFEST.yaml` is committed |
| `src/ews/` | The system, one package per layer of §4 |
| `scripts/` | One-off and batch jobs: acquisition, precompute, training, evaluation, demo |
| `tests/` | Mirrors `src/`; markers select layers (§31) |
| `docs/` | Human-readable decisions; `LIMITATIONS.md` repeats §2.5 |

## 25. Configuration

**Principles.** Secrets only in environment variables or Docker secrets, never in Git; everything else in versioned YAML. Precedence: environment variable over YAML. The effective configuration (secrets excluded) is serialised as canonical JSON and hashed: `config_hash = SHA-256(...)[:16]`, stored on every run and risk row.

| File | Holds |
| --- | --- |
| `.env` / `.env.example` | `DATABASE_URL`, `JWT_SECRET`, `SENSOR_KEY_PEPPER`, `SMTP_HOST`, `SMTP_PORT`, `LLM_PROVIDER` (`none` by default), `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` (optional), `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` (optional, IMERG only), `VITE_API_URL`, `VITE_BASEMAP_STYLE_URL` |
| `config/app.yaml` | Time zone, horizons, analysis cadence, run and node timeouts, paths, feature flags |
| `config/risk.yaml` | All §12.4 parameters, weights, level cuts, floors, overrides |
| `config/features.yaml` | Window lengths, missing-data limits |
| `config/models.yaml` | LightGBM hyperparameters and seeds for M1 and M3, gating rules |
| `config/sensors.yaml` | Sensor counts, placement weights, simulator parameter ranges, fault rates |
| `config/data_sources.yaml` | Endpoints, intervals, timeouts, retry policy, fallback order |
| `config/policy.prototype.yaml`, `policy.official.yaml` | Actions by level; the official file stays empty until supplied by the authority |
| `config/response.prototype.yaml` | Placeholder resource ratios |
| `config/alert_templates/*.yaml` | Approved message templates by locale |
| `config/scenarios/*.yaml` | Replay and synthetic storms, fault schedules |

A safe example of each file is in Appendix 45. `gitleaks` runs as a pre-commit hook and in CI.

## 26. MLOps

Kept deliberately small. There are three models and one calibration, so heavy tooling would cost more than it saves.

| Concern | Practice |
| --- | --- |
| Dataset versioning | `data/MANIFEST.yaml` plus `data_sources` rows (URL, retrieval date, version, licence, SHA-256). `scripts/probe_sources.py` re-verifies hashes. DVC is a production option |
| Model versioning | `model_versions`: name, semantic version, git SHA, dataset-manifest hash, parameters, metrics, `trained_on_simulated`, artefact SHA-256 |
| Experiment tracking | Each training or evaluation script appends one JSON line to `runs/experiments.jsonl` (run ID, script, git SHA, seed, parameters, metrics, duration); notebooks append to the same file. MLflow is a production option |
| Registry | CANDIDATE, ACTIVE, RETIRED, REJECTED; exactly one ACTIVE per name (database index) |
| Evaluation | `scripts/evaluate.py` writes `reports/eval_<date>.json` and the tables shown in the Model Performance view |
| Promotion | Human action through the API, gated by the rules in §11 and §27, written to the audit log |
| Rollback | `python -m ews.learning.promotion rollback <name>` makes the most recent RETIRED version ACTIVE and retires the current one in one transaction; covered by a test |
| Reproducibility | Seeds in config, `uv.lock`, pinned image tags, `make repro` rebuilds the demo from the manifest |

## 27. Continuous Learning

### 27.1 The loop and what is real

```
Prediction ► Actual outcome ► Comparison ► Error analysis ► Dataset update
    ▲                                                               │
    └── better prediction ◄── human-gated promotion ◄── recalibration / retraining ◄──┘
```

The prototype implements a **controlled, offline** loop started by `POST /api/v1/learning/run`. It does not learn online, and it never changes a model that is serving predictions unless a human promotes a candidate.

### 27.2 Outcome sources

| Source | Content | Real or simulated | Status |
| --- | --- | --- | --- |
| `HISTORICAL_LAYER` | Observed flooded points or polygons from the OpenCity layers for the replayed event, mapped to wards and cells | Real labels | MVP |
| `SIM_GROUND_TRUTH` | Per-ward `sim_flooded` (overflow occurred) and per-sensor peak level from the simulator | Simulated | MVP |
| `OPERATOR_REPORT` | Dashboard form: ward, flooded yes or no, first-impact time, depth estimate | Real in operation; demo entries marked simulated | MVP (form) |
| `SATELLITE` | Flood maps derived from Sentinel-1 | Real | Stretch |
| `CITIZEN_REPORT` | Citizen reports | Real | Not built |

### 27.3 Pairing and metrics

A prediction (ward, `as_of`, horizon) is paired with an outcome observed in (`as_of`, `as_of` + horizon + 30 min\]. **Predicted positive:** H at that horizon is at least 0.60 (the impact-onset value, configurable). **Observed positive:** `observed_flooded` is true.

- **Categorical:** hits, misses, false alarms, correct negatives; POD = hits / (hits + misses); false-alarm ratio = false alarms / (hits + false alarms); CSI = hits / (hits + misses + false alarms); precision, recall, F1.
- **Probabilistic:** Brier score = mean of (H - outcome)²; reliability curve with five equal-width bins; expected calibration error.
- **Timing:** lead time = observed first-impact time minus the first time H reached 0.60 (positive means warned early).
- **Spatial:** cell-level IoU, precision and recall of the footprint against observed flooded cells when the outcome has geometry; share of observed-flooded population inside the predicted footprint.
- Every metric is reported with its counts, and intervals come from a bootstrap that resamples **events**. With fewer than five events the interval is shown as “insufficient events”.

### 27.4 Error analysis

For false alarms and misses the report lists mean Shapley contributions by factor (false alarms against hits), sensor coverage in the ward, S\_w against outcome, confidence level, data quality, and the ten worst wards. It proposes adjustments (ramp bounds, sensor placement, label corrections) as text. Proposals are never applied automatically.

### 27.5 Dataset update

New outcomes go to `prediction_outcomes`. For historical events, `event_features` rows are rebuilt with provenance. Simulated storms are added to the M3 training set with `trained_on_simulated = true`. Label sources are never merged away.

### 27.6 What a learning run can produce

| Output | Method | Minimum data | Result |
| --- | --- | --- | --- |
| Probability calibration | Isotonic regression on (H, outcome), fitted out-of-fold; Platt scaling below 50 pairs | 20 pairs (Platt), 50 (isotonic) | CALIBRATION candidate with reliability evidence |
| Threshold tuning | Choose onset and level cuts that minimise `c_miss × misses + c_fa × false alarms`; ratio 5 : 1 \[ASSUMPTION\] | 30 pairs, at least 3 positives | RULESET candidate (a `risk.yaml` diff) |
| Ramp bounds and s0 | Minimise Brier score under leave-one-event-out | 3 events with labels | RULESET candidate |
| M3 retraining | Same script as §11.2 with new data | any new storms | ML candidate |
| M1 retraining | Same as §11.3 with new label polygons | new labels | ML candidate |

Every candidate is a `model_versions` row with before and after metrics. **Nothing is promoted automatically.**

### 27.7 Retraining triggers (`config/models.yaml`)

At least 30 new paired outcomes since the last candidate; Brier score worse by 10 % or more (relative) over the last 50 pairs than at the previous promotion; feature drift with population stability index above 0.2 for `r60_mm`, `fill_ratio` or S\_w; or a manual request.

### 27.8 Promotion gate and rollback

A candidate is eligible only if (1) a shadow evaluation (stored inputs replayed for the last N events) shows Brier and CSI no worse than ACTIVE beyond a tolerance (default 5 % relative); (2) the model tests pass; (3) an ADMIN or EMERGENCY\_COORDINATOR approves with a reason, which is written to the audit log. Rollback is described in §26.

### 27.9 The demonstration

After the replay, the outcome loader attaches the real event layer's observed flooding for the replayed event and the simulator's ground truth. `mode=evaluate` computes §27.3 from stored predictions. `mode=recalibrate` fits a calibration candidate on outcomes that **exclude the replayed event** (the simulated-outcome batch from §11 supplies extra pairs and is labelled simulated) and applies it to the replayed event, so the before and after comparison is out-of-sample. The UI shows Brier score, calibration error and the reliability diagram before and after, computed from data. The result may be no improvement or a worse score; it is shown as computed.

### 27.10 Not claimed

Autonomous online learning, automatic promotion, and any accuracy figure from the conceptual diagrams (87 %, IoU 0.76, “90 %+”).

## 28. Failure Handling

Policy: degrade safely and visibly; never invent data. Any failure that removes both rainfall and sensor evidence for a ward ends in abstention (§17). `/health` reports each component as OK, DEGRADED or DOWN.

| Case | Detection | Fallback | User-visible behaviour | Logging | Severity |
| --- | --- | --- | --- | --- | --- |
| No rainfall data | No valid rainfall row within its freshness window from any source | Refresh Open-Meteo once; use cached analysis or forecast up to 6 h, flagged STALE; otherwise no rainfall-driven hazard | Wards with sensors continue on drain stress with lower confidence; others show INSUFFICIENT\_EVIDENCE and “rainfall data unavailable since HH:MM” | WARN `rain.unavailable`; ERROR after 30 min | High |
| No forecast | Forecast empty or older than 3 h | Persistence nowcast only | Forecast band hidden; horizons beyond 15 min marked observation-only; confidence lowered | WARN | Medium |
| Sensor offline | No reading for 3 intervals, or status OFFLINE | Valid neighbours within 1.5 km, else model-based drain stress | Sensor grey; ward chip “model-estimated drain stress” | WARN `sensor.offline` | Medium |
| Sensor anomaly | SPIKE, STUCK or NEIGHBOUR\_DISAGREE | Exclude the reading, keep the raw value, use other sensors | Flag icon with QC tooltip | INFO or WARN with sensor ID | Low to Medium |
| Database unavailable | Connection error or failed health check | API returns 503 for writes; dashboards serve an in-memory snapshot up to 60 s old; worker pauses and retries with backoff; **no dispatch** (the guard needs the database) | Red banner “database unavailable, view is stale”; approvals disabled | ERROR; notify admin | Critical |
| LLM unavailable | Timeout, 5xx, or guard rejection | `TemplateNarrator` | Chip reads TEMPLATE | INFO `narrator.fallback` | Low |
| Routing unavailable | Graph missing or corrupt; planner exception | Straight-line nearest official shelters, flagged APPROXIMATE; operator task | Route card says “approximate, no road routing” | ERROR if graph missing, else WARN | High |
| Low confidence | C below 0.40 | Cap at HIGH, LOW-CONFIDENCE tag, mandatory review, no resource suggestions | Amber banner with reasons | INFO | Medium |
| Conflicting sources | `a_ev` of 0.6 (rainfall high and sensors low, or the reverse) | Do not average; keep both routes inside H; lower confidence | Conflict panel in the explanation shows both evidence sets | WARN `evidence.conflict` | Medium |
| Missing historical event | Similarity search returns no event for the ward | Omit similarity | Text: “no comparable events in the archive” | INFO | Low |
| Invalid geometry | `ST_IsValid` is false at load or runtime | `ST_MakeValid` at load; quarantine to `data/quarantine/`; fail the load if repair changes area by more than 5 % | Not user-visible (build step fails) | ERROR `geom.invalid` | Medium |
| Stale data | Age above its window | Lower `q_fresh`; STALE chip; beyond a hard limit (rain 60 min, sensors 15 min) treat as missing | Data-age chips turn amber then red | WARN | Medium |
| Model file missing or corrupt | Load error or SHA-256 mismatch | M3: linear extrapolation; M1: fallback index; flagged `FALLBACK_MODEL`, tier E | Tier chip E; admin banner | ERROR | High |
| Worker stalled | Heartbeat older than three cadence intervals | `/health` marks the scheduler unhealthy; container restart policy `unless-stopped` | Red health badge; “analysis is stale” banner | ERROR | High |
| Notification failure | Gateway error | Three retries with backoff; mark FAILED; operator task for an alternate channel | Delivery log shows FAILED | ERROR; metric `notification_failures` | High |
| Clock skew | Timestamp more than 2 minutes in the future | Flag `CLOCK_SKEW`; receive time is used for ordering only, never as event time | Sensor chip | WARN | Low |

## 29. Security

### 29.1 Authentication and keys

Users log in with email and password (Argon2 hashes) and receive a JWT (HS256, 60-minute expiry, claims `sub` and `role`). Each sensor and gauge has its own random 256-bit API key, stored only as `HMAC-SHA256(SENSOR_KEY_PEPPER, key)`; the key is shown once at creation. Service keys work the same way. Revocation sets `is_active = false`; rotation is an admin script.

### 29.2 Roles and permissions

| Capability | Citizen | Operator | Coordinator | Admin | Researcher | Service |
| --- | --- | --- | --- | --- | --- | --- |
| Public map and approved active alerts | Y | Y | Y | Y | Y | - |
| Rainfall, sensor data and QC flags | - | Y | Y | Y | Y | - |
| Explanations and evidence | - | Y | Y | Y | Y | - |
| Run analysis; create a manual draft | - | Y | Y | Y | - | Y |
| Approve or reject ADVISORY | - | Y | Y | - | - | - |
| Approve or reject WARNING or URGENT | - | - | Y | - | - | - |
| Cancel an alert | - | - | Y | Y | - | - |
| Submit outcomes and feedback | - | Y | Y | Y | - | Y |
| Control the simulation | - | Y | - | Y | - | - |
| View model metrics | - | Y | Y | Y | Y | - |
| Promote or roll back a model | - | - | Y | Y | - | - |
| Manage users, keys, configuration | - | - | - | Y | - | - |
| Read the audit log | - | - | Y | Y | - | - |
| Ingest rainfall and water level | - | - | - | - | - | Y (with device key) |

Admins cannot approve WARNING or URGENT alerts: separation of duties keeps system administration apart from the decision to warn the public. Permissions are enforced in the API routers and, for dispatch, again by the database guard.

### 29.3 API and platform hardening

TLS terminates at the reverse proxy for any shared deployment (a local demo may use HTTP); CORS uses an allow-list from the environment; all SQL uses bound parameters; request bodies are limited to 1 MB and ingestion batches to 1,000 items; rate limits apply (for example 60 requests per minute unauthenticated, higher for sensors); error responses never include stack traces and carry a `request_id`; containers run as a non-root user; `pip-audit` and `npm audit` run in CI; lock files are committed.

### 29.4 Secrets

`.env` is git-ignored; `.env.example` contains placeholders only; deployments on a VM use Docker secrets; `gitleaks` runs as a pre-commit hook and in CI; rotating `JWT_SECRET` is a redeploy.

### 29.5 Privacy

The MVP stores no personal data of citizens: recipients are audience groups per ward and `address_hash` stays empty. Operator emails are personal data and are limited to the users table. If real phone numbers or addresses are ever collected, minimise them, encrypt at rest, define retention and take legal advice on India's Digital Personal Data Protection Act, 2023. Logs must not contain personal data.

### 29.6 Threats and mitigations

| Threat | Mitigation |
| --- | --- |
| Forged sensor data | Per-device keys, QC rules, neighbour checks, confidence penalty |
| Replayed readings | Timestamp window; unique (sensor, time) constraint |
| False alert injection | Human gate plus the database dispatch guard |
| Prompt injection into the narrator | The LLM sees only a structured facts object and returns text that is validated; it has no tools |
| Privilege escalation | Role checks in routers; separation of duties; guard in the database |
| Audit tampering | Append-only triggers and hash chain |
| Flooding the ingestion endpoint | Size limits, rate limits, authentication |
| Vulnerable dependencies | Locked versions and audit scans |

No penetration test has been performed; HS256 is symmetric; the deployment is single-node (§2.5, L13).

## 30. Observability

### 30.1 Logs

structlog writes JSON to stdout (collected by Docker). Common fields: `ts` (UTC), `level`, `event`, `request_id`, `run_id`, `scenario_run_id`, `zone_id`, `node`, `duration_ms`, `error`.

| Event | When | Key fields |
| --- | --- | --- |
| `ingest.batch` | Each ingestion batch | source, accepted, rejected, flagged, latency\_ms |
| `sensor.status` | Status change | sensor\_id, old, new, reason |
| `model.inference` | Each forecast or susceptibility call | model, version, rows, duration\_ms |
| `agent.call`, `tool.call` | Each agent or tool call | agent or tool, run\_id, status, duration\_ms |
| `risk.calculated` | Per ward and horizon | zone\_id, H, E, V, R, level, confidence |
| `alert.created` | Draft saved | alert\_id, severity, zone\_id, low\_confidence |
| `approval.decision` | Review recorded | alert\_id, version, decision, reviewer role |
| `notification.result` | Per delivery attempt | alert\_id, channel, status |
| `fallback.used` | Any fallback | kind, reason |
| `learning.update` | Learning run | mode, candidate\_id, metrics |
| `error` | Any exception | type, message, request\_id |

### 30.2 Metrics

Prometheus exposition at `/metrics`: `ews_ingest_latency_seconds{source}`, `ews_ingest_items_total{source,status}`, `ews_data_age_seconds{source}` (data freshness), `ews_sensor_availability_ratio`, `ews_prediction_latency_seconds{stage}` (forecast, risk, explain, decide, cycle), `ews_risk_wards{level}`, `ews_alert_latency_seconds{phase}` (trigger to draft, approval to dispatch), `ews_notifications_total{channel,status}`, `ews_model_confidence` (histogram), `ews_agent_runs_total{status}`, `ews_fallbacks_total{kind}`. Forecast accuracy, false positives and false negatives come from the learning service as gauges (`ews_eval_pod`, `ews_eval_far`, `ews_eval_brier`) after each evaluation.

### 30.3 Views and alerts

A System Health panel in the web app reads `/health` and a metrics summary. Grafana and Prometheus are an optional compose profile. Internal alerts (log lines and a banner) fire on data age beyond its hard limit, scheduler heartbeat loss, database loss and repeated notification failures. `agent_runs.trace` is the trace for each analysis cycle; OpenTelemetry is a production option.

## 31. Testing

### 31.1 Layers

| Layer | What it proves | Tools and marker |
| --- | --- | --- |
| Unit | Ramps, risk formulas, Shapley (efficiency: values sum to R(actual) minus R(baseline)), QC rules, SCS-CN, Manning, safe-route score; Hypothesis checks that H never falls when rain rises | pytest `unit` |
| Integration | Migrations, triggers (dispatch guard, append-only), ingestion idempotency, repositories | pytest `integration`, PostGIS service container |
| Geospatial | SRID and validity, grid tiling, block reduction and population mass preservation, KNN equals brute force on a sample, lat/lon lands in the expected ward | pytest `geo`, tiny fixture city |
| Model | No leakage (group split asserted), M3 beats persistence on fixture storms, determinism with fixed seeds, artefact SHA check, M1 cross-validation runs | pytest `model` (slow, nightly) |
| Agent | Contract validation, abstention paths, passes with `LLM_PROVIDER=none`, narrative guard rejects invented numbers, graph routing per condition | pytest `agent` |
| API | RBAC matrix, validation errors, approve and reject with versions, ingestion results | pytest `api` (httpx test client) |
| Simulation | Determinism per seed; fault rates within statistical tolerance; rain raises level; levels never negative | pytest `sim` |
| End to end | Scripted demo through the API; one browser smoke test (login, map loads, approval flow) | `scripts/e2e_demo.py`, Playwright |

### 31.2 Required cases

| ID | Scenario | Given | Then |
| --- | --- | --- | --- |
| T01 | Rainfall spike | Dry ward; 95 mm falls within 60 minutes | T is 1.0; an `INGEST_EVENT` run starts within the 60 s debounce |
| T02 | Sensor spike | One reading jumps by 60 cm in a minute; neighbours flat | Flagged SPIKE and excluded; ward drain stress unchanged; no alert |
| T03 | Missing sensor | Sensor offline; a valid neighbour within 1.5 km (case a) or none (case b) | (a) neighbour used; (b) model-based drain stress with the “model-estimated” chip; confidence lower than baseline in both |
| T04 | High rainfall, low elevation | S = 0.90, storm as in case C | H at least 0.90 and level HIGH or above |
| T05 | High rainfall, good drainage | S = 0.10, same storm | H lower than in T04 for identical inputs; matches case B |
| T06 | Low rainfall, high water level | No rain; fill ratio 0.95 and rising 1.5 cm per minute | Sensor route alone gives H of at least 0.60; confidence lowered by the conflict factor; explanation cites water-level evidence and notes no rainfall |
| T07 | Historical similarity | Fixture events with known features | Nearest event is the matching one; text states how many events were compared |
| T08 | High risk, low confidence | R in the HIGH range, C = 0.35 | Level capped at HIGH; LOW-CONFIDENCE tag; mandatory review; no VERY\_HIGH |
| T09 | Critical alert approval | URGENT draft | Operator approval returns 403; coordinator without all checklist boxes returns 422; coordinator with them gives APPROVED then DISPATCHED; a direct SQL update to DISPATCHED without a review fails; audit rows exist and the chain verifies |
| T10 | Alert rejection | WARNING draft | Reject with reason gives REJECTED; no recipient rows; no dispatch; audit row; the same state does not recreate the alert within 30 minutes unless severity rises |
| T11 | Dry day, dense and vulnerable ward | T = 0; E = V = 0.9 | R is 0 and the level is LOW (the plain weighted sum would give 0.558) |
| T12 | No data | No rainfall and no valid sensor for a ward | State INSUFFICIENT\_EVIDENCE; no score; no alert; an operator task |
| T13 | Invented number | Narrator output contains a number not in the facts | Guard rejects; template used; `narrative_source` is TEMPLATE |
| T14 | Stale approval | Approve with an old `alert_version` | 409 |
| T15 | CRS | Sensor latitude and longitude from the demo ward | Stored in SRID 32644 inside that ward |
| T16 | Scenario determinism | Same scenario and seed twice | Identical readings |
| T17 | Rollback | Promote a candidate, then roll back | Previous version is ACTIVE; exactly one ACTIVE row |

Coverage is reported by CI; no coverage figure is claimed here. The engines in `ews.risk`, `ews.explain.attribution` and `ews.policy` are expected to be fully covered by unit tests.

## 32. Evaluation

Targets below are **proposals made by this manual** so the team has something to measure against. They are not official, not derived from data and not achieved results. `scripts/evaluate.py` fills the “Achieved” column from stored outputs; until it runs the column is empty.

| Area | KPI and definition | Data tier | Proposed target | Achieved |
| --- | --- | --- | --- | --- |
| Forecasting (M3) | MAE, RMSE (cm) per horizon; R² on Δh; skill score against persistence | S (domain-shift test) | SS of at least 0.10 at 15 and 30 minutes; above 0 at 60 | to be measured |
| Susceptibility (M1) | ROC-AUC, PR-AUC, Brier under spatial block CV | R | ROC-AUC of at least 0.70 | to be measured |
| Event classification | Precision, recall, F1, ROC-AUC on ward-level hindcasts | R | Report with counts; no target until three or more events are labelled | to be measured |
| Flood mapping | IoU, precision, recall of the footprint against observed cells | R | Report only (the footprint is indicative) | to be measured |
| Timing | Median lead time (minutes) | R and S | At least 30 minutes | to be measured |
| Operational | POD; false-alarm ratio; missed-event rate (1 - POD) | R and S | POD at least 0.70; FAR at most 0.50 (to be revised after the first hindcast) | to be measured |
| Calibration | Brier score, ECE, reliability curve | R and S | Report; label “calibrated” only after the curve supports it | to be measured |
| System | Prediction latency for a full 200-ward cycle | n/a | At most 5 s on a laptop | to be measured |
| System | Alert latency: trigger to draft; approval to dispatch | n/a | At most 30 s; at most 5 s | to be measured |
| System | Data freshness (rain, sensors); sensor availability | n/a | Rain at most 20 min; sensors at most 2 min; availability reported against injected faults | to be measured |

**Protocols.** (1) Hindcast with leave-one-event-out and per-event tables. (2) Simulation benchmark with the domain-shift test set. (3) Baselines in every table: persistence; a rainfall-threshold-only classifier; the plain weighted sum; the gated engine, so the added value of the design is visible. (4) Intervals by event bootstrap; counts always shown; no claim from fewer than five events. (5) Results from simulated data are labelled simulated everywhere they appear, including slides.

## 33. MVP Architecture

```
 Browser (React)  ◄── REST/JSON ──►  api (FastAPI) ──► PostgreSQL + PostGIS ◄── worker (APScheduler)
   │                                  │                                      ├─ connectors (GCC, Open-Meteo, IMD, OSM)
   │                                  │                                      ├─ simulator (HTTP → same API)
   └─ MapLibre, charts                ├─ LangGraph agents + risk engine      └─ learning jobs
                                      ├─ models/ (joblib), config/ (YAML)
                                      └─ Mailpit (sandbox email) · optional Ollama
```

**The MVP contains:** public datasets and GCC layers; historical flood layers; rainfall archive and forecast; terrain and drainage analysis; the geospatial engine; the water-level and susceptibility models; the risk engine; multi-agent orchestration; explainability; the dashboard; simulated IoT sensors; simulated alert delivery (plus sandbox email); a real human-approval workflow operated by seeded demo users; and the controlled continuous-learning demonstration.

**The MVP must not contain** (§41 gives reasons): Kubernetes, microservices, Kafka, Redis, a vector database, autonomous emergency actions, claimed real-time integrations, deep learning in the runtime path, hydraulic inundation simulation, claims of real IoT hardware, or claimed government integrations.

## 34. Production Architecture

Nothing in this table is built in the hackathon. It shows that the MVP interfaces were chosen so each row can be swapped in without redesign.

| Concern | MVP | Production direction |
| --- | --- | --- |
| Sensors | Simulated, HTTP | Real gateways publishing over MQTT (for example LoRaWAN or NB-IoT backhaul) with device provisioning and firmware management |
| Streaming | HTTP ingestion | MQTT and Kafka behind the same validators |
| Time series | PostgreSQL tables | TimescaleDB hypertables or partitioning |
| Model serving | In-process joblib | Versioned model service, shadow deployment, drift monitoring |
| Hydraulics | SCS-CN and reservoir surrogate | Calibrated SWMM or HEC-RAS on utility-supplied pipe and terrain data |
| Routing | NetworkX | OpenRouteService, GraphHopper or pgRouting with live traffic |
| Rainfall | Reanalysis, NWP, simulated gauges | Rain-gauge network, IMD radar products, satellite estimates, calibrated nowcasting |
| Compute | Docker Compose, one node | Kubernetes, managed or HA PostgreSQL, autoscaling workers |
| Alerts | Dashboard, sandbox email, simulated SMS and IVRS | Licensed SMS and IVRS, cell broadcast, national alert gateway through CAP |
| Security | JWT and RBAC, single approver | SSO and OIDC, dual approval for URGENT, penetration test, privacy compliance |
| Observability | Logs, `/metrics`, health view | Full Prometheus and Grafana, tracing, on-call rotation |
| Governance | Prototype thresholds | Official thresholds, SOPs and data-sharing agreements with the competent authorities |

## 35. Implementation Roadmap

**Method.** Build a walking skeleton on fake data first (end of Phase 2 plus one fake risk row on the map), then deepen. Effort figures are planning estimates in person-days (not measured); the total is about 68 person-days, parallelisable across four tracks: data (Phases 1, 3, 4, 5), backend (2, 6, 7, 8, 9, 10, 11, 12), routing and learning (13, 15), frontend (14). **Milestones:** M0 skeleton (Phases 0–2); M1 real static layers (1, 3, 4); M2 dynamic data and simulator (5–7); M3 engines and agents (8–11); M4 human gate, routing, UI (12–14); M5 integration, tests, demo (15–17). Critical path: 0 → 2 → 3 → 4 → 8 → 9 → 11 → 12 → 15 → 17.

**Phase 0 — Repository initialisation (2 pd).** *Goal:* runnable skeleton with CI. *Inputs:* this manual. *Outputs:* repository, Compose stack, green CI, health endpoint. *Files:* `pyproject.toml`, `uv.lock`, `docker-compose.yml`, `Makefile`, `.env.example`, `.github/workflows/ci.yml`, `src/ews/{config,logging,timeutil}.py`, `src/ews/api/main.py`, `web/` shell. *Depends on:* nothing. *Tasks:* initialise with `uv`; Compose with the database; `GET /health`; ruff, mypy, pytest; gitleaks hook; Vite shell. *Tests:* smoke test; CI run. *Done when:* a fresh clone runs `make up` and `GET /health` is OK.

**Phase 1 — Chennai datasets and source probe (4 pd).** *Goal:* know exactly what can be obtained and fetch the static layers. *Inputs:* §6. *Outputs:* `data/MANIFEST.yaml` with statuses; probe report; GCC layers 0–8; DEM; WorldPop; WorldCover; OSM extract; OpenCity files; demo area chosen. *Files:* `scripts/probe_sources.py`, `scripts/fetch_gcc.py`, `config/data_sources.yaml`, `notebooks/01_data_profiling`, `docs/DATA.md`. *Depends on:* 0. *Tasks:* probe each source (status, content type, counts); page the GCC layers; try the DEM chain (public bucket, then SRTM, then GLO-90); measure drain-attribute completeness and per-ward coverage; apply the §2.4 rule; record licences. *Tests:* manifest hashes verify; failed probes are recorded as FAILED\_PROBE. *Done when:* every dataset has a status and a next step, and the demo area is documented.

**Phase 2 — Database and PostGIS (2 pd).** *Goal:* schema applied and seeded. *Outputs:* seven migrations, seed users, repositories skeleton. *Files:* `database/migrations/*`, `database/seed/*`, `src/ews/db/*`, `scripts/migrate.py`, `tests/integration/test_schema.py`. *Depends on:* 0. *Tasks:* apply the DDL; seed one user per role; base repositories. *Tests:* all tables exist; every geometry column is typed; dispatch guard and append-only triggers fire. *Done when:* migrations are idempotent and tests pass in CI.

**Phase 3 — Geospatial preprocessing (6 pd).** *Goal:* zones, grid, terrain, drainage and exposure features. *Outputs:* `zones`, `grid_cells`, `terrain_features`, `drainage_*`, `population_grids`, `critical_facilities`, `shelters`, `roads`, `zone_static_features` (static E and V). *Files:* `src/ews/geo/*`, `scripts/build_grid.py`, `build_terrain.py`, `build_static_features.py`, `build_road_graph.py`, `tests/geo/*`. *Depends on:* 1, 2. *Tasks:* load wards and zones; build the grid; DEM to 25 m to derivatives to block reduction; clean drains, build nodes, compute the Manning proxy; mass-preserving population; land-cover fractions; OSM graph and facilities; shelters; compute static E and V; run the §8.5 checks. *Tests:* every §8.5 check; conservation tests. *Done when:* all wards have static features with a coverage report and a QGIS visual check.

**Phase 4 — Historical flood pipeline (4 pd).** *Goal:* labels, event table, susceptibility. *Outputs:* `historical_flood_events`, `flood_extents`, `event_features`, M1 candidate or fallback index, `S_cell` for all cells. *Files:* `scripts/build_event_table.py`, `train_susceptibility.py`, `src/ews/models/susceptibility.py`, notebooks 02 and 03. *Depends on:* 1, 3. *Tasks:* convert KML; inches to centimetres; assign events to cells and wards; build pseudo-absences; spatial block CV; rank-scale S. *Tests:* `hist_flood_freq` is absent from M1 inputs; the CV runs; the gate falls back to the index when positives are few. *Done when:* M1 metrics exist with their caveats and S is stored.

**Phase 5 — Rainfall pipeline (3 pd).** *Goal:* archive, forecast and replay series. *Outputs:* connectors, `stations`, rainfall tables filled, replay series for the demo event, blended-timeline builder. *Files:* `src/ews/ingest/connectors/open_meteo.py`, `imd.py`, `src/ews/features/rainfall.py`, `src/ews/models/rainfall_blend.py`. *Depends on:* 2. *Tasks:* hourly archive pull; bias correction to IMD daily; 15-minute disaggregation; forecast pull with cache fallback. *Tests:* UTC handling; disaggregation conserves totals; idempotent upsert; fallback to cache. *Done when:* the replay series is stored with provenance and the forecast connector works or its cached fallback is proven.

**Phase 6 — Sensor simulator (4 pd).** *Goal:* simulator and ingestion API. *Outputs:* 48 sensors posting through HTTP, QC flags, simulation control endpoints. *Files:* `src/ews/simulation/*`, `src/ews/api/routers/data.py`, `src/ews/quality/*`, `tests/sim/*`. *Depends on:* 2, 3 (placement), 5 (rainfall). *Tasks:* placement; reservoir model; faults; engine; keys; QC rules. *Tests:* determinism, fault rates, rain raises level. *Done when:* a scenario runs end to end into `water_level_observations`.

**Phase 7 — Forecasting model (4 pd).** *Goal:* M3 trained and registered. *Outputs:* `models/waterlevel_*`, `metrics.json`, a CANDIDATE then ACTIVE row. *Files:* `scripts/train_waterlevel.py`, `src/ews/models/waterlevel.py`, `src/ews/features/waterlevel.py`. *Depends on:* 6. *Tasks:* generate storms; group split; train point and quantile models; compare candidates; domain-shift test; register. *Tests:* no leakage; beats persistence on fixtures; artefact hash. *Done when:* the promotion gate of §11.2 passes and metrics are reported as simulation benchmarks.

**Phase 8 — Risk engine (4 pd).** *Goal:* pure engine, uncertainty, footprint, attribution. *Files:* `src/ews/risk/*`, `src/ews/explain/attribution.py`, `src/ews/geo/footprint.py`. *Depends on:* 3, 4, 7. *Tasks:* implement §12.3; Monte Carlo; confidence; footprint; Shapley. *Tests:* worked cases A to D; monotonicity; Shapley efficiency. *Done when:* the engine reproduces the §12.3 table and stores its config hash.

**Phase 9 — Agent system (5 pd).** *Goal:* six agents and the analysis graph. *Files:* `src/ews/agents/*`, `src/ews/tools/*`, `src/ews/contracts.py`. *Depends on:* 5, 6, 8. *Tasks:* contracts; agents; graph; fallbacks; run store. *Tests:* contract validation, routing, abstention, fallback. *Done when:* one command runs a full cycle on stored data and writes risk rows and evidence.

**Phase 10 — Explainability (3 pd).** *Files:* `src/ews/explain/{evidence,similarity,narrators,guard}.py`. *Depends on:* 9. *Tasks:* evidence registry; similar events; template narrator; optional LLM adapter; guard V1–V5. *Tests:* guard rejects invented numbers; LLM-off passes. *Done when:* every risk at MEDIUM or above has a validated explanation.

**Phase 11 — Decision engine (3 pd).** *Files:* `src/ews/policy/*`, `src/ews/alerts/drafts.py`, templates. *Depends on:* 9, 10. *Tasks:* policy rules; confidence caps; resource matcher; alert drafts. *Tests:* rule evaluation; caps; approval flags. *Done when:* HIGH and VERY\_HIGH wards yield drafts with recommendations.

**Phase 12 — Human approval (3 pd).** *Files:* `src/ews/oversight/*`, `src/ews/api/routers/alerts.py`. *Depends on:* 2, 11. *Tasks:* state machine; review endpoints; audit chain; versioning. *Tests:* T09, T10, T14. *Done when:* dispatch is impossible without an approving review, at both the API and the database.

**Phase 13 — Routing and shelters (4 pd).** *Files:* `src/ews/routing/*`, `src/ews/api/routers/routes.py`, `shelters.py`. *Depends on:* 3, 8. *Tasks:* load graph; edge risk; planner; safe-route score; fallback. *Tests:* blocked-edge avoidance; underpass handling; score ordering. *Done when:* the demo ward returns three routes with warnings.

**Phase 14 — Dashboard (8 pd).** *Files:* `web/src/*`. *Depends on:* 2 (mock API first), then 8–13. *Tasks:* 13 views, citizen view, SIMULATED badges, review panel, scenario controls. *Tests:* component tests; one Playwright smoke test. *Done when:* every view renders from the real API.

**Phase 15 — End-to-end integration (3 pd).** *Files:* `scripts/run_demo.py`, `scripts/e2e_demo.py`, `src/ews/learning/*`, `docs/DEMO.md`. *Depends on:* 12, 13, 14. *Tasks:* wire the learning loop; script the 16 steps. *Tests:* e2e. *Done when:* §37 runs from a clean state.

**Phase 16 — Testing and measurement (3 pd).** *Tasks:* close gaps in §31; run the nightly model tests; measure latencies; run `evaluate.py` to fill the “Achieved” column of §32. *Done when:* every number shown in slides is traceable to an evaluation output.

**Phase 17 — Demo hardening (3 pd).** *Tasks:* rehearse; offline mode (no map tiles, no LLM, cached forecast); pinned seeds; failure drills (kill a sensor, kill the LLM, drop the network); backup screen recording; align slides with actual outputs. *Done when:* the demo passes three consecutive runs from a clean `make up`.

## 36. Code Skeletons

The skeletons below are **representative**, not a finished implementation. They use only libraries named in §5. Where a third-party method name matters (pysheds, LangGraph, LightGBM) it should be checked against the installed version.

### 36.1 Build order, dependencies and first interfaces

| Order | Module | Why here | Depends on |
| --- | --- | --- | --- |
| 1 | `ews.config`, `ews.timeutil`, `ews.logging` | Everything imports them | none |
| 2 | `ews.contracts` | The shapes everything exchanges | none |
| 3 | `ews.db.connection`, migrations | Storage | config |
| 4 | `ews.quality.validators` | Ingestion needs them | contracts |
| 5 | `ews.ingest.*`, `api.routers.data` | Data in | db, quality |
| 6 | `ews.geo.*`, `scripts/build_*` | Static layers | db, config |
| 7 | `ews.features.*` | Model inputs | db, geo |
| 8 | `ews.risk.*` (pure) | The heart; testable alone | config only |
| 9 | `ews.explain.attribution` (pure) | Needs only the risk function | risk |
| 10 | `ews.simulation.*` | Feeds data through HTTP | config, api |
| 11 | `ews.models.*` | Forecaster, susceptibility | features |
| 12 | `ews.tools.*`, `ews.agents.*` | Orchestration | all above |
| 13 | `ews.policy.*`, `ews.alerts.*`, `ews.oversight.*` | Decision and gate | agents, db |
| 14 | `ews.routing.*` | Routes | geo, risk |
| 15 | `ews.learning.*` | Loop | db, models, risk |
| 16 | `ews.api.routers.*`, `web/` | Applications | services |

Interfaces to write **before** their implementations (`ews/interfaces.py`):

```python
from typing import Protocol

class BlobStore(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...

class NotificationGateway(Protocol):
    # returns a delivery status: SIMULATED_DELIVERED, SENT_SANDBOX or FAILED
    def send(self, channel: str, audience: str, text: dict, payload: dict) -> str: ...

class Narrator(Protocol):
    def narrate(self, facts: dict, allowed_evidence_ids: set) -> str: ...

class RoutePlanner(Protocol):
    def plan(self, origin_xy: tuple, zone_id: str, edge_risk: dict, max_routes: int = 3) -> list: ...
```

### 36.2 PostGIS connection

```python
# ews/db/connection.py
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_engine: Engine | None = None

def engine() -> Engine:
    global _engine
    if _engine is None:   # DATABASE_URL example: postgresql+psycopg://ews:***@db:5432/ews
        _engine = create_engine(os.environ['DATABASE_URL'], pool_size=10, max_overflow=5, pool_pre_ping=True)
    return _engine

@contextmanager
def tx():
    with engine().begin() as conn:      # commits on success, rolls back on error
        yield conn

def zones_geojson(conn, level: str = 'WARD') -> dict:
    rows = conn.execute(text('''
        SELECT zone_id, name, ST_AsGeoJSON(ST_Transform(geom, 4326), 6)::json AS geometry
        FROM zones WHERE level = :level'''), {'level': level}).mappings().all()
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': r['zone_id'], 'properties': {'name': r['name']}, 'geometry': r['geometry']}
        for r in rows]}

def ward_of_point(conn, lon: float, lat: float) -> str | None:
    return conn.execute(text('''
        SELECT zone_id FROM zones
        WHERE level = 'WARD'
          AND ST_Contains(geom, ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32644))
        LIMIT 1'''), {'lon': lon, 'lat': lat}).scalar()
```

### 36.3 FastAPI application and the water-level ingestion route

```python
# ews/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from ews.config import settings
from ews.db.connection import engine
from ews.api.routers import data, zones, risk, alerts, routes, shelters, events, feedback, models, sim

app = FastAPI(title='Chennai Flood EWS', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=['GET', 'POST'], allow_headers=['*'])
for r in (data, zones, risk, alerts, routes, shelters, events, feedback, models, sim):
    app.include_router(r.router, prefix='/api/v1')

@app.get('/api/v1/health')
def health():
    try:
        with engine().connect() as c:
            c.execute(text('SELECT 1'))
    except Exception:
        return JSONResponse({'status': 'DEGRADED', 'db': 'DOWN'}, status_code=503)
    return {'status': 'OK', 'db': 'OK', 'version': app.version}
```

```python
# ews/api/routers/data.py (excerpt)
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Header, HTTPException
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import text
from ews.db.connection import tx
from ews.api.deps import sensor_for_key
from ews.quality.validators import validate_water_level

router = APIRouter(tags=['data'])

class WaterLevelReading(BaseModel):
    sensor_id: str
    observed_at: AwareDatetime
    level_cm: float | None = None
    rise_rate_cm_min: float | None = None
    battery_pct: float | None = Field(default=None, ge=0, le=100)
    signal_dbm: float | None = Field(default=None, ge=-130, le=0)
    device_status: str | None = None

class WaterLevelBatch(BaseModel):
    readings: list[WaterLevelReading] = Field(max_length=1000)
    scenario_run_id: UUID | None = None

UPSERT = text('''
INSERT INTO water_level_observations
  (sensor_id, observed_at, level_cm, rise_rate_cm_min, battery_pct, signal_dbm, device_status,
   qc_flags, quality, is_simulated, scenario_run_id)
VALUES (:sensor_id, :observed_at, :level_cm, :rise, :battery, :signal, :status,
        :flags, :quality, :sim, :run)
ON CONFLICT (sensor_id, observed_at) DO UPDATE
  SET level_cm = EXCLUDED.level_cm,
      qc_flags = array_append(water_level_observations.qc_flags, 'REVISED')
  WHERE water_level_observations.level_cm IS DISTINCT FROM EXCLUDED.level_cm
RETURNING (xmax = 0) AS inserted''')

@router.post('/data/water-level')
def ingest_water_level(batch: WaterLevelBatch, x_sensor_key: str = Header(...)):
    now = datetime.now(timezone.utc)
    results = []
    with tx() as conn:
        sensor = sensor_for_key(conn, x_sensor_key)            # None when the key is unknown
        if sensor is None:
            raise HTTPException(401, 'invalid sensor key')
        for i, r in enumerate(batch.readings):
            if r.sensor_id != sensor['sensor_id']:
                raise HTTPException(403, 'key does not belong to this sensor')
            flags, quality, reject = validate_water_level(r, sensor, now)
            if reject:
                results.append({'index': i, 'status': 'REJECTED', 'reason': reject})
                continue
            row = conn.execute(UPSERT, {
                'sensor_id': r.sensor_id, 'observed_at': r.observed_at, 'level_cm': r.level_cm,
                'rise': r.rise_rate_cm_min, 'battery': r.battery_pct, 'signal': r.signal_dbm,
                'status': r.device_status, 'flags': flags, 'quality': quality,
                'sim': bool(sensor['is_simulated']), 'run': batch.scenario_run_id}).first()
            status = 'DUPLICATE_IGNORED' if row is None else ('CREATED' if row[0] else 'UPDATED')
            results.append({'index': i, 'status': status, 'flags': flags})
    return {'accepted': sum(x['status'] in ('CREATED', 'UPDATED') for x in results),
            'rejected': sum(x['status'] == 'REJECTED' for x in results),
            'flagged': sum(bool(x.get('flags')) for x in results), 'items': results}
```

### 36.4 Validation and rainfall ingestion

```python
# ews/quality/validators.py
from datetime import datetime, timedelta

def validate_rainfall(r, now: datetime, historical: bool = False):
    # returns (flags, reject_reason); r has period_start, period_end, depth_mm
    flags: list[str] = []
    if r.period_end <= r.period_start:
        return flags, 'period_end must be after period_start'
    hours = (r.period_end - r.period_start).total_seconds() / 3600.0
    if hours > 24:
        return flags, 'period longer than 24 h'
    if r.period_end > now + timedelta(minutes=5):
        return flags, 'period_end is in the future'
    if r.depth_mm is None:
        flags.append('MISSING')                      # stays null, never coerced to zero
    else:
        rate = r.depth_mm / hours                    # mm per hour equivalent
        if rate > 300:
            return flags, 'rate above 300 mm per hour equivalent'
        if rate > 150:
            flags.append('OUT_OF_RANGE_HIGH')
    if not historical and now - r.period_end > timedelta(minutes=15):
        flags.append('LATE')
    return flags, None

def validate_water_level(r, sensor: dict, now: datetime):
    # returns (flags, quality, reject_reason)
    flags: list[str] = []
    if r.level_cm is None:
        flags.append('MISSING')
    elif not (-5.0 <= r.level_cm <= sensor['drain_depth_cm'] + 100.0):
        return flags, 0.0, 'level outside plausible range'
    if r.observed_at > now + timedelta(minutes=2):
        flags.append('CLOCK_SKEW')
    elif now - r.observed_at > timedelta(minutes=10):
        flags.append('LATE')
    quality = 1.0
    if 'MISSING' in flags:
        quality = 0.0
    if (r.battery_pct is not None and r.battery_pct < 15) or (r.signal_dbm is not None and r.signal_dbm < -105):
        flags += ['LOW_BATTERY' if (r.battery_pct is not None and r.battery_pct < 15) else 'WEAK_SIGNAL']
        quality *= 0.6
    if 'LATE' in flags:
        quality *= 0.8
    return flags, quality, None
```

The rainfall route follows the same pattern as the water-level route, with `ON CONFLICT (station_id, period_start, period_end, kind) DO UPDATE ... WHERE depth_mm IS DISTINCT FROM EXCLUDED.depth_mm` so that identical repeats return no row (`DUPLICATE_IGNORED`) and changed values are flagged `REVISED`. Spike, stuck and neighbour-disagreement checks (§9.4) run in a separate pass over recent rows, because they need history.

### 36.5 Sensor simulator core

```python
# ews/simulation/hydrology.py
from dataclasses import dataclass, field
import numpy as np

def scs_runoff_mm(p_cum_mm: float, cn: float) -> float:
    s = 25400.0 / cn - 254.0
    ia = 0.2 * s
    return 0.0 if p_cum_mm <= ia else (p_cum_mm - ia) ** 2 / (p_cum_mm - ia + s)

@dataclass
class SensorState:
    sensor_id: str
    depth_cm: float
    cn: float              # 60 + 38 * built_fraction
    kappa: float           # cm of drain depth per mm of runoff
    lag_min: int
    k_out: float           # outflow constant per minute
    blockage: float
    tidal: bool
    spatial_factor: float = 1.0
    h: float = 0.0         # level inside the drain, cm
    pond: float = 0.0      # ponding above the drain, cm
    p_cum: float = 0.0     # cumulative rainfall at the sensor, mm
    q_hist: list = field(default_factory=list)
    flooded: bool = False  # ground truth: overflow occurred at least once

    def __post_init__(self):
        self.q_hist = [0.0] * (self.lag_min + 1)

def step(s: SensorState, rain_mm_min: float, minute: int, rng: np.random.Generator) -> float:
    before = scs_runoff_mm(s.p_cum, s.cn)
    s.p_cum += rain_mm_min * s.spatial_factor
    s.q_hist.append(scs_runoff_mm(s.p_cum, s.cn) - before)   # runoff generated this minute, mm
    inflow = s.kappa * s.q_hist.pop(0)                       # delayed by lag_min minutes, cm
    tide = 1.0 - (0.3 * max(0.0, np.sin(2 * np.pi * minute / (12.42 * 60))) if s.tidal else 0.0)
    s.h = max(0.0, s.h + inflow - s.k_out * s.h * (1.0 - s.blockage) * tide)
    if s.h > s.depth_cm:
        s.pond += s.h - s.depth_cm
        s.h = s.depth_cm
        s.flooded = True
    s.pond *= 0.98
    return max(0.0, s.h + s.pond + rng.normal(0.0, 0.5))
```

```python
# ews/simulation/engine.py (outline)
import time
import numpy as np

class SimulationEngine:
    def __init__(self, scenario, sensors, rain_mm_per_min, faults, client, seed: int):
        self.rng = np.random.default_rng(seed)          # one generator: runs are reproducible
        self.scenario, self.sensors, self.rain = scenario, sensors, rain_mm_per_min
        self.faults, self.client = faults, client

    def run(self, speed: float, start_minute: int = 0):
        for minute in range(start_minute, len(self.rain)):
            for s in self.sensors:
                level = step(s, self.rain[minute], minute, self.rng)
                reading = self.faults.apply(s, minute, level, self.rng)   # None = dropped packet
                if reading is not None:
                    self.client.post_water_level(s.sensor_id, [reading])  # same endpoint as a real device
            self.client.update_clock(minute)
            time.sleep(60.0 / speed)
```

### 36.6 Feature engineering

```python
# ews/features/waterlevel.py
import numpy as np
import pandas as pd

def rise_rate(levels: pd.Series, window_min: int) -> float | None:
    # least-squares slope in cm per minute over the last window_min minutes of valid readings
    s = levels.dropna()
    if s.empty:
        return None
    recent = s[s.index > s.index.max() - pd.Timedelta(minutes=window_min)]
    if len(recent) < 3:
        return None
    t = (recent.index - recent.index[0]).total_seconds().to_numpy() / 60.0
    return float(np.polyfit(t, recent.to_numpy(dtype=float), 1)[0])

def rain_window(timeline: pd.Series, as_of: pd.Timestamp, minutes: int, max_missing: float = 0.2):
    # timeline: 15-minute rainfall depths (mm) indexed by period end, UTC; NaN = missing
    w = timeline[(timeline.index > as_of - pd.Timedelta(minutes=minutes)) & (timeline.index <= as_of)]
    expected = max(1, minutes // 15)
    if len(w) == 0 or w.isna().sum() / expected > max_missing:
        return None                                   # caller sets the MISSING_RAIN flag
    return float(w.sum(skipna=True))                  # tolerated gaps are skipped, not filled

def forecaster_features(levels: pd.Series, rain: pd.Series, fc: pd.Series, as_of: pd.Timestamp, site: dict) -> dict:
    f = {'level_cm': levels.asof(as_of)}
    for lag in (1, 5, 10, 15, 30, 60):
        f[f'lag_{lag}'] = levels.asof(as_of - pd.Timedelta(minutes=lag))
    for w in (5, 15, 30, 60):
        f[f'rise_{w}'] = rise_rate(levels[levels.index <= as_of], w)
    for w in (15, 30, 60, 180):
        f[f'rain_{w}'] = rain_window(rain, as_of, w)
    for w in (15, 30, 60):
        f[f'fc_{w}'] = rain_window(fc, as_of + pd.Timedelta(minutes=w), w)    # forecast part only
    f.update({k: site[k] for k in ('cn', 'depth_cm', 's_ward', 'built_frac')})
    return f
```

### 36.7 Forecasting model (M3)

```python
# ews/models/waterlevel.py
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

HORIZONS = (15, 30, 60)

def split_by_storm(df: pd.DataFrame, seed: int = 42):
    # 60 / 20 / 20 by storm: rows of one storm never appear in two sets
    tr, rest = next(GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=seed).split(df, groups=df['storm_id']))
    rest_df = df.iloc[rest]
    va, te = next(GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=seed).split(rest_df, groups=rest_df['storm_id']))
    return df.iloc[tr], rest_df.iloc[va], rest_df.iloc[te]

def train(df: pd.DataFrame, cols: list, params: dict, seed: int) -> dict:
    # one row per (storm, sensor, time); targets dh_15, dh_30, dh_60 = level(t + h) - level(t)
    models = {}
    for h in HORIZONS:
        y = df[f'dh_{h}']
        models[h] = {
            'mean': lgb.LGBMRegressor(objective='regression', random_state=seed, **params).fit(df[cols], y),
            'q10': lgb.LGBMRegressor(objective='quantile', alpha=0.1, random_state=seed, **params).fit(df[cols], y),
            'q90': lgb.LGBMRegressor(objective='quantile', alpha=0.9, random_state=seed, **params).fit(df[cols], y)}
    return models

def evaluate(models: dict, df: pd.DataFrame, cols: list) -> dict:
    out = {}
    for h in HORIZONS:
        y = df[f'dh_{h}'].to_numpy()
        pred = models[h]['mean'].predict(df[cols])
        rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
        rmse_persistence = float(np.sqrt(np.mean(y ** 2)))     # persistence predicts a change of zero
        out[h] = {'mae': float(np.mean(np.abs(pred - y))), 'rmse': rmse,
                  'skill_vs_persistence': 1.0 - rmse / rmse_persistence}
    return out

def predict(models: dict, feats: pd.DataFrame, level_now: float, depth_cm: float) -> dict:
    res = {}
    for h, m in models.items():
        lo, mid, hi = (float(m[k].predict(feats)[0]) for k in ('q10', 'mean', 'q90'))
        lo, hi = min(lo, hi), max(lo, hi)                       # guard against quantile crossing
        clip = lambda d: float(np.clip(level_now + d, 0.0, depth_cm + 100.0))
        res[h] = {'p10': clip(lo), 'value': clip(mid), 'p90': clip(hi)}
    return res

def save(models: dict, path: str) -> None:
    joblib.dump(models, path)       # path = models/waterlevel/<version>/model.joblib; SHA-256 goes to model_versions
```

### 36.8 Risk engine (pure functions)

```python
# ews/risk/engine.py  (no I/O; every number comes from RiskParams or the inputs)
from dataclasses import dataclass, replace
import numpy as np

def ramp(x: float, lo: float, hi: float) -> float:
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))

@dataclass(frozen=True)
class RiskParams:                  # defaults mirror config/risk.yaml; all are [ASSUMPTION] values
    r60: tuple = (20.0, 90.0)
    r180: tuple = (50.0, 200.0)
    a72: tuple = (30.0, 150.0)
    a72_boost: float = 0.25
    fill: tuple = (0.5, 1.0)
    rise: tuple = (0.3, 2.0)
    rise_gate: tuple = (0.25, 0.7)
    i_design: float = 50.0
    blockage: float = 0.15
    d_est: tuple = (0.6, 1.2)
    model_trust: float = 0.7
    s0: float = 0.25
    gate: tuple = (0.10, 0.40)
    w_h: float = 0.4
    w_e: float = 0.3
    w_v: float = 0.3
    cuts: tuple = (0.25, 0.50, 0.85)
    high_min_h: float = 0.40
    vhigh_min_h: float = 0.70
    onset_h: float = 0.60

@dataclass(frozen=True)
class WardInputs:
    r60: float                 # mm; blended timeline ending at t + tau
    r180: float
    a72: float                 # antecedent rainfall, mm
    i15_max: float             # mm per hour; maximum 15-minute intensity in the hour ending at t + tau
    built_frac: float
    phi: float | None          # forecast fill ratio; None when no valid sensor
    rise: float | None         # forecast rise, cm per minute
    c_s: float                 # sensor confidence 0..1
    s_ward: float
    e: float
    v: float

def trigger(x: WardInputs, p: RiskParams) -> float:
    t = max(ramp(x.r60, *p.r60), ramp(x.r180, *p.r180))
    return min(1.0, t * (1.0 + p.a72_boost * ramp(x.a72, *p.a72)))

def drain_stress(x: WardInputs, p: RiskParams, tau_min: int) -> float:
    if x.phi is not None and tau_min <= 60:                    # sensor route
        d_s = max(ramp(x.phi, *p.fill), ramp(x.rise or 0.0, *p.rise) * ramp(x.phi, *p.rise_gate))
        return x.c_s * d_s
    c_w = 0.15 + 0.75 * x.built_frac                           # model route
    return p.model_trust * ramp(c_w * x.i15_max / (p.i_design * (1.0 - p.blockage)), *p.d_est)

def hazard_from_components(t_prime: float, s_ward: float, d_eff: float, s0: float = 0.25) -> float:
    return 1.0 - (1.0 - t_prime * (s0 + (1.0 - s0) * s_ward)) * (1.0 - d_eff)   # used by test cases A to D

def hazard(x: WardInputs, p: RiskParams, tau_min: int) -> float:
    return hazard_from_components(trigger(x, p), x.s_ward, drain_stress(x, p, tau_min), p.s0)

def risk_score(h: float, e: float, v: float, p: RiskParams) -> float:
    return ramp(h, *p.gate) * (p.w_h * h + p.w_e * e + p.w_v * v)

def risk_level(r: float, h: float, confidence_level: str, p: RiskParams) -> str:
    lv = 0 if r < p.cuts[0] else 1 if r < p.cuts[1] else 2 if r < p.cuts[2] else 3
    if lv == 3 and (h < p.vhigh_min_h or confidence_level == 'LOW'):
        lv = 2
    if lv == 2 and h < p.high_min_h:
        lv = 1
    return ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')[lv]

def time_to_impact(h_by_tau: dict, p: RiskParams):
    for tau in sorted(h_by_tau):
        if h_by_tau[tau] >= p.onset_h:
            return tau              # 0 means already under way; None means none within 120 minutes
    return None

def monte_carlo_h(x: WardInputs, p: RiskParams, tau_min: int, n: int = 200, seed: int = 0):
    rng = np.random.default_rng(seed)
    hs = []
    for _ in range(n):
        f = rng.uniform(0.8, 1.2, size=4)                      # plus or minus 20 % on key parameters
        q = replace(p, r60=(p.r60[0] * f[0], p.r60[1] * f[0]), r180=(p.r180[0] * f[1], p.r180[1] * f[1]),
                    s0=float(np.clip(p.s0 * f[2], 0.05, 0.6)), fill=(p.fill[0] * f[3], p.fill[1] * f[3]))
        hs.append(hazard(x, q, tau_min))
    return float(np.percentile(hs, 10)), float(np.percentile(hs, 90))
```

### 36.9 Explanation engine

Exact Shapley attribution (§16.2):

```python
# ews/explain/attribution.py
from itertools import combinations
from math import factorial

def shapley(value_fn, factors: list, actual: dict, baseline: dict) -> dict:
    # value_fn(inputs: dict) -> float builds WardInputs from the factor dict and returns risk_score.
    # Exact for up to about 10 factors (2^n evaluations, cached).
    n = len(factors)
    cache: dict = {}
    def v(coalition: frozenset) -> float:
        if coalition not in cache:
            cache[coalition] = value_fn({k: (actual[k] if k in coalition else baseline[k]) for k in factors})
        return cache[coalition]
    phi = {}
    for i in factors:
        others = [f for f in factors if f != i]
        total = 0.0
        for k in range(n):
            w = factorial(k) * factorial(n - k - 1) / factorial(n)
            for c in combinations(others, k):
                s = frozenset(c)
                total += w * (v(s | {i}) - v(s))
        phi[i] = total
    return phi            # sum(phi.values()) == value_fn(actual) - value_fn(baseline)

def to_contributions(phi: dict) -> dict:
    pos = {k: max(x, 0.0) for k, x in phi.items()}
    total = sum(pos.values()) or 1.0
    return {k: round(100.0 * x / total, 1) for k, x in pos.items()}
```

Narrative template and guard (§16.3):

```python
# ews/explain/guard.py
import re

NUM = re.compile('[0-9]+(?:[.][0-9]+)?')
EVID = re.compile('EV-[A-Z]+-[A-Za-z0-9_-]+')
INSTRUCTION = re.compile('(?i)(?<![a-z])(evacuate|avoid|move|stay|do not|go to|leave)(?![a-z])')

def flatten_numbers(obj) -> set:
    out: set = set()
    if isinstance(obj, dict):
        for v in obj.values():
            out |= flatten_numbers(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out |= flatten_numbers(v)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out |= {str(obj), format(obj, '.0f'), format(obj, '.1f'), format(obj, '.2f')}
    elif isinstance(obj, str):
        out |= set(NUM.findall(obj))
    return out

def validate_narrative(text: str, facts: dict, allowed_ids: set) -> list:
    errors = []
    allowed = flatten_numbers(facts)
    errors += ['V3 number not in facts: ' + n for n in NUM.findall(text) if n not in allowed]
    errors += ['V1 unknown evidence id: ' + e for e in EVID.findall(text) if e not in allowed_ids]
    if INSTRUCTION.search(text):
        errors.append('V5 instruction pattern found')
    return errors                         # empty list means the narrative is accepted

def template_narrative(facts: dict) -> str:
    drivers = '; '.join('{} ({:.0f} percent)'.format(f['label'], f['pct']) for f in facts['top_factors'][:3])
    note = ' Inputs include simulated sensors.' if facts['uses_simulated_inputs'] else ''
    return ('Ward {} is assessed at {} risk (flood likelihood index {:.2f}, confidence {}). '
            'Main drivers: {}.{}').format(facts['ward_no'], facts['level'], facts['probability'],
                                          facts['confidence_level'], drivers, note)
```

### 36.10 LangGraph workflow

```python
# ews/agents/graph.py  (check the API against the installed langgraph version)
from typing import TypedDict
from langgraph.graph import END, START, StateGraph

class RunState(TypedDict, total=False):
    request: dict
    bundle: dict
    forecasts: list
    risks: list
    explanations: list
    drafts: list
    missing: list
    retried: bool

def route_after_qa(s: RunState) -> str:
    if not s.get('missing'):
        return 'forecast'
    return 'abstain' if s.get('retried') else 'fallback_data'    # fallback node sets retried = True

def route_after_risk(s: RunState) -> str:
    levels = {r['risk_level'] for r in s.get('risks', []) if r.get('risk_level')}
    return 'explain' if levels & {'MEDIUM', 'HIGH', 'VERY_HIGH'} else 'log_only'

def build_analysis_graph(a):
    g = StateGraph(RunState)
    g.add_node('plan', a.orchestrator.plan)
    g.add_node('retrieve', a.data.retrieve)
    g.add_node('qa_gate', a.orchestrator.qa_gate)
    g.add_node('fallback_data', a.data.fallback)
    g.add_node('forecast', a.forecast.run)
    g.add_node('risk', a.risk.run)
    g.add_node('explain', a.rca.run)
    g.add_node('decide', a.decision.run)
    g.add_node('policy_check', a.decision.policy_check)
    g.add_node('persist_drafts', a.decision.persist)
    g.add_node('log_only', a.orchestrator.log_only)
    g.add_node('abstain', a.orchestrator.abstain)
    g.add_edge(START, 'plan')
    g.add_edge('plan', 'retrieve')
    g.add_edge('retrieve', 'qa_gate')
    g.add_conditional_edges('qa_gate', route_after_qa,
                            {'forecast': 'forecast', 'fallback_data': 'fallback_data', 'abstain': 'abstain'})
    g.add_edge('fallback_data', 'qa_gate')
    g.add_edge('forecast', 'risk')
    g.add_conditional_edges('risk', route_after_risk, {'explain': 'explain', 'log_only': 'log_only'})
    g.add_edge('explain', 'decide')
    g.add_edge('decide', 'policy_check')
    g.add_edge('policy_check', 'persist_drafts')
    for terminal in ('persist_drafts', 'log_only', 'abstain'):
        g.add_edge(terminal, END)
    return g.compile()
```

Each node function takes the state dictionary and returns a dictionary of updates. The `dispatch_graph` is built the same way with the nodes `load_approved`, `routes_and_resources`, `notify`, `schedule_outcome_capture`.

### 36.11 Alert engine: state machine, approval, dispatch, audit chain

```python
# ews/oversight/state_machine.py
ALLOWED = {
    'DRAFT': {'AI_GENERATED', 'CANCELLED'},
    'AI_GENERATED': {'PENDING_REVIEW', 'CANCELLED'},
    'PENDING_REVIEW': {'APPROVED', 'REJECTED', 'REQUEST_CHANGES', 'EXPIRED', 'CANCELLED'},
    'REQUEST_CHANGES': {'REANALYSIS', 'CANCELLED'},
    'REANALYSIS': {'PENDING_REVIEW', 'CANCELLED'},
    'APPROVED': {'DISPATCHED', 'CANCELLED'},
    'DISPATCHED': {'ACTIVE', 'CANCELLED'},
    'ACTIVE': {'RESOLVED', 'CANCELLED'},
}
APPROVER_ROLES = {'ADVISORY': {'MUNICIPAL_OPERATOR', 'EMERGENCY_COORDINATOR'},
                  'WARNING': {'EMERGENCY_COORDINATOR'}, 'URGENT': {'EMERGENCY_COORDINATOR'}}

class ConflictError(Exception):
    pass

def transition(current: str, new: str) -> str:
    if new not in ALLOWED.get(current, set()):
        raise ValueError('illegal transition ' + current + ' to ' + new)
    return new

def approve(conn, alert: dict, review, role: str) -> None:      # review is a validated HumanReview
    if role not in APPROVER_ROLES[alert['severity']]:
        raise PermissionError('role may not approve this severity')
    if review.alert_version != alert['version']:
        raise ConflictError('stale alert version')
    if review.decision == 'APPROVE_WITH_CHANGES':                  # lower severity or narrow scope only
        alert = alerts_repo.apply_modifications(conn, alert, review.modifications)   # version + 1
        review = review.model_copy(update={'alert_version': alert['version']})
    reviews_repo.insert(conn, review)                              # append-only table
    alerts_repo.set_status(conn, alert['alert_id'], transition(alert['status'], 'APPROVED'))
    audit.append(conn, review.reviewer_id, role, 'ALERT_APPROVED', 'alert', str(alert['alert_id']),
                 {'version': alert['version'], 'decision': review.decision})
```

```python
# ews/alerts/dispatcher.py
import time

class SimulatedGateway:                                            # implements NotificationGateway
    def send(self, channel: str, audience: str, text: dict, payload: dict) -> str:
        log.info('notification.simulated', channel=channel, audience=audience)
        return 'SIMULATED_DELIVERED'                               # never claims real delivery

def dispatch(conn, alert: dict, gateways: dict) -> None:
    if alert['status'] != 'APPROVED':
        raise ValueError('only APPROVED alerts can be dispatched')
    for channel, audience in recipients_for(alert):
        status = 'FAILED'
        for attempt in range(3):
            try:
                status = gateways[channel].send(channel, audience, alert['locale_texts'], alert['payload'])
                break
            except Exception:
                time.sleep(2 ** attempt)
        recipients_repo.record(conn, alert['alert_id'], channel, audience, status)   # idempotent on the triple
    alerts_repo.set_status(conn, alert['alert_id'], 'DISPATCHED')   # the database guard re-checks the review
```

```python
# ews/oversight/audit.py
import hashlib
import json
from sqlalchemy import text

def canonical(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True, separators=(',', ':'), default=str)

def append(conn, actor_id, actor_role, action, entity_type, entity_id, detail) -> None:
    conn.execute(text('SELECT pg_advisory_xact_lock(7001)'))       # serialise appends: the chain cannot fork
    prev = conn.execute(text('SELECT row_hash FROM audit_logs ORDER BY audit_id DESC LIMIT 1')).scalar() or '0' * 64
    entry = {'actor_id': str(actor_id), 'actor_role': actor_role, 'action': action,
             'entity_type': entity_type, 'entity_id': entity_id, 'detail': detail}
    row_hash = hashlib.sha256((prev + canonical(entry)).encode('utf-8')).hexdigest()
    conn.execute(text('''INSERT INTO audit_logs
        (actor_id, actor_role, action, entity_type, entity_id, detail, prev_hash, row_hash)
        VALUES (:a, :r, :act, :et, :eid, CAST(:d AS jsonb), :p, :h)'''),
        {'a': actor_id, 'r': actor_role, 'act': action, 'et': entity_type, 'eid': entity_id,
         'd': json.dumps(detail, default=str), 'p': prev, 'h': row_hash})
```

## 37. Chennai End-to-End Demo

### 37.1 Scenario and preconditions

**Scenario `chennai_2015_replay_demo`.** Rainfall is a replay of the hourly reanalysis series (Open-Meteo archive, bias-corrected to IMD daily totals) for the NE-monsoon event of 30 November to 2 December 2015. The demo window is the 12 hours with the highest accumulated rainfall in that series, preceded by a 3-hour lead-in, run at 120 × real time (15 simulated hours take 7.5 minutes). Sensors and gauges are simulated \[SIM\]; the forecast shown to the system is the labelled scenario forecast (§9.2). The reanalysis underestimates local peaks and the demo says so.

**Preconditions (all produced by `make demo-prepare`):** static layers loaded (§3 of the roadmap); M1 trained **without** the replayed event's labels (hindcast integrity, §6.5) and M3 ACTIVE; 48 sensors registered; the demo cluster and ward chosen by the §2.4 rule; a **contrast ward** (susceptibility in the bottom quartile, exposure at or above the cluster median); seeded users for each role; Mailpit running; policy `proto-0.1` active.

**Clock rule (applies to §9 and §36).** During a replay, “now” is the simulation clock stored in `sim_runs.sim_clock`. Validators, freshness checks, late and clock-skew flags and the analysis `as_of` all take the time from a `Clock` object: the system clock in live mode, the simulation clock when a request carries a `scenario_run_id`. The skeletons in §36 pass `datetime.now(timezone.utc)` for brevity; routers must pass `clock.now(scenario_run_id)` instead, or every replayed reading would be flagged LATE.

### 37.2 The sixteen steps

| Step | What the audience sees | System action | APIs and data |
| --- | --- | --- | --- |
| 1 Select Chennai | City Overview: wards at LOW or “not assessed”, data chips (static layers loaded, models ACTIVE, policy PROTOTYPE, simulation idle) | Health and registry check | `GET /health`, `GET /zones?with_risk=true`, `GET /models` |
| 2 Select the demonstration zone | Demo cluster and ward highlighted with the rule outcome; Zone Details shows S, E, V, drain-capacity index, past events | Read static features | `GET /zones/{zone_id}`, `/events`, `/shelters?zone_id=`, `/sensors?zone_id=` |
| 3 Load rainfall | Live Rainfall shows 72 h antecedent series, the scenario rain preview, source chips (REANALYSIS, SIM) | Create the run in PENDING | `GET /data/rainfall`, `POST /sim/scenario` with `{scenario_id: chennai_2015_replay_demo, seed: 42, speed: 120}` |
| 4 Rainfall intensifies | Hyetograph builds in simulated time; clock runs at 120 × | Resume; gauges post every 5 simulated minutes; analysis every 10 | `POST /sim/{run_id}/control` with `{action: resume}`; `POST /data/rainfall` |
| 5 Sensor levels rise | Water Levels: fill ratios climb; a sensor goes STUCK and is flagged; a zone-wide outage greys sensors | Per-sensor posts every minute; QC flags | `POST /data/water-level`, `GET /data/water-level`, `GET /sensors` |
| 6 Forecast continues the rise | Level chart with the 15, 30 and 60 minute forecast and its interval; tier chip S | M3 forecast per sensor | `POST /forecast` (also run inside each cycle) |
| 7 Risk engine scores the zone | Risk card: H, E, V, R, interval, confidence, time to impact | Analysis cycle | `POST /risk/analyze` (worker-triggered), `GET /risk/{zone_id}` |
| 8 Map turns high | Demo ward moves up through the levels; the contrast ward stays lower despite the same rain; horizon slider shows +30 and +60 | Read latest risk by horizon | `GET /risk?horizon_min=30` |
| 9 RCA explains why | Shapley bars, evidence IDs with links, similar events (with the number of events compared), narrative chip TEMPLATE | Explanation validated | `GET /explanations/{risk_id}` |
| 10 Decision agent proposes | Recommendation list: public warning, prepare routes, open shelters (and evacuation or deployment if VERY\_HIGH); draft in PENDING\_REVIEW | Policy evaluated | `GET /alerts`, `GET /alerts/{id}` |
| 11 Human approval | Review panel; Approve disabled until the three boxes are ticked; an operator attempt on a WARNING returns 403; the coordinator approves | Review stored; audit row | `POST /alerts/{id}/approve` |
| 12 Alert generated | Delivery log: dashboard and municipal view, email in Mailpit, SMS and IVRS shown as SIMULATED on the phone mock | `dispatch_graph` | `GET /alerts/{id}` |
| 13 Route calculated | Three routes with safe-route score, ETA, warnings; an underpass avoided; shelter capacity shown as unknown where it is | Risk-weighted Dijkstra | `GET /routes?zone_id=`, `GET /shelters` |
| 14 Outcome loaded | “Load outcomes” attaches the real observed flooding for the event (historical layer) and the simulator ground truth, each labelled | Outcome rows | `POST /feedback` |
| 15 Prediction compared with outcome | Predicted footprint against observed cells; POD, false-alarm ratio, CSI, Brier, lead time with counts | Evaluation | `POST /learning/run` with `{mode: evaluate}` |
| 16 Learning updates metrics | Calibration candidate with before and after Brier, ECE and reliability diagram, computed out-of-sample; promotion shown but left to a human | Recalibrate | `POST /learning/run` with `{mode: recalibrate}`, `GET /models` |

### 37.3 Presenter rules

Say, on screen or aloud: the rainfall is a replay of reanalysis data; the sensors are simulated and use the same endpoint real devices would; the likelihood is an index until calibrated; the susceptibility model was trained without the replayed event; the outcome comparison for this event uses real observed layers; learning is a controlled, human-gated step. Use numbers the system produces during the run, never numbers from the conceptual diagrams.

### 37.4 Backup plan

`python scripts/run_demo.py --record` stores every API response of a good run; the UI's demo-cache mode replays them without the backend. Rehearse offline mode (no map tiles, LLM off, cached forecast), a killed sensor, a killed LLM and a dropped network. Keep a screen recording of a full run.

## 38. Deployment

### 38.1 Targets

**A. Laptop (the live demo):** Docker Compose, 16 GB RAM recommended (8 GB is enough with the LLM off), about 10 GB of disk for data. **B. Single cloud VM (remote access for evaluators):** the same Compose file behind a TLS reverse proxy, firewall allowing only 443 and SSH, nightly `pg_dump`, `restart: unless-stopped`. No Kubernetes.

### 38.2 Compose skeleton

```
services:
  db:
    image: postgis/postgis:16-3.4
    environment: {POSTGRES_DB: ews, POSTGRES_USER: ews, POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: [CMD-SHELL, pg_isready -U ews], interval: 5s, retries: 10}
    restart: unless-stopped
  api:
    build: {context: ., dockerfile: docker/api.Dockerfile}
    env_file: .env
    depends_on: {db: {condition: service_healthy}}
    volumes: ['./config:/app/config:ro', './models:/app/models', './data:/app/data', './runs:/app/runs']
    ports: ['8000:8000']
    command: sh -c 'python scripts/migrate.py && uvicorn ews.api.main:app --host 0.0.0.0 --port 8000'
    restart: unless-stopped
  worker:
    build: {context: ., dockerfile: docker/api.Dockerfile}
    env_file: .env
    depends_on: {db: {condition: service_healthy}}
    volumes: ['./config:/app/config:ro', './models:/app/models', './data:/app/data', './runs:/app/runs']
    command: python -m ews.worker
    restart: unless-stopped
  web:
    build: {context: ./web, dockerfile: ../docker/web.Dockerfile}
    ports: ['8080:80']
    depends_on: [api]
  mailpit:
    image: axllent/mailpit
    profiles: [demo]
    ports: ['8025:8025', '1025:1025']
  ollama:
    image: ollama/ollama
    profiles: [llm]
    volumes: ['ollama:/root/.ollama']
    ports: ['11434:11434']
volumes: {pgdata: {}, ollama: {}}
```

### 38.3 Makefile targets

`make up` (compose up), `make seed` (users, sources, resources), `make data` (acquire and process static layers: Phase 1 and 3 scripts), `make train` (M1, M3), `make demo-prepare`, `make demo` (start the scenario and open the UI), `make test`, `make e2e`, `make repro` (rebuild from the manifest).

### 38.4 CI workflow skeleton

```
name: ci
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      db:
        image: postgis/postgis:16-3.4
        env: {POSTGRES_PASSWORD: ci, POSTGRES_DB: ews}
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 5s --health-retries 10
    env:
      DATABASE_URL: postgresql+psycopg://postgres:ci@localhost:5432/ews
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5        # pin to the current major versions of all actions
      - run: uv sync --all-groups
      - run: uv run ruff check .
      - run: uv run mypy src/ews/risk src/ews/agents src/ews/api
      - run: uv run python scripts/migrate.py
      - run: uv run pytest -m 'not slow' --cov=ews
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: 20}
      - run: cd web && npm ci && npm run build
```

### 38.5 Release and backup

Tag releases (`v1.0-demo`), build images from the tag, and let the `api` container run the idempotent migration on start. Back up with `pg_dump` and archive `data/MANIFEST.yaml`, `config/` and `models/` with the tag. Restoring on a new machine is `docker compose up`, `make data` and `make demo-prepare`.

## 39. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Geometries land in the wrong place or `ST_Contains` finds nothing | SRID missing or 4326 mixed with 32644 | Check `ST_SRID`; transform inputs with `ST_Transform(ST_SetSRID(..., 4326), 32644)`; run the geometry-typmod test |
| GCC query returns fewer rows than the layer holds | Paging without a stable order, or the loop stopped early | Use `orderByFields=objectid` and continue until a page is shorter than 2,000 |
| GeoJSON coordinates look like metres | `outSR=32644` was requested | Request `outSR=4326` and call `to_crs(32644)` locally (§8.4) |
| KML file will not open | The GDAL KML driver is missing in the wheel | Convert with `ogr2ogr -f GeoJSON out.geojson in.kml`, or install a GDAL build with the driver |
| DEM download fails or asks for authorisation | Access conditions for Copernicus GLO-30 changed \[TEAM DOC\] | Follow the fallback chain: SRTM 30 m, then GLO-90; record the outcome in the manifest |
| Flow accumulation looks wrong on flat ground | Unresolved flats or nodata cells | Call `resolve_flats`, mask nodata, and rely on sink depth and GCC drains as primary features |
| Open-Meteo returns 429 or empty arrays | Fair-use limit, or malformed multi-location parameters | Cache responses, make one request for all ward centroids, back off, and fall back to the cached forecast |
| Times are off by 5.5 hours | Naive timestamps or IST/UTC confusion | Store UTC only; reject naive timestamps; test with an IST payload |
| Every replayed reading is flagged LATE | Real clock used instead of the simulation clock | Pass `clock.now(scenario_run_id)` (§37.1) |
| Everything shows INSUFFICIENT\_EVIDENCE during a replay | Freshness computed against the wall clock | Use the simulation clock for `q_fresh` and the data-age chips |
| Upsert returns no row | Identical duplicate ignored (by design) | Treat as `DUPLICATE_IGNORED` |
| Dispatch raises an exception from `alerts_dispatch_guard` | No approving review for the current alert version | Approve the current version; check that a modification did not bump it |
| LangGraph stops with a recursion error | The `qa_gate` and `fallback_data` loop never clears `missing` | Make `fallback_data` set `retried = true` and let `qa_gate` abstain on the second pass |
| Sensors never rise in the simulation | Rain series in the wrong unit (mm per hour used as mm per minute) or all zero | Check the conversion and the selected window; plot the series |
| Risk stays LOW in a storm | Hazard gate (H below 0.10) because rainfall is stale, S is null, or sensors are flagged | Check data-age chips, `terrain_features.susceptibility`, and QC flags; read the evidence list |
| Map is blank | Basemap URL blocked or offline | The app falls back to GeoJSON; check `VITE_BASEMAP_STYLE_URL` |
| Browser shows a CORS error | Origin not in the allow-list | Add it to `cors_origins` in `config/app.yaml` or the environment |
| Model file is missing or its hash differs | Artefact not built or registry out of date | Rerun the training script; until then the flagged fallback model is used |
| Docker runs out of memory | Local LLM plus data processing | Turn the LLM profile off; process data before starting the stack |

## 40. Final Architecture Decision

### 40.1 Decisions

- **FINAL ARCHITECTURE.** A modular monolith (`api` plus `worker`) with the twelve logical layers of §4; PostgreSQL/PostGIS as the single store; HTTP ingestion for both real and simulated devices; deterministic engines for every number; LangGraph for orchestration; the human gate enforced in the API and the database; a React dashboard.
- **FINAL STACK.** As listed in §5.2.
- **FINAL DATABASE.** PostgreSQL 16 with PostGIS 3.4; 38 tables; every geometry typed in SRID 32644; numbered SQL migrations; plain tables, no Timescale in the MVP; triggers for the dispatch guard and append-only logs.
- **FINAL DATA PIPELINE.** Connectors, validators, normalisation, spatial join, idempotent upsert, as-of features, model inputs. Static layers from GCC GIS, DEM, WorldPop, WorldCover, OSM and OpenCity through scripts; rainfall from the Open-Meteo archive and forecast plus IMD daily series; sensors simulated and posted through the API.
- **FINAL MODEL STRATEGY.** M1 LightGBM susceptibility, rank-scaled, with a fallback index; M2 ramp-based trigger, not ML; M3 LightGBM water-level forecaster (15, 30, 60 minutes, quantile intervals), trained on simulated storms and labelled tier S; a persistence-NWP rainfall blend; no deep learning at runtime; calibration only when outcome evidence exists.
- **FINAL AGENT STRATEGY.** Six deterministic agents and two LangGraph graphs (analysis, dispatch), typed contracts, explicit abstention, LLM off by default, an optional local narrator whose output is validated.
- **FINAL GEOSPATIAL STRATEGY.** Wards decide, 250 m cells compute, EPSG:32644 stores, the DEM is processed at 25 m and block-reduced, and the output is an indicative flood-prone footprint rather than inundation depth.
- **FINAL FRONTEND.** React, Vite, TypeScript, Tailwind CSS with shadcn/ui, TanStack Query, MapLibre GL JS and Recharts; thirteen views plus a citizen view.
- **FINAL DEPLOYMENT.** Docker Compose on a laptop; optionally a single VM behind TLS; GitHub Actions for CI.
- **FINAL DEMO.** The 16-step replay of the December 2015 event window with simulated sensors, a demo ward chosen by rule, an outcome comparison against real observed layers, and a controlled learning update.

### 40.2 Canonical end-to-end flow mapped to software

| Stage | Component | Module or table |
| --- | --- | --- |
| Chennai data sources | GCC GIS, DEM, OpenCity, Open-Meteo and IMD, WorldPop, OSM, simulator | `ews.ingest.connectors.*`, `ews.simulation` |
| Ingestion | Pull connectors and HTTP push | `ews.ingest`, `api.routers.data` |
| Validation | Schema, range, QC flags | `ews.quality` |
| PostGIS and time-series storage | Tables of §7 | `ews.db`, `database/migrations` |
| Feature engineering | As-of builders | `ews.features` |
| Forecasting | Rainfall blend, M3 | `ews.models`, Forecasting agent |
| Flood risk engine | H, E, V, R, footprint, uncertainty | `ews.risk`, Risk agent |
| Orchestrator | Analysis and dispatch graphs | `ews.agents.graph` |
| RCA and explainability | Shapley, evidence, similar events | `ews.explain`, RCA agent |
| Decision and policy | Rules, resources | `ews.policy`, Decision agent |
| Human approval | State machine, reviews, audit | `ews.oversight`, `api.routers.alerts` |
| Alert | Drafts, CAP-style payload, gateway | `ews.alerts` |
| Evacuation, shelter, response | Routing, shelters, resources | `ews.routing`, `ews.policy.resources` |
| Outcome capture | Feedback and outcomes | `ews.learning.outcomes`, `POST /feedback` |
| Validation of predictions | Metrics | `ews.learning.metrics` |
| Model and knowledge update | Recalibrate, retrain, promote | `ews.learning.*`, `model_versions` |
| Better future prediction | New ACTIVE model or configuration | model registry |

## 41. What NOT to Build

| Do not build | Why | Revisit when |
| --- | --- | --- |
| Kubernetes | Operational weight with no MVP benefit; Compose reproduces the demo | A multi-node production deployment is funded |
| Microservices | One team, one machine; network boundaries add failure modes | Independent scaling needs appear |
| A Kafka cluster | About 50 sensors; HTTP ingestion is enough | Thousands of devices or multi-tenant streams |
| Redis, Celery, RabbitMQ | PostgreSQL and APScheduler cover every MVP need | A measured bottleneck appears |
| A vector database or embeddings | Similar events use numeric nearest neighbours | Document retrieval over large corpora is required |
| Autonomous emergency actions | Breaks P1; unsafe and unaccountable | Never without legal and operational authority |
| Fake real-time integrations (scraping IMD radar, claiming live CWC or GCC telemetry) | They cannot be defended and fail on stage | Official data-sharing is agreed |
| LLM-driven agent routing, multi-LLM debate, extra agents | Non-deterministic control flow conflicts with P1 and P2 | A specific, evaluated need is shown |
| Deep learning without data (ConvLSTM, Transformers, rainfall nowcasting nets) | No real sequences, no radar; results would be artefacts of the simulator | Months of real telemetry and radar are available |
| Hydraulic inundation simulation (HEC-RAS, SWMM) | Needs calibrated terrain and a connected pipe network; large effort for an MVP | The utility supplies network and survey data |
| Claims of real IoT hardware | There is none; the simulator is labelled | Real devices are deployed |
| Integrations with NDMA, the national alert gateway or GCC control-room systems | Unsupported; no agreements or credentials | Formal engagement exists |
| Real SMS, IVRS, WhatsApp, social-media delivery | Registrations and partnerships are required | A pilot is approved |
| A native mobile app | The responsive citizen view demonstrates the flow | Field pilots |
| Mapbox or other keyed map services | Keys and licences; OSM-derived styles suffice | A commercial deployment needs them |
| A custom authentication server | JWT and RBAC meet the MVP; building one adds risk | Production SSO |
| A knowledge-graph database | No requirement needs graph queries | Cross-agency knowledge integration |
| Sentinel-1 flood-mapping pipeline | Heavy; not needed for the MVP evaluation | After the MVP, as a labelling source |
| Live traffic routing | No data source assumed | A traffic data agreement exists |

## 42. Build Checklist

- [ ] Repository
- [ ] Environment (`uv`, Docker, `.env` from `.env.example`)
- [ ] Database (migrations 001–007 applied and seeded)
- [ ] Chennai GIS (wards, zones, drains, buildings, subways, rivers)
- [ ] Rainfall ingestion (archive, IMD daily, simulated gauges)
- [ ] Weather forecast (Open-Meteo connector with cache fallback)
- [ ] DEM (processed to 25 m, terrain derivatives)
- [ ] Drainage (clean edges, nodes, Manning proxy)
- [ ] Historical floods (events, extents, `event_features`)
- [ ] Population
- [ ] Buildings
- [ ] Roads (OSM graph)
- [ ] Shelters
- [ ] Sensor simulator
- [ ] Forecast model (M3)
- [ ] Risk model (M1 and the risk engine)
- [ ] Explainability
- [ ] Agents
- [ ] Orchestrator
- [ ] Human approval
- [ ] Alerts
- [ ] Routing
- [ ] Dashboard
- [ ] Evaluation
- [ ] Continuous learning
- [ ] Testing
- [ ] Docker
- [ ] Deployment
- [ ] Demo script
- [ ] Source probe passed and manifest committed
- [ ] Limitations page (`docs/LIMITATIONS.md`) published in the app

## 43. Appendix — Schemas

The relational schema is in §7.2 and the Pydantic contracts are in §14. This appendix adds the wire-level schemas and example records that those sections refer to.

**A. Rainfall ingestion batch (JSON Schema, abbreviated)**

```json
{"type": "object", "required": ["readings"],
 "properties": {
  "scenario_run_id": {"type": ["string", "null"], "format": "uuid"},
  "readings": {"type": "array", "maxItems": 1000, "items": {
    "type": "object", "required": ["station_id", "period_start", "period_end", "kind"],
    "properties": {
      "station_id": {"type": "string"},
      "period_start": {"type": "string", "format": "date-time"},
      "period_end": {"type": "string", "format": "date-time"},
      "depth_mm": {"type": ["number", "null"], "minimum": 0},
      "kind": {"enum": ["GAUGE", "SIM_GAUGE", "REANALYSIS", "NWP_ANALYSIS",
                        "SATELLITE_ESTIMATE", "CITY_DAILY", "GRIDDED_DAILY"]}}}}}}
```

The water-level batch has the same envelope; each reading has `sensor_id`, `observed_at` (date-time with offset), and optional `level_cm`, `rise_rate_cm_min`, `battery_pct` (0–100), `signal_dbm` (-130 to 0), `device_status`.

**B. Evidence item (illustrative values)**

```json
{"evidence_id": "EV-RAINFALL-WARD-XXX-20151201T0530-1a2b3c4d",
 "evidence_type": "RAINFALL", "zone_id": "WARD-XXX", "observed_at": "2015-12-01T05:30:00Z",
 "value": {"window_min": 60, "sum_mm": 68.0, "sources": ["SIMG-03", "SIMG-04"]},
 "source_table": "rainfall_observations", "source_keys": {"obs_ids": [101, 102, 103]},
 "quality": 0.9, "is_simulated": true, "content_hash": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"}
```

**C. Stored alert payload (CAP-aligned, illustrative values; `status` is always Exercise in the prototype)**

```json
{"identifier": "ALERT-00000000-0000-4000-8000-000000000010-v1", "sender": "ews-prototype",
 "sent": "2015-12-01T05:45:00Z", "status": "Exercise", "msgType": "Alert", "scope": "Public",
 "info": [{"language": "en", "category": ["Met"], "event": "Urban flood warning",
   "urgency": "Expected", "severity": "Moderate", "certainty": "Likely",
   "onset": "2015-12-01T06:30:00Z", "expires": "2015-12-01T09:30:00Z",
   "headline": "Flood warning for Ward XXX",
   "description": "Elevated flood likelihood within the next 45 minutes.",
   "instruction": "TEMPLATE TEXT PENDING APPROVED WORDING",
   "area": {"areaDesc": "Ward XXX", "polygon": ["12.98,80.22 12.98,80.23 12.99,80.23 12.98,80.22"]},
   "parameter": [{"valueName": "risk_id", "value": "00000000-0000-4000-8000-000000000020"},
                 {"valueName": "confidence", "value": "MEDIUM"},
                 {"valueName": "uses_simulated_inputs", "value": "true"}]}]}
```

**D. Scenario file keys.** `id`; `rainfall.source` (`open_meteo_archive`, `synthetic_triangular`); `rainfall.window_start`, `window_end` or `window: auto_peak_12h` with `lead_in_h`; `rainfall.scale`; `rainfall.forecast` (`scenario_sim`); `sensors.background_per_gcc_zone`, `sensors.per_demo_ward`; `faults[]` (`type` of `stuck`, `outage`, `spike_rate`, `drift`; with scope, start and duration); `speed`; `seed`.

**E. Enumerations.** Risk levels LOW, MEDIUM, HIGH, VERY\_HIGH. Alert severities ADVISORY, WARNING, URGENT. Alert states DRAFT, AI\_GENERATED, PENDING\_REVIEW, REQUEST\_CHANGES, REANALYSIS, APPROVED, REJECTED, DISPATCHED, ACTIVE, RESOLVED, EXPIRED, CANCELLED. Sensor status OK, DEGRADED, STUCK, OFFLINE, LOW\_BATTERY, ANOMALY. QC flags as in §9.4. Evidence tiers R, S, E, MIXED. Calibration status UNCALIBRATED, HINDCAST\_CALIBRATED, OUTCOME\_CALIBRATED.

## 44. Appendix — API Examples

All values are illustrative; IDs are placeholders. Every response may instead carry the error body of §23.1.

**1. `POST /api/v1/data/rainfall`**

```json
{"readings": [{"station_id": "SIMG-03", "period_start": "2015-12-01T05:25:00Z",
  "period_end": "2015-12-01T05:30:00Z", "depth_mm": 3.4, "kind": "SIM_GAUGE",
  "scenario_run_id": "00000000-0000-4000-8000-000000000001"}]}
```

```json
{"accepted": 1, "rejected": 0, "flagged": 0, "items": [{"index": 0, "status": "CREATED", "flags": []}]}
```

**2. `POST /api/v1/data/water-level`** (header `X-Sensor-Key`)

```json
{"readings": [{"sensor_id": "SNS-017", "observed_at": "2015-12-01T11:00:00+05:30",
  "level_cm": 42.5, "rise_rate_cm_min": 0.8, "battery_pct": 87, "signal_dbm": -92, "device_status": "OK"}],
 "scenario_run_id": "00000000-0000-4000-8000-000000000001"}
```

```json
{"accepted": 1, "rejected": 0, "flagged": 0, "items": [{"index": 0, "status": "CREATED", "flags": []}]}
```

**3. `GET /api/v1/zones?level=WARD&with_risk=true`**

```json
{"items": [{"zone_id": "WARD-XXX", "level": "WARD", "name": "Ward XXX", "gcc_zone_no": 13,
  "area_km2": 2.4, "risk_level": "HIGH", "risk_as_of": "2015-12-01T05:30:00Z"}], "next_cursor": null}
```

**4. `GET /api/v1/risk?horizon_min=30&min_level=HIGH`**

```json
{"as_of": "2015-12-01T05:30:00Z", "horizon_min": 30, "items": [{"zone_id": "WARD-XXX",
  "risk_level": "HIGH", "risk_score": 0.71, "probability": 0.78, "calibration_status": "UNCALIBRATED",
  "time_to_impact_min": 45, "confidence_level": "MEDIUM", "uses_simulated_inputs": true}]}
```

**5. `GET /api/v1/risk/WARD-XXX`**

```json
{"zone_id": "WARD-XXX", "timeline": [
  {"horizon_min": 0, "risk_score": 0.52, "risk_level": "HIGH", "probability": 0.61, "h_p10": 0.48, "h_p90": 0.72},
  {"horizon_min": 30, "risk_score": 0.71, "risk_level": "HIGH", "probability": 0.78, "h_p10": 0.60, "h_p90": 0.88}],
 "hazard_score": 0.78, "exposure_score": 0.72, "vulnerability_score": 0.55, "data_quality": 0.9,
 "confidence": 0.58, "confidence_level": "MEDIUM", "evidence_tier": "MIXED",
 "risk_id": "00000000-0000-4000-8000-000000000020"}
```

**6. `GET /api/v1/explanations/00000000-0000-4000-8000-000000000020`**

```json
{"risk_id": "00000000-0000-4000-8000-000000000020", "where": "Ward XXX, GCC Zone 13",
 "when": "As of 2015-12-01T11:00+05:30; likelihood reaches 0.60 within 45 minutes",
 "why": [{"factor_key": "observed_rainfall", "value": 68.0, "unit": "mm per 60 min", "contribution_pct": 34.0,
          "direction": "INCREASES", "evidence_ids": ["EV-RAINFALL-WARD-XXX-20151201T0530-1a2b3c4d"]}],
 "historical_similarity": [{"event_id": "CHN-2015-12", "similarity": 0.71, "flooded_frac": 0.35, "evidence_ids": ["EV-HISTORICAL_EVENT-WARD-XXX-20151201T0530-5e6f7a8b"]}],
 "narrative": "Ward 000 is assessed at HIGH risk ...", "narrative_source": "TEMPLATE", "validation": {"errors": []}}
```

**7. `POST /api/v1/forecast`**

```json
{"as_of": "2015-12-01T05:30:00Z", "sensor_ids": ["SNS-017"], "targets": ["WATER_LEVEL_CM"]}
```

```json
[{"target": "WATER_LEVEL_CM", "subject_id": "SNS-017", "issued_at": "2015-12-01T05:30:05Z",
  "input_as_of": "2015-12-01T05:30:00Z", "points": [
    {"horizon_min": 15, "value": 58.2, "p10": 54.0, "p90": 63.5},
    {"horizon_min": 30, "value": 71.0, "p10": 62.0, "p90": 80.4}],
  "model_version": "waterlevel/1.0.0", "model_tier": "S", "is_simulated_input": true,
  "fallback_used": false, "warnings": []}]
```

**8. `POST /api/v1/risk/analyze`** (202)

```json
{"zone_ids": ["WARD-XXX"], "as_of": "2015-12-01T05:30:00Z", "scenario_run_id": "00000000-0000-4000-8000-000000000001"}
```

```json
{"run_id": "00000000-0000-4000-8000-000000000030", "status": "RUNNING"}
```

**9. `POST /api/v1/alerts`**

```json
{"risk_id": "00000000-0000-4000-8000-000000000020", "severity": "WARNING", "note": "Operator-initiated draft"}
```

```json
{"alert_id": "00000000-0000-4000-8000-000000000010", "status": "DRAFT", "version": 1, "requires_approval": true}
```

**10. `POST /api/v1/alerts/00000000-0000-4000-8000-000000000010/approve`** (coordinator)

```json
{"alert_version": 1, "checklist": {"evidence_reviewed": true, "risk_reviewed": true,
  "recommendations_reviewed": true}, "note": "Evidence checked against sensors"}
```

```json
{"alert_id": "00000000-0000-4000-8000-000000000010", "status": "DISPATCHED", "version": 1,
 "recipients": [{"channel": "SMS_SIM", "delivery_status": "SIMULATED_DELIVERED"},
                {"channel": "EMAIL", "delivery_status": "SENT_SANDBOX"}]}
```

Errors: `403` `{"error": {"code": "FORBIDDEN", "message": "role may not approve this severity"}}`; `409` stale version; `422` incomplete checklist.

**11. `POST /api/v1/alerts/{id}/reject`**

```json
{"alert_version": 1, "reason": "Rainfall evidence is stale"}
```

```json
{"alert_id": "00000000-0000-4000-8000-000000000010", "status": "REJECTED", "version": 1}
```

**12. `GET /api/v1/routes?zone_id=WARD-XXX&max_routes=3`**

```json
{"zone_id": "WARD-XXX", "approximate": false, "routes": [{"route_id": "00000000-0000-4000-8000-000000000040",
  "shelter_id": 12, "shelter_name": "Example shelter", "rank": 1, "length_m": 2400, "eta_min": 8.1,
  "safe_route_score": 0.74, "max_edge_risk": 0.4, "blocked_edges": 0, "warnings": ["capacity unknown"],
  "geometry": {"type": "LineString", "coordinates": [[80.22, 12.98], [80.23, 12.99]]}}]}
```

**13. `GET /api/v1/shelters?zone_id=WARD-XXX`**

```json
{"items": [{"shelter_id": 12, "name": "Example shelter", "zone_id": "WARD-XXX", "capacity": null,
  "status": "UNKNOWN", "is_official": true, "distance_m": 1800}]}
```

**14. `GET /api/v1/events`**

```json
{"items": [{"event_id": "CHN-2015-12", "name": "NE monsoon floods, Nov–Dec 2015", "start_date": "2015-11-30",
  "end_date": "2015-12-03", "label_quality": "OBSERVED_POINTS", "source_id": "opencity_flood_2015"}]}
```

**15. `POST /api/v1/feedback`**

```json
{"feedback_type": "OUTCOME", "risk_id": "00000000-0000-4000-8000-000000000020", "zone_id": "WARD-XXX",
 "outcome_source": "HISTORICAL_LAYER", "observed_flooded": true, "observed_flood_frac": 0.35, "is_simulated": false}
```

```json
{"feedback_id": "00000000-0000-4000-8000-000000000050", "outcome_id": "00000000-0000-4000-8000-000000000051"}
```

**16. `GET /api/v1/models`**

```json
{"items": [{"model_id": "00000000-0000-4000-8000-000000000060", "name": "waterlevel_h30", "version": "1.0.0",
  "status": "ACTIVE", "kind": "ML", "trained_on_simulated": true, "metrics": {"status": "not yet evaluated"}}]}
```

**17. `GET /api/v1/health`**

```json
{"status": "OK", "db": "OK", "models": "OK",
 "sources": [{"id": "open_meteo_forecast", "status": "OK", "age_s": 1800}],
 "scenario": {"run_id": "00000000-0000-4000-8000-000000000001", "status": "RUNNING", "sim_clock": "2015-12-01T05:30:00Z"},
 "version": "1.0.0"}
```

## 45. Appendix — Configuration

Safe examples only. Every number marked in the body as \[ASSUMPTION\] appears here and nowhere in code.

**`.env.example`**

```
# copy to .env and fill in; never commit .env
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+psycopg://ews:change-me@db:5432/ews
JWT_SECRET=generate-a-long-random-value
SENSOR_KEY_PEPPER=generate-another-long-random-value
CORS_ORIGINS=http://localhost:8080,http://localhost:5173
SMTP_HOST=mailpit
SMTP_PORT=1025
LLM_PROVIDER=none              # none | openai_compatible
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=                     # tag of the local or hosted model; empty when LLM_PROVIDER=none
LLM_API_KEY=                   # hosted providers only
EARTHDATA_USERNAME=            # optional, IMERG only
EARTHDATA_PASSWORD=
VITE_API_URL=http://localhost:8000/api/v1
VITE_BASEMAP_STYLE_URL=        # OSM-derived style URL; verify the provider's terms
```

**`config/app.yaml`**

```
timezone_display: Asia/Kolkata
storage_crs: 32644
horizons_min: [0, 15, 30, 45, 60, 75, 90, 105, 120]
analysis:
  schedule_interval_min: 10
  event_trigger: {r15_mm: 5.0, fill_ratio: 0.5, rise_5_cm_min: 0.3, debounce_s: 60}
  node_timeout_s: 30
  run_timeout_s: 120
alerts:
  draft_expiry_min: 30
  min_interval_per_ward_min: 30
  resolve_after_quiet_cycles: 2
paths: {data: data, models: models, runs: runs}
features: {llm_narrator: false, allow_candidate_shelters: false, demo_cache_mode: false}
```

**`config/risk.yaml`** (all values are prototype assumptions)

```
version: proto-0.1
official: false
trigger:
  r60: [20, 90]
  r180: [50, 200]
  antecedent: {ramp: [30, 150], boost_max: 0.25}
drain_stress:
  fill_ramp: [0.5, 1.0]
  rise_ramp_cm_min: [0.3, 2.0]
  rise_gate_fill: [0.25, 0.7]
  design_intensity_mm_h: 50       # placeholder; replace with a GCC or Manning-derived value
  blockage: 0.15
  model_ramp: [0.6, 1.2]
  model_trust: 0.7
susceptibility: {s0: 0.25, ward_mix: 0.5}
risk:
  weights: {hazard: 0.4, exposure: 0.3, vulnerability: 0.3}
  gate: [0.10, 0.40]
  level_cuts: [0.25, 0.50, 0.85]
  floors: {high_min_hazard: 0.40, very_high_min_hazard: 0.70}
  impact_onset_hazard: 0.60
exposure_weights: {population: 0.35, buildings: 0.15, road_km: 0.15, health: 0.15, schools: 0.10, other_critical: 0.10}
vulnerability_weights: {vulnerable_age_fraction: 0.5, shelter_distance: 0.3, evacuation_difficulty: 0.2}
footprint: {intercept: 0.90, slope: 0.60, min: 0.30, max: 0.90}
confidence:
  tau_min: {rain_obs: 20, forecast: 120, sensor: 5}
  levels: {high_min: 0.70, medium_min: 0.40}
  agreement: {agree: 1.0, single_source: 0.8, conflict: 0.6}
monte_carlo: {draws: 200, perturbation: 0.2, seed: 0}
overrides:
  - {id: O-HOSP, when: hospital_in_footprint, from: MEDIUM, to: HIGH, requires_review: true}
  - {id: O-LOWCONF, when: confidence_low, cap: HIGH, tag: LOW-CONFIDENCE}
```

**`config/sensors.yaml`**

```
count: {background_per_gcc_zone: 1, per_demo_ward: 3}
placement: {min_separation_m: 500, weight_formula: '(0.5 + S_ward) * (1 + hist_flood_freq)'}
thresholds: {warning_fraction_of_depth: 0.6, critical_fraction_of_depth: 0.9}
simulator:
  cn: {base: 60, per_built_fraction: 38}
  kappa_cm_per_mm: [0.4, 1.6]
  lag_min: [5, 25]
  k_out_per_min: [0.01, 0.04]
  blockage_beta: [2, 10]
  blockage_obstacle_bonus: 0.2
  tide: {period_h: 12.42, amplitude: 0.3, within_km_of_coast_or_river: 3}
  pond_decay_per_min: 0.02
  noise_cm: 0.5
  quantisation_cm: 0.1
faults:
  dropout: {enter_p_per_min: 0.003, mean_burst_min: 5}
  spike: {p: 0.002, magnitude_cm: [30, 80]}
  drift_cm_per_h: 2
  battery: {start_pct: [60, 100], drain_pct_per_h: [0.01, 0.03], low_pct: 15, low_dropout_multiplier: 3}
  signal: {range_dbm: [-110, -60], weak_dbm: -105, weak_dropout_multiplier: 2}
  clock_skew_min: [1, 3]
```

**`config/models.yaml`**

```
susceptibility:
  min_positive_cells: 150
  negatives: {min_distance_from_positive_m: 750, exclude_hazard_class: HIGH}
  cv: {block_km: 5, folds: 5}
  lightgbm: {n_estimators: 300, learning_rate: 0.05, num_leaves: 31, min_child_samples: 20,
             subsample: 0.8, subsample_freq: 1, colsample_bytree: 0.8, reg_lambda: 1.0}
  seed: 42
waterlevel:
  horizons_min: [15, 30, 60]
  storms: {n: 300, split: [0.6, 0.2, 0.2], replay_windows: 10, replay_scale: [0.5, 1.5]}
  domain_shift: {param_perturbation: 0.3, fault_injection: true, n_storms: 60}
  lightgbm: {n_estimators: 400, learning_rate: 0.05, num_leaves: 31, min_child_samples: 50,
             subsample: 0.8, subsample_freq: 1, colsample_bytree: 0.8}
  promotion_gate: {skill_vs_persistence_min: 0.0, skill_vs_linear_min: 0.0, rmse_regression_tolerance: 0.05}
  seed: 42
learning:
  triggers: {new_pairs: 30, brier_degradation: 0.10, brier_window_pairs: 50, psi: 0.2}
  calibration: {platt_min_pairs: 20, isotonic_min_pairs: 50}
  cost_ratio_miss_to_false_alarm: 5
  shadow_tolerance: 0.05
```

**`config/data_sources.yaml`**

```
sources:
  gcc_arcgis:
    base_url: https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/GCC_COLLABORATION_LAYER/MapServer
    layers: {bridge: 0, river: 1, centreline: 2, carriageway: 3, buildings: 4, subways: 5, ward: 6, zone: 7, drains: 8}
    page_size: 2000
    timeout_s: 60
  open_meteo_forecast:
    url: https://api.open-meteo.com/v1/forecast
    interval_min: 60
    timeout_s: 30
    retries: 3
    stale_after_h: 6
  open_meteo_archive:
    url: https://archive-api.open-meteo.com/v1/archive
    timeout_s: 60
  imd_daily: {kind: file, path: data/raw/opencity/chennai_rainfall.csv}
  osm: {area: GCC boundary plus 2 km buffer, refresh_days: 30}
fallback_order:
  rainfall: [open_meteo_forecast, cache, scenario]
```

**`config/response.prototype.yaml`** and **`config/alert_templates/en.yaml`** (placeholders)

```
# response.prototype.yaml
official: false
note: PLACEHOLDER ratios; replace with GCC or NDRF norms before any operational use
pumps_per_km2_footprint: 2
rescue_teams_per_1000_exposed: 1
ambulance_standby_per_hospital_in_footprint: 1
```

```
# alert_templates/en.yaml   (ta.yaml has the same keys; authored by a Tamil speaker, reviewed by the authority)
locale: en
status: PLACEHOLDER WORDING PENDING APPROVAL BY THE COMPETENT AUTHORITY
ADVISORY:
  headline: Flood watch for Ward {ward_name}
  description: Elevated flood likelihood in {ward_name} within {time_window}.
  instruction: Stay informed through official channels.
WARNING:
  headline: Flood warning for Ward {ward_name}
  description: Flood likelihood is high in {ward_name} within {time_window}.
  instruction: Avoid low-lying roads and underpasses. Official shelter: {shelter_name}. {route_summary}
URGENT:
  headline: Urgent flood warning for Ward {ward_name}
  description: Flooding is likely in {ward_name} within {time_window}.
  instruction: Follow the official evacuation route to {shelter_name}. {route_summary}
```

## 46. Appendix — Dataset References

Status on 9 October 2026: **\[VERIFIED\]** checked live or against public pages; **\[TEAM DOC\]** from the team's dataset report or guidebooks and not re-verified. Licences must be confirmed per dataset before redistribution; `scripts/probe_sources.py` records the result in `data/MANIFEST.yaml`.

| # | Dataset | Link | Status | Use in the MVP |
| --- | --- | --- | --- | --- |
| 1 | GCC GIS service: wards, zones, storm-water drains, buildings, vehicular subways, river, bridges, centre line, carriageway | https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/GCC\_COLLABORATION\_LAYER/MapServer | \[VERIFIED\] layers and field lists for layers 4, 5, 6 and 8; attribute completeness and feature counts not measured | Yes |
| 2 | Open-Meteo forecast, archive (ERA5-based, hourly, from 1940) and flood endpoints | https://open-meteo.com ; `api.open-meteo.com/v1/forecast`, `archive-api.open-meteo.com/v1/archive` | \[VERIFIED\] via public pages: keyless, non-commercial, attribution; read the provider's current terms | Yes (rainfall, forecast) |
| 3 | IMD data services, gridded rainfall, radar page | https://mausam.imd.gov.in/ ; https://mausam.imd.gov.in/responsive/radar.php | \[TEAM DOC\] | Daily series yes; radar no |
| 4 | OpenCity Chennai datasets: rainfall, flood events, hazard zones, shelters, waterbodies, storm-water KML | https://data.opencity.in/dataset/?groups=chennai&q=data ; https://data.opencity.in/dataset/chennai-shelters | \[TEAM DOC\] | Yes |
| 5 | NASA GPM IMERG | https://gpm.nasa.gov/data/imerg | \[TEAM DOC\]; registration needed | Optional |
| 6 | CHIRPS v3 | https://www.chc.ucsb.edu/data/chirps3 | \[TEAM DOC\] | No |
| 7 | ERA5 (Copernicus CDS) | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels | \[TEAM DOC\] | Indirect, through the Open-Meteo archive |
| 8 | ECMWF open data | https://www.ecmwf.int/en/forecasts/datasets/open-data-0 | \[TEAM DOC\] | No (production candidate) |
| 9 | NOAA GHCN | https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily | \[TEAM DOC\] | No |
| 10 | CWC hydrological observations, India-WRIS | https://cwc.gov.in/hydro-meteorological-observation | \[TEAM DOC\]; access-dependent | Optional, manual CSV |
| 11 | Copernicus GloFAS historical | https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical | \[TEAM DOC\] | No |
| 12 | Bhuvan flood early warning and hazard zones | https://bhuvan-app1.nrsc.gov.in/fews/index.php ; https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood\_hz/flood\_hz.php | \[TEAM DOC\] | Manual validation reference |
| 13 | Global Flood Database v1 (2000–2018) | https://developers.google.com/earth-engine/datasets/catalog/GLOBAL\_FLOOD\_DB\_MODIS\_EVENTS\_V1 | \[TEAM DOC\] | Optional validation for 2015 |
| 14 | Sentinel-1 (Copernicus Data Space) | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1 | \[TEAM DOC\] | Stretch labelling source |
| 15 | Sen1Floods11; Cloud to Street flood dataset | https://github.com/EOEPCA/Sen1Floods11-Dataset ; https://registry.opendata.aws/c2smsfloods/ | \[TEAM DOC\] | No |
| 16 | Copernicus DEM | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html | \[TEAM DOC\]; access changed in 2026 | Yes (first attempt) |
| 17 | SRTM | https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm | \[TEAM DOC\] | Fallback |
| 18 | HydroSHEDS | https://www.hydrosheds.org/products | \[TEAM DOC\] | Optional context |
| 19 | JRC Global Surface Water | https://global-surface-water.appspot.com/download | \[TEAM DOC\] | Optional water mask |
| 20 | ESA WorldCover | https://esa-worldcover.org/en/data-access | \[TEAM DOC\] | Yes |
| 21 | Google Open Buildings; Microsoft building footprints | https://sites.research.google/gr/open-buildings/ ; https://github.com/microsoft/GlobalMLBuildingFootprints | \[TEAM DOC\] | Fallback to the GCC buildings layer |
| 22 | WorldPop India | https://hub.worldpop.org/project/categories?id=3 | \[TEAM DOC\] | Yes |
| 23 | OpenStreetMap, Geofabrik India | https://download.geofabrik.de/asia/india.html | \[TEAM DOC\] | Yes, through OSMnx |
| 24 | EM-DAT | https://doc.emdat.be/docs/data-accessibility/ | \[TEAM DOC\] | No |

**Verification log, 9 October 2026.** The GCC service root lists nine layers (0 bridge category, 1 river, 2 centre line, 3 carriageway, 4 buildings, 5 vehicular subways, 6 ward, 7 zone, 8 storm-water drain), spatial reference 32644, a maximum of 2,000 records per request, and JSON, GeoJSON and PBF output. Layer 6 fields: `objectid`, `pro_z_no`, `pro_ward_n` (numeric), area and perimeter. Layer 8 fields: `zone`, `ward`, `location`, `drain_type`, `cover`, `drain_len`, `drain_wid`, `drain_dep`, `drain_size`, `mh_shape`, `mh_size`, `typ_mat`, `water_flow`, `puca_kacha`, `status`, `swd_mat`, `drain_detl`, `invert_sp`, `invert_ep`, `inlet_shp`, start and end easting and northing, `obstacles`, `dlen_km` (all text except the last). Layer 5 fields: `zone`, `ward`, `road_name`, `region`, `area_name`, `locality`, `road_id`, `category`. Layer 4 fields: `region_name`, `zone_number`, `ward_number`, `road_id`, `gcc_gis_id`, `locality`, `area_name`, area and perimeter (no use or height field). **Not verified:** feature counts, completeness of attribute values, licences of every dataset, the content of the OpenCity files, and every item tagged \[TEAM DOC\].

**Before relying on any \[TEAM DOC\] item:** run the Phase 1 probe and update the manifest; if a dataset fails, record `FAILED_PROBE`, follow its fallback in §6.2 and §28, and state the change in `docs/LIMITATIONS.md`.

*End of manual. Version 1.0, 9 October 2026.*
