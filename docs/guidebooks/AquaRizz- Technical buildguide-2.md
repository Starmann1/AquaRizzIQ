# CHENNAI URBAN FLOOD EARLY WARNING SYSTEM

**TECHNICAL BUILD GUIDE & SPECIFICATION MANUAL — DREAMOVATION 2.0 — DREAM-SSB-09**

Climate-Resilient Urban Flood Monitoring and Early Warning System · Prototype city: Chennai, Tamil Nadu, India

Version 1.0 · 9 October 2026 · Status: build-ready specification for the hackathon prototype (MVP), with a production evolution path

Built from: proposal PPT, End-to-End Project Explanation PDF, Dataset Research Report, ten architecture/workflow diagrams, the Diagram Specification, and the Gemini and Grok research guidebooks. Where those sources disagree, §1.4 records the decision taken here.

> Reading guide. §1–4 decisions and architecture · §5–11 stack, data, database, geospatial, ingestion, features, forecasting · §12–22 risk engine, agents, explainability, decisions, routing, alerts, UI · §23–32 APIs, repo, config, MLOps, learning, failure, security, observability, tests, evaluation · §33–42 MVP vs production, roadmap, code, demo, deployment, final decisions, checklist · §43–46 appendices. Anything marked PROTOTYPE is a starting value chosen for the demo. It is not an official threshold and not a measured result.

## 1. Executive Summary

### 1.1 What is being built

A decision-support and early-warning platform for urban pluvial flooding in Chennai. It ingests rainfall, forecast, water-level, terrain, drainage, exposure and flood-history data; forecasts short-term water-level behaviour; computes a calibrated flood probability and a risk level for every GCC ward; explains the drivers with traceable evidence; drafts alerts, evacuation routes, shelter and resource recommendations; holds every critical action for human approval; and compares predictions with outcomes so the system can improve under controlled governance.

SENSE → PREDICT → ANALYZE → EXPLAIN → DECIDE → HUMAN APPROVAL → ALERT → LEARN

It is not an autonomous emergency system, and no language model ever produces a flood number.

### 1.2 The twelve decisions that matter most

| # | Decision | Reason |
| --- | --- | --- |
| 1 | Modular monolith (one FastAPI app + one worker), not microservices | One team, one demo machine; module boundaries give the same separation without network failure modes |
| 2 | PostgreSQL 16 + PostGIS 3.4 as the only datastore; no Redis, Kafka, MinIO or vector DB in the MVP | Every workload fits one database; fewer containers means fewer demo failures |
| 3 | Alerts and risk reported per GCC ward (200 wards); modelling on a 250 m grid | Wards match shelters, response jurisdictions and the proposal; the grid captures micro-topography |
| 4 | Two real ML models plus one calibrated expert-prior function: M1 static susceptibility (LightGBM), M2 water-level forecaster (LightGBM quantile), M3 hazard function (logistic) | Small data, high interpretability; deep learning is not justified by the data that exists |
| 5 | Risk is gated: probability of flooding sets the level, exposure and vulnerability modulate it through a risk matrix | The plain weighted sum raises risk on a dry day (see §12.2) |
| 6 | Water-level sensors are simulated, labelled SIM, and enter through the same HTTP contract real sensors will use | No public dense Chennai drain telemetry exists; the adapter makes replacement a config change |
| 7 | Six typed agents run inside one LangGraph graph; the LLM is optional and only writes prose behind a number guard | The system must work with the LLM off and must never invent numbers |
| 8 | Human approval is a server-side state machine; no code path leads from an agent to dispatch | Safety by construction, not by prompt |
| 9 | Routing with OSMnx + NetworkX using risk-penalised edge costs; OSRM is a production option | Dynamic avoidance of predicted flooded segments is trivial in a graph library |
| 10 | Continuous learning is controlled recalibration/retraining: candidate → offline evaluation → human approval → versioned promotion | Online learning in a safety workflow is unsafe and unnecessary |
| 11 | React + Vite + MapLibre + ECharts, polling rather than websockets | Fewest moving parts that still look live |
| 12 | Docker Compose on one machine, with an offline-capable replay mode and a deterministic simulation clock | The demo must survive bad Wi-Fi and run identically every time |

### 1.3 Real, simulated and not claimed

| Real or open data | Simulated for the MVP (always labelled) | Not claimed |
| --- | --- | --- |
| IMD gridded rainfall, GPM IMERG, forecast feeds, Copernicus DEM, GCC drain geometry, wards, shelters, flood labels (OpenCity, Bhuvan, Sentinel-1, GFD), WorldPop, OSM, Open Buildings, ESA WorldCover | Urban drain water-level time series, sensor health, battery and faults, drain capacity attributes, notification delivery, the demo storm | Live GCC drain telemetry, radar rainfall estimates, official relief-centre capacity, real SMS/IVRS/CAP delivery, hydraulic inundation modelling, any integration with NDMA, TN SDMA or GCC systems |

### 1.4 Source reconciliation — where the documents disagree

| # | Issue | Decision in this manual |
| --- | --- | --- |
| 1 | Slides show H 0.85, E 0.75, V 0.70 with weights 0.4/0.3/0.3, which gives 0.775, yet the final score is shown as 0.82. The same 0.82 is also shown as an 82% flood probability | Probability and risk index are separate quantities. All examples here are recomputed. Fix the slide arithmetic before judging |
| 2 | Proposal promises 15–120 min lead time; both guidebooks warn that 15–120 min rainfall nowcasting needs radar QPE that is not publicly available | Lead time comes from sensor-driven water-level forecasts plus hourly forecast feeds. A 15-minute rainfall nowcast is never claimed |
| 3 | Demo area: Gemini says Ward 112 (Zone 9 Teynampet) plus the Adyar basin; Grok says Velachery–Pallikaranai or Ambattur–Anna Nagar West | Live demo hero ward is Ward 112 (matches the slides). Backtest showcase is Velachery–Pallikaranai (best documented 2015 and 2023 flooding). Verify the ward-to-zone mapping in the loaded GCC boundary file |
| 4 | Sensor count: 15–30 (Grok) vs about 50 (Gemini) | Configured at 50, minimum 30, at least 4 in the hero ward |
| 5 | Timelines differ between diagrams (alerts sent at T=12 in one, T=19 in another) | One canonical timeline in §37 |
| 6 | Slides label 78% and 82% as High | Risk matrix edges are set so a probability of 0.60–0.85 with medium or high impact is HIGH (§12.3) |
| 7 | Unverified claims: SWD segment count (10,308 vs a KML covering 114+ wards), IFS open-data resolution (0.25° vs 0.4°), an 86.12% LSTM accuracy figure, a Chennai-specific radar Z–R relation | Treated as unverified. Load-time coverage reports replace assumptions; no external accuracy figure is quoted |

### 1.5 Limits to state openly

- Drain water levels are simulated. Any model trained on simulator output demonstrates the pipeline, not real hydrologic skill; its metrics carry the label synthetic-validation.
- Gridded rainfall (0.1°–0.25°) is coarser than a ward. IMERG Early Run has about 4 hours latency, so live-monitor mode is monitoring only.
- Flood footprints are indicative susceptibility surfaces, not hydraulic simulations.
- All thresholds are PROTOTYPE values. Mapping to IMD colour-coded warnings, TN SDMA and GCC procedures is a production step requiring the authorities.
- Alert delivery is simulated. Nothing is transmitted to real people.

## 2. Prototype Scope

### 2.1 Capability map

| # | Required capability | Primary module | Demo step (§37) |
| --- | --- | --- | --- |
| 1 | Chennai rainfall ingestion | ewf.ingestion.adapters (IMD, IMERG, replay) | 3 |
| 2 | Weather/forecast ingestion | adapters.openmeteo, adapters.ecmwf | 3 |
| 3 | Water-level monitoring | api /data/water-level, sensor\_http adapter | 5 |
| 4 | Simulated IoT sensors | ewf.simulation | 4–5 |
| 5 | Terrain analysis | ewf.geo.terrain | offline |
| 6 | Drainage analysis | ewf.geo.drainage | offline |
| 7 | Historical flood analysis | ewf.geo.history, M1 | offline, 14–16 |
| 8 | Zone-level flood-risk prediction | ewf.risk.engine | 7–8 |
| 9 | Hazard + exposure + vulnerability | ewf.risk | 7 |
| 10 | Explainable risk | ewf.explain | 9 |
| 11 | Confidence and uncertainty | ewf.risk.confidence | 7–9 |
| 12 | Recommended action | ewf.decision | 10 |
| 13 | Human approval | ewf.alerts.state\_machine + review UI | 11 |
| 14 | Alert generation | ewf.alerts | 12 |
| 15 | Evacuation routes | ewf.routing | 13 |
| 16 | Shelter recommendation | ewf.routing.shelters | 13 |
| 17 | Emergency resource recommendation | ewf.decision.actions | 10 |
| 18 | Dashboard | web/ | all |
| 19 | Actual-event comparison | ewf.learning.outcomes | 15 |
| 20 | Continuous-learning demonstration | ewf.learning | 16 |

### 2.2 Spatial scope

- City layer: all 200 GCC wards (15 GCC administrative zones) are loaded. Features are computed city-wide wherever data exist, and every ward carries coverage flags (drain data, shelters, sensors, flood labels).
- Live demo area of interest: hero ward 112 plus its first-ring neighbours plus wards along the Adyar corridor to the coast, selected by adjacency, capped at 15 wards, defined in config/aoi.yaml.
- Backtest showcase: Velachery–Pallikaranai corridor for the December 2015 and December 2023 events.
- Modelling grid: 250 m regular grid in EPSG:32644, roughly 7,000 cells for the GCC area (about 426 km², verify from the loaded boundary). Inputs at native resolution: DEM 30 m, WorldPop 100 m, buildings as vectors.

### 2.3 Run modes and time

| Mode | Purpose | Data | Alerts |
| --- | --- | --- | --- |
| replay (default demo) | Deterministic, offline-capable demonstration | Scripted storm DEMO-STORM-01 plus simulated sensors, seeded | Draft and simulated dispatch |
| backtest | Validate on historical events | IMERG/ERA5-derived rainfall and flood labels for 2015, 2020, 2021, 2023 | None |
| live-monitor | Show real feeds | Open-Meteo hourly plus IMERG Early; sensors still simulated | Drafts only; dispatch disabled by ALLOW\_LIVE\_DISPATCH=false |

Horizons: water level +15, +30, +60, +120 min; rainfall outlook hourly to 48 h. Cadence: sensors every 1 min, ward assessments every 5 min (configurable). All timestamps are stored as UTC timestamptz and shown in IST (Asia/Kolkata, UTC+05:30, no daylight saving). A simulation clock drives replay mode.

### 2.4 Terminology

- Zone (risk zone): a GCC ward. The proposal's Zone X means a ward. The 15 GCC administrative zones are called GCC zones.
- Cell: a 250 m analysis grid cell. Ward values are aggregated from cells.
- Levels: LOW, MEDIUM, HIGH, VERY\_HIGH. Plus the abstention outcome INSUFFICIENT\_EVIDENCE.
- SIM: any object produced by the simulator. Carries is\_simulated = true and an on-screen badge.
- PROTOTYPE threshold: a value chosen by this team, not by an authority.

### 2.5 Out of scope

Live GCC telemetry; 1D/2D hydraulic modelling (SWMM, HEC-RAS) in the runtime path; radar nowcasting; real SMS, IVRS or CAP delivery; citizen-report ingestion; any autonomous emergency action; other cities.

## 3. Design Principles

| # | Principle | How it is enforced |
| --- | --- | --- |
| P1 | AI is not the sensor and the LLM is not the hydrologist | Numeric fields are produced only by ewf.models, ewf.risk and ewf.geo. The LLM adapter returns text. A verifier rejects any number in generated text that is absent from the evidence payload |
| P2 | Every prediction carries evidence | risk\_predictions rows are inseparable from risk\_factors and evidence rows; the API refuses to return a risk without evidence ids |
| P3 | Human approval for high-impact action | Alert state machine in the database; dispatch endpoint requires status APPROVED and a reviewer role; agents hold no dispatch credentials |
| P4 | Uncertainty is explicit and abstention is allowed | Confidence composed from named components; INSUFFICIENT\_EVIDENCE is a first-class outcome |
| P5 | Provenance for every dataset | data\_sources table plus data/manifest.yaml with URL, licence, version, retrieval date, checksum, CRS, resolution |
| P6 | Reproducibility and auditability | Each prediction stores model\_version\_id, config\_version, input snapshot hash and feature timestamps |
| P7 | Simulation honesty | is\_simulated columns, SIM id prefix, UI badge, labelled metrics |
| P8 | Geospatial correctness | CRS rules in §8, SRID constraints in the database, CRS tests in CI |
| P9 | Time correctness | Timezone-aware datetimes only; UTC at the boundary; one Clock interface |
| P10 | Controlled learning | Candidate model, offline evaluation, human approval, versioned promotion, rollback |
| P11 | MVP restraint | Section 41 lists what must not be built |
| P12 | Graceful degradation | Every external dependency has a fallback and a visible degraded-mode flag (§28) |

## 4. Final Architecture

### 4.1 Logical architecture — twelve layers

| Layer | Responsibility | Modules | Technology |
| --- | --- | --- | --- |
| 1 Data sources | Provide observations, forecasts, static layers, labels | external | IMD, IMERG, Open-Meteo, DEM, GCC/OpenCity, OSM, WorldPop |
| 2 Ingestion and validation | Fetch, parse, validate, normalise, reject to dead letter | ewf.ingestion | httpx, pydantic, APScheduler |
| 3 Data platform | Persist time series, geometries, outputs, audit | ewf.db, db/migrations | PostgreSQL + PostGIS, Alembic, files under data/ |
| 4 Geospatial processing | Grid, terrain derivatives, zonal statistics, footprints | ewf.geo | GeoPandas, Shapely 2, rasterio, rioxarray, pysheds, scipy |
| 5 Forecasting and ML | Water-level forecast, susceptibility, rainfall outlook | ewf.models, ewf.features | LightGBM, scikit-learn |
| 6 Flood risk engine | Hazard, exposure, vulnerability, matrix, confidence | ewf.risk | pure Python, YAML config |
| 7 Multi-agent intelligence | Coordinate tools and models, route on conditions | ewf.agents | LangGraph, pydantic |
| 8 Explainability and policy | Drivers, evidence, similar events, rules, abstention | ewf.explain, ewf.decision.policy | deterministic code, SHAP where tree models are used |
| 9 Human oversight | Review, approve, modify, reject, audit | ewf.alerts.state\_machine, review UI | FastAPI, React |
| 10 Alerts, routing, response | Alert drafting, simulated dispatch, routes, shelters, resources | ewf.alerts, ewf.routing, ewf.decision.actions | OSMnx, NetworkX |
| 11 Applications | Operator dashboard, citizen view, admin, API | ewf.api, web/ | FastAPI, React, MapLibre, ECharts |
| 12 Continuous learning | Outcome capture, evaluation, recalibration candidates | ewf.learning | pandas, scikit-learn |

### 4.2 Component and data flow

```text
SOURCES                 INGEST / STORE               INTELLIGENCE                      HUMAN AND ACTION
IMD, IMERG, Open-Meteo  adapters + validators        M2 water-level forecaster         review UI: approve / modify / reject
Simulated sensors   ->  dead-letter table        ->  M1 susceptibility (static)    ->  alert state machine -> simulated channels
GCC SWD, wards, shelters PostgreSQL + PostGIS        M3 hazard function -> risk engine routing (OSMnx + NetworkX) -> shelters
DEM, LULC, WorldPop     files + manifest             agents on one LangGraph graph     outcome capture -> learning -> candidate model
```

Control flow for one ward assessment: scheduler tick or POST /risk/analyze → orchestrator → data agent → forecasting agent → risk agent → RCA agent → decision agent → policy check → alert DRAFT/PENDING\_REVIEW → human review → dispatch → outcome → learning.

### 4.3 Physical and deployment architecture (MVP)

```text
Laptop or single VM, Docker Compose
  db        postgis/postgis:16-3.4       port 5432, volume pgdata
  api       FastAPI + Uvicorn            port 8000   (models loaded in process)
  worker    APScheduler                  ingestion, assessment tick, simulation driver
  simulator sensor publisher (HTTP)      posts to api exactly like a real sensor gateway
  web       nginx serving Vite build     port 8080
  volumes   ./data (rasters, graphs, model artifacts), ./config
```

Production adds: managed PostgreSQL, MQTT broker plus Kafka for sensor streams, Kubernetes, object storage, model serving, OSRM, observability stack, OIDC. See §34.

### 4.4 Software architecture

- One Python package ewf with strict dependency direction: core ← db ← (ingestion, geo, features) ← (models, risk, explain, routing) ← (decision, alerts, learning) ← agents ← (api, worker).
- Synchronous by default. FastAPI runs blocking endpoints in its threadpool; heavy work (feature builds, model training) runs in scripts or the worker.
- Every cross-module call uses pydantic models (§14). Agents are classes with run(request) → response; the orchestrator is the only place that knows the order.
- No agent imports dispatch code. Dispatch lives in ewf.alerts.dispatcher and is reachable only from the approval endpoint.

### 4.5 AI architecture — model inventory

| ID | Component | Type | Input | Output / target | Trained on |
| --- | --- | --- | --- | --- | --- |
| M1 | Static susceptibility | LightGBM classifier plus isotonic calibration | 250 m cell terrain, HAND, sink depth, drain distance, imperviousness, history | S: probability a cell floods in a historical event | OpenCity inundation points and KML, hazard zones, Sentinel-1 and GFD masks (real) |
| M2 | Water-level forecaster | LightGBM direct multi-horizon, point plus P10/P90 | sensor lags, rise rate, rain accumulations, forecast rain, tide | level change at +15/+30/+60/+120 min | Simulator and replayed storms (synthetic, labelled) |
| M3 | Hazard function | Expert-prior logistic with two-parameter calibration | 11 normalised features, including M1 and M2 outputs | H: probability of flood-impacting inundation in a ward within the horizon | Calibrated on backtests and simulated truth |
| M4 | Rainfall outlook | Forecast feed plus trend extrapolation, no ML | Open-Meteo or ECMWF hourly, IMERG 30-min | accumulation outlook 1–48 h | none |
| R | Risk engine | Deterministic | H, E, V, confidence | level, risk index | YAML config |
| X | Explainer | Deterministic decomposition plus templates | M3 terms, evidence rows | drivers, evidence ids, text | none |
| L | LLM (optional) | Provider adapter | structured JSON only | prose and translation | none |

### 4.6 What is deliberately simplified relative to the concept diagrams

| Concept diagram element | MVP decision |
| --- | --- |
| Kafka / MQTT / stream processing (Flink, Spark) | HTTP ingestion plus APScheduler. An MQTT bridge is an optional stretch |
| Vector database | PostgreSQL full-text search over about 50 curated knowledge chunks |
| Feature store | SQL tables and materialised views plus versioned feature code |
| Object storage | Files under data/ with a manifest (MinIO in production) |
| Model serving platform | Models loaded in process; LLM through a provider adapter |
| Kubernetes, ELK, Grafana stack | Compose, structured JSON logs, a /metrics endpoint; Grafana as an optional profile |
| Mapbox | MapLibre GL (no token, offline-capable) |
| Mobile app and embeddable widget | Responsive citizen web view; widget is a production item |
| HEC-RAS or SWMM hydraulics | Not in the runtime path; indicative footprints; optional offline calibration notebook |

## 5. Technology Stack

### 5.1 Evaluation and decision table

| Component | Selected | Why | Alternative considered | Why not | MVP | Production |
| --- | --- | --- | --- | --- | --- | --- |
| Language and runtime | Python 3.11 | One language for API, geospatial, ML and agents | Node.js or Go backend | Geospatial and ML libraries live in Python | Yes | Yes |
| API framework | FastAPI, Uvicorn, Pydantic v2 | Typed contracts, automatic OpenAPI, easy testing | Flask, Django REST | No typed models, more boilerplate | Yes | Yes, Gunicorn workers |
| Primary store | PostgreSQL 16 + PostGIS 3.4 | Spatial SQL, JSONB, full-text search, one database for everything | MongoDB; SQLite with SpatiaLite | Weak spatial support; poor concurrency | Yes | Managed PostgreSQL |
| Time series | Plain PostgreSQL tables, hypertable-ready | About 72,000 sensor rows per day (50 sensors, 1-minute cadence); a composite primary key and one index suffice | TimescaleDB; InfluxDB | Extra service, no benefit at this volume | Yes | TimescaleDB or partitioning |
| Object storage | Local volume plus manifest | Rasters, graphs and model files total a few GB | MinIO; S3 | Extra service | Yes | S3 or MinIO |
| Cache and queue | None (PostgreSQL plus APScheduler) | No workload needs one | Redis, Celery, RabbitMQ | Moving parts without need | No | Redis Streams or Kafka |
| Sensor transport | HTTP ingestion contract | Testable; identical payload to production | MQTT; Kafka | A broker becoming unhealthy is a demo risk | Yes, HTTP | MQTT into Kafka |
| Scheduling | APScheduler 3.x | In-process and simple | Airflow, Prefect, Dagster, cron | Heavy for six jobs | Yes | Prefect or Kubernetes CronJobs |
| Migrations | Alembic, SQL-first revisions | Versioned schema; PostGIS DDL stays raw SQL | Flyway; hand-run scripts | Not Python-native; no history | Yes | Yes |
| Database access | SQLAlchemy 2.0 Core, psycopg2-binary, GeoAlchemy2 for GeoPandas I/O | GeoPandas to\_postgis and read\_postgis need an SQLAlchemy engine | psycopg3 only; full ORM | Less proven with GeoAlchemy2; ORM mapping adds code with no gain | Yes | psycopg3 later |
| Vector and raster | GeoPandas, Shapely 2, pyproj, rasterio, rioxarray, xarray, scipy | PyPI wheels bundle GDAL, GEOS and PROJ | GDAL command line; ArcPy | Not reproducible, or licence-bound | Yes | Add Dask for scale |
| Terrain derivatives | pysheds plus scipy distance transform | Pit and depression filling, flow accumulation and HAND-approx in Python | WhiteboxTools; GRASS; RichDEM | Binary download or heavier install (Whitebox is the fallback) | Yes | WhiteboxTools or GRASS batch |
| GIS inspection | QGIS | Visual check of every layer | n/a | Not a runtime dependency | Dev only | Dev only |
| Web map | MapLibre GL JS | No token, data-driven styling, offline PMTiles possible | Leaflet; Mapbox GL | Leaflet is weak for styling many polygons by data; Mapbox needs a token and billing | Yes | MapLibre with Martin vector tiles |
| Tabular ML | LightGBM, scikit-learn, SHAP | Small data, monotone constraints, quantile objective | XGBoost; Random Forest; TensorFlow | XGBoost is equivalent so one library is enough; Random Forest lacks quantiles and monotonicity; TensorFlow unnecessary | Yes | Same |
| Deep learning | None in the serving path | No real sequential labels exist; synthetic data would simply be learned back | LSTM, GRU, ConvLSTM, Transformers | Not justified by the data; opaque | No | After one or two monsoons of real telemetry |
| Rainfall nowcasting | None; forecast feeds plus trend extrapolation | No radar access | TCN or U-Net; pysteps | Need radar archives | No | When IMD radar access is granted |
| Hydraulics | None in the runtime path | Cannot be built and validated in hackathon time | SWMM; HEC-RAS | Parameter-heavy; drain capacities are unpublished | No | Calibrated SWMM for priority wards |
| Agent framework | LangGraph, exact version pinned | Conditional edges, typed state, tracing | Plain Python state machine; CrewAI; AutoGen | CrewAI and AutoGen let the LLM steer control flow, which is forbidden here; plain Python is the tested fallback | Yes | Same plus a Postgres checkpointer |
| LLM | Provider adapter with modes off, template, llm; default a small low-cost model | Prose and translation only. Default value claude-haiku-5-5; verify availability and price at build time | Gemini Flash-class; local Ollama; frontier models | Frontier models add cost with no benefit for templated prose | Optional | Provider with an SLA, or on-premise |
| Routing | OSMnx plus NetworkX | Full control of edge costs from predicted risk | OSRM; OpenRouteService; GraphHopper | Dynamic penalties need custom profiles and server setup | Yes | OSRM or GraphHopper with live closures |
| Frontend | React 18, TypeScript, Vite | Mature map and chart ecosystem | Next.js; Streamlit | No SSR needed; Streamlit is weak for maps, roles and approvals | Yes | Same |
| Charts | Apache ECharts | Thresholds, bands and heatmaps built in | Plotly; Recharts | Plotly is heavy; Recharts is weak for confidence bands | Yes | Same |
| Fetching, state, styling | TanStack Query, Zustand, Tailwind CSS | Polling, caching, fast UI work | Redux; MUI | Verbose; heavier | Yes | Same |
| Authentication | PyJWT, bcrypt, six seeded demo roles | No extra service | Keycloak; Auth0 | Extra service | Yes | OIDC with Keycloak or Azure AD |
| Containers | Docker and Compose | One-command start | Podman; Kubernetes | Kubernetes is unnecessary for one machine | Yes | Kubernetes and Helm |
| CI | GitHub Actions | ruff, mypy, pytest with a PostGIS service container, web build | GitLab CI | Assumes the team uses GitHub | Yes | Same plus image scanning |
| Observability | structlog JSON logs, prometheus\_client, optional Grafana profile | Enough to evidence the metrics in §30 | ELK; OpenTelemetry collector | Heavy | Yes | Prometheus, Grafana, Loki, OpenTelemetry |

### 5.2 Final recommended stack (decided)

- Backend: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 Core, Alembic, APScheduler 3.x, httpx.
- Data: PostgreSQL 16 with PostGIS 3.4 as the single database; files under data/ with a manifest; GeoParquet for vectors, Cloud Optimized GeoTIFF for rasters.
- Geospatial: GeoPandas, Shapely 2, pyproj, rasterio, rioxarray, pysheds, scipy, OSMnx 2.x, NetworkX.
- ML: LightGBM, scikit-learn, SHAP, pandas, numpy.
- Agents: LangGraph (pinned) with typed Python agents; LLM mode defaults to template, optional small model for prose.
- Frontend: React 18, TypeScript, Vite, MapLibre GL JS, ECharts, TanStack Query, Zustand, Tailwind CSS.
- Operations: Docker Compose, GitHub Actions, structlog, prometheus\_client, pytest, ruff, mypy.

### 5.3 Version policy

Pin exact versions in pyproject.toml and a lockfile (uv lock or pip-compile) on day one. The skeletons in this manual target current major versions: SQLAlchemy 2.x, Pydantic 2.x, GeoPandas 1.x, Shapely 2.x, LightGBM 4.x, OSMnx 2.x, LangGraph 1.x, APScheduler 3.x. Library APIs move; if a call in a skeleton fails, read the pinned version's documentation first. Change the lockfile only between roadmap phases, never in demo week.

## 6. Data Architecture

### 6.1 Layers and rules

- data/raw: immutable downloads. File names carry source, version and retrieval date. Git-ignored.
- data/interim: scripted intermediates (clipped, reprojected).
- data/processed: model-ready files. GeoParquet for vectors, Cloud Optimized GeoTIFF for rasters, Parquet for tables. Each file has a sidecar JSON holding input hashes, parameters, git commit, CRS and resolution.
- Database: the serving layer for queries and outputs, loaded from processed files by scripts/build\_db.py, which is idempotent.
- Rules: every dataset has a manifest entry; every script that writes a file writes its sidecar; CRS is explicit on every layer; no manual edits (fix the upstream script); raw and processed files are never committed, but the manifest and scripts are.

### 6.2 Dataset register

Priority and availability follow the Dataset Research Report and both guidebooks. Items marked optional are not on the MVP critical path.

| ID | Dataset and source | Ingestion, raw to processed | Refresh and validation | CRS, time, storage | Derived features |
| --- | --- | --- | --- | --- | --- |
| D01 | GCC wards (200) and GCC zones (15); GCC ArcGIS service or OpenCity | ArcGIS REST query with pagination, GeoJSON, then GeoPackage, then zones | Static. make\_valid, 200 unique ward numbers, no material overlaps | Stored 4326 plus UTM 44N copy; table zones | area, centroid, adjacency |
| D02 | IMD gridded rainfall, 0.25 deg daily; IMD Pune via imdlib | imdlib download, GRD to Parquet per AOI cell | Annual plus provisional. -999 to NULL; 0 to 1000 mm/day | Cell centroids 4326; IST day converted to UTC bounds; rainfall\_observations | climatology, extreme-day percentiles |
| D03 | Chennai station rainfall (OpenCity IMD extracts; IMD stations on request) | CSV to Parquet | Static. Dedupe, unit check in mm | Points 4326; IST to UTC | bias factors for gridded products |
| D04 | GPM IMERG half-hourly via earthaccess | HDF5 to clipped NetCDF to Parquet; precipitation in mm/hr | Every 30 min; Early Run lag about 4 h. 0 to 300 mm/hr, missing flag | 0.1 deg grid, UTC; rainfall\_observations | accumulations 15/30/60/180 min, antecedent 24 h and 72 h |
| D05 | Forecast: Open-Meteo hourly precipitation (primary); ECMWF open data and IMD API optional | httpx JSON to rows | Hourly, cached 30 min; stale if issue time older than 3 h | One point per AOI centroid, UTC; rainfall\_forecasts | forecast accumulation next 60/120 min, 6 h, 24 h |
| D06 | ERA5 hourly via CDS API (backtests, climatology) | NetCDF to Parquet | Static | 0.25 deg, UTC | context percentiles |
| D07 | Optional context series: tide (INCOIS, PSMSL), reservoir levels (CMWSSB public pages) | Adapters off by default; replay mode uses a labelled synthetic tide | Hourly to daily. Check terms before scraping | Points, UTC; context\_series | tide state, reservoir fill fraction |
| D08 | Copernicus DEM GLO-30 (fallback SRTM 1 arc-second, then GLO-90) | Tiles from AWS Open Data or Copernicus Data Space, mosaic, clip to AOI plus 10 km, COG | Static. Void fill; elevation within -5 to 100 m | UTM 44N, 30 m; datum note in §6.4 | elevation, slope, sink depth, HAND-approx, TWI |
| D09 | GCC stormwater drains (OpenCity SWD 2023 KML; GCC ArcGIS) | KML via pyogrio to GeoPackage to drainage\_nodes and drainage\_edges | Static. Repair, dedupe, per-ward coverage report | 4326 plus UTM | drain density, distance to nearest drain |
| D10 | Waterbodies and basin drainage (OpenCity); JRC Global Surface Water | Vector to GeoPackage; occurrence raster to COG | Static | 4326 and UTM | distance to water, permanent-water mask |
| D11 | ESA WorldCover 2021 (10 m); GHSL built-up | COG tiles, clip, 250 m class fractions | Annual | UTM 44N | impervious fraction, green fraction |
| D12 | Buildings: Google Open Buildings v3 (fallbacks Microsoft, OSM) | Shards, clip, buildings; keep confidence at or above the configured minimum | Static. Valid geometry, overlap dedupe | 4326 plus UTM | count and area per cell |
| D13 | Population: WorldPop India 100 m with age and sex | GeoTIFF summed into 250 m cells and wards (total conserved) | Annual. Vintage stored; total sanity check | Raster 4326 to UTM cells | population, under-5 share, over-65 share |
| D14 | Roads: OpenStreetMap through OSMnx (drive and walk) | Download by AOI polygon to GraphML plus roads table | Monthly snapshot. Largest strongly connected component only | Graph 4326; lengths in metres via UTM | edge min elevation, HAND, underpass flag, static susceptibility |
| D15 | Critical facilities: OSM amenities (hospital, school, fire station, police, substation) plus OpenCity | Overpass to GeoPackage to critical\_facilities | Quarterly. Dedupe by name and distance | 4326 plus UTM | facility weights, exposed counts |
| D16 | Shelters and relief centres (OpenCity, GCC) | Download, clean, shelters; capacity may be unknown | Static. capacity\_known flag; location inside GCC | 4326 plus UTM | shelter flood safety |
| D17 | Flood labels: OpenCity KML (2005, 2015, 2020, hazard zones by return period), Bhuvan hazard layers, GFD, Sentinel-1 masks (2015, 2021, 2023) | KML or GeoTIFF to GeoPackage to flood\_extents and historical\_flood\_events | Static. Provenance and confidence per label; overlaps resolved by priority | 4326 to UTM; event dates UTC | historical frequency, labels for M1 |
| D18 | Flood incident points with depth (OpenCity, inches; 2024 waterlogging datajam) | flood\_incidents, inches converted to cm | Static | 4326 | validation and label support |
| D19 | Simulated sensors (ewf.simulation) | HTTP POST batches | Every 1 min of simulation time | UTC | M2 features |
| D20 | Scenario definitions (YAML) | Files in config/scenarios | n/a | UTC offsets from T0 | storm hyetographs, fault schedules |
| D21 | Knowledge base: NDMA urban flooding guidelines (public), team response text | Markdown chunks to kb\_chunks with tsvector | Manual | n/a | retrieval for explanations |

### 6.3 Canonical entities and conventions

| Entity | Key fields | Conventions |
| --- | --- | --- |
| Rainfall observation | station\_id, observed\_at, interval\_minutes, rain\_mm, intensity\_mm\_hr, source, quality\_flag | observed\_at is the END of the accumulation interval, UTC |
| Rainfall forecast | station\_id, issued\_at, valid\_at, source, model, rain\_mm, p10, p90 | valid\_at is the end of the interval; lead time is derived |
| Water level | sensor\_id, observed\_at, level\_cm, rise\_rate\_cm\_min, battery\_percent, signal\_dbm, status, quality\_flag | level\_cm is height above the drain invert at the sensor |
| Sensor | sensor\_id (prefix SIM-), drain\_edge\_id, zone\_id, geom, depth\_cm, warn\_cm, critical\_cm, is\_simulated | Thresholds share the level datum |
| Terrain cell | cell\_id, elev\_mean\_m, elev\_min\_m, slope\_deg, sink\_depth\_m, hand\_m, twi, dist\_drain\_m, dist\_water\_m | Relative indices, not street-level depths |
| Drainage | node\_id, edge\_id, geometry, drain\_type, optional dimensions and condition | Capacity attributes are usually NULL |
| Flood event and extent | event\_id, dates, source, confidence; geometry, kind, valid\_from, valid\_to | kind separates observed from predicted |
| Roads | edge id, osm\_way\_id, highway, length\_m, bridge, tunnel, min\_elev\_m, hand\_m | Lengths from UTM geometry |
| Buildings, population | building\_id, area\_m2, confidence, cell\_id; cell\_id, pop\_total, pop\_u5, pop\_o65, year | Population totals conserved on resampling |
| Shelters, hospitals, critical facilities | id, kind, name, geom, capacity, capacity\_known | Unknown capacity stays NULL, never guessed |
| Risk prediction | prediction\_id, zone\_id, issued\_at, horizon\_minutes, probability, scores, level, confidence, versions | Always joined to factors and evidence |
| Alerts, actions, outcomes | See §7 and §27 | State machine in §18 |

### 6.4 Datum and accuracy caveats

- Elevation: Copernicus DEM heights are orthometric (EGM2008); SRTM uses EGM96. Do not mix tiles from different DEMs without conversion. In Chennai's flat terrain a 30 m DEM error of a few metres is comparable to the signal, so HAND and sink depth are used as relative indices and are never quoted as street-level flood depth.
- Water levels use a sensor datum: cm above the drain invert at the sensor. This is not mean sea level.
- Rainfall grids are areal averages and understate point extremes. Intensity in mm/hr is derived from accumulation over the stated interval.
- Population is residential and static. It is never presented as live movement.
- Drain capacity, siltation and blockage are not published. The simulator and the confidence model treat them as uncertain parameters (§9.5, §17).

### 6.5 Provenance manifest entry (data/manifest.yaml)

```yaml
- id: D08
  name: Copernicus DEM GLO-30
  source_url: <fill at download>
  licence: <fill at download>
  version: <tile version or date>
  retrieved_at: 2026-10-10T09:00:00Z
  sha256: <hash>
  crs: EPSG:4326 raw, EPSG:32644 processed
  resolution: 30 m
  processing: scripts/build_terrain.py --aoi config/aoi.yaml
  used_by: [M1, risk.exposure]
```

## 7. Database Specification

### 7.1 Conventions

- One PostgreSQL database with the PostGIS extension, default public schema. Migrations live in db/migrations (Alembic); revision 0001 executes db/sql/0001\_baseline.sql, later revisions are additive.
- Keys: text natural keys for reference data (W112, SIM-SWD-W112-004), uuid for generated rows.
- Geometry: geom in EPSG:4326 (interchange, display) and geom\_utm in EPSG:32644 (metric work). A trigger fills geom\_utm, so loaders write geom only. Both are GiST indexed.
- Time: timestamptz only, UTC. Rainfall observed\_at is the end of the accumulation interval.
- Enumerations are CHECK constraints so they can evolve. JSONB holds snapshots and payloads, never fields that are queried routinely.
- Anything simulated carries is\_simulated; nothing simulated is inserted without it.
- Key relationships: zones 1-N grid\_cells 1-1 terrain\_features; zones 1-N water\_level\_sensors 1-N water\_level\_observations; risk\_predictions 1-N risk\_factors, evidence, explanations, alerts, evacuation\_routes, recommended\_actions, prediction\_outcomes; alerts 1-N human\_reviews, alert\_recipients, response\_actions.
- All 29 tables named in the brief are present, plus 16 supporting tables: users, data\_sources, ingestion\_runs, rejected\_records, config\_versions, grid\_cells, zone\_static\_features, context\_series, flood\_incidents, evidence, subscribers, agent\_runs, tool\_calls, kb\_chunks, scenarios, sim\_state.

### 7.2 DDL part 1 — governance, reference and static layers

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE OR REPLACE FUNCTION set_geom_utm() RETURNS trigger AS $$
BEGIN
  NEW.geom_utm := ST_Transform(NEW.geom, 32644);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text NOT NULL UNIQUE, display_name text, password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('citizen','municipal_operator','emergency_coordinator','administrator','researcher','system_service')),
  active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE data_sources (
  source_id text PRIMARY KEY, name text NOT NULL, url text, licence text, version text,
  retrieved_at timestamptz, sha256 text, crs text, resolution text, notes text
);
CREATE TABLE ingestion_runs (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id text REFERENCES data_sources, adapter text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
  status text NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING','OK','PARTIAL','FAILED')),
  rows_in int NOT NULL DEFAULT 0, rows_ok int NOT NULL DEFAULT 0, rows_rejected int NOT NULL DEFAULT 0, error text
);
CREATE TABLE rejected_records (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id uuid REFERENCES ingestion_runs, rejected_at timestamptz NOT NULL DEFAULT now(),
  reason text NOT NULL, payload jsonb NOT NULL
);
CREATE TABLE config_versions (
  config_version text PRIMARY KEY, sha256 text NOT NULL, content jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), created_by uuid REFERENCES users
);
CREATE TABLE model_versions (
  model_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL, version text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('SUSCEPTIBILITY','WL_FORECAST','HAZARD_FUNCTION','RISK_CONFIG','OTHER')),
  framework text, artifact_uri text, data_manifest_sha256 text, git_sha text,
  params jsonb NOT NULL DEFAULT '{}'::jsonb, metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  trained_on_synthetic boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'CANDIDATE' CHECK (status IN ('CANDIDATE','STAGING','PRODUCTION','RETIRED')),
  trained_at timestamptz NOT NULL DEFAULT now(), promoted_by uuid REFERENCES users, promoted_at timestamptz, notes text,
  UNIQUE (name, version)
);
CREATE UNIQUE INDEX ux_one_production_model ON model_versions (name) WHERE status = 'PRODUCTION';

CREATE TABLE zones (
  zone_id text PRIMARY KEY,                       -- W112
  ward_no int NOT NULL UNIQUE, ward_name text, gcc_zone_no int, gcc_zone_name text,
  geom geometry(MultiPolygon,4326) NOT NULL, geom_utm geometry(MultiPolygon,32644),
  area_km2 numeric(9,3), is_coastal boolean NOT NULL DEFAULT false,
  in_aoi boolean NOT NULL DEFAULT false, is_hero boolean NOT NULL DEFAULT false,
  coverage jsonb NOT NULL DEFAULT '{}'::jsonb      -- drains, shelters, sensors, labels flags
);
CREATE TABLE grid_cells (                          -- 250 m cells, assigned to a ward by centroid
  cell_id text PRIMARY KEY, zone_id text REFERENCES zones,
  geom geometry(Polygon,4326) NOT NULL, geom_utm geometry(Polygon,32644),
  centroid geometry(Point,4326) NOT NULL, area_m2 real NOT NULL
);
CREATE TABLE terrain_features (
  cell_id text PRIMARY KEY REFERENCES grid_cells,
  elev_mean_m real, elev_min_m real, elev_p10_m real, slope_deg real, sink_depth_m real,
  hand_m real, twi real, dist_drain_m real, dist_water_m real, drain_density_km_km2 real,
  imperv_frac real CHECK (imperv_frac BETWEEN 0 AND 1), green_frac real,
  hist_freq real CHECK (hist_freq BETWEEN 0 AND 1),
  susceptibility real CHECK (susceptibility BETWEEN 0 AND 1),   -- M1 output S
  susceptibility_model_id uuid REFERENCES model_versions, feature_version text NOT NULL DEFAULT 'v1'
);
CREATE TABLE population_grids (
  cell_id text NOT NULL REFERENCES grid_cells, year int NOT NULL,
  pop_total real NOT NULL, pop_u5 real, pop_o65 real, source_id text REFERENCES data_sources,
  PRIMARY KEY (cell_id, year)
);
CREATE TABLE drainage_nodes (
  node_id text PRIMARY KEY,
  kind text NOT NULL DEFAULT 'junction' CHECK (kind IN ('inlet','junction','outfall','culvert','pump','unknown')),
  geom geometry(Point,4326) NOT NULL, geom_utm geometry(Point,32644),
  invert_elev_m real, zone_id text REFERENCES zones
);
CREATE TABLE drainage_edges (                      -- explode MultiLineString to LineString on load
  edge_id text PRIMARY KEY, from_node text REFERENCES drainage_nodes, to_node text REFERENCES drainage_nodes,
  drain_type text NOT NULL DEFAULT 'storm_drain' CHECK (drain_type IN ('storm_drain','micro_drain','canal','river','culvert','unknown')),
  geom geometry(LineString,4326) NOT NULL, geom_utm geometry(LineString,32644),
  length_m real, width_m real, depth_m real, capacity_m3s real, condition text,   -- usually NULL
  zone_id text REFERENCES zones, source_id text REFERENCES data_sources
);
CREATE TABLE roads (
  edge_id text PRIMARY KEY, osm_way_id bigint, name text, highway text,
  length_m real NOT NULL, maxspeed_kph real,
  is_bridge boolean NOT NULL DEFAULT false, is_tunnel boolean NOT NULL DEFAULT false, is_underpass boolean NOT NULL DEFAULT false,
  geom geometry(LineString,4326) NOT NULL, geom_utm geometry(LineString,32644),
  zone_id text REFERENCES zones, min_elev_m real, hand_m real, static_susceptibility real, graph_version text
);
CREATE TABLE buildings (
  building_id text PRIMARY KEY, source text NOT NULL, area_m2 real NOT NULL, confidence real,
  geom geometry(Polygon,4326) NOT NULL, geom_utm geometry(Polygon,32644),
  cell_id text REFERENCES grid_cells, zone_id text REFERENCES zones
);
CREATE TABLE critical_facilities (
  facility_id text PRIMARY KEY,
  kind text NOT NULL CHECK (kind IN ('hospital','school','fire_station','police','power','water_works','other')),
  name text, geom geometry(Point,4326) NOT NULL, geom_utm geometry(Point,32644),
  zone_id text REFERENCES zones, weight real NOT NULL DEFAULT 1, beds int, source_id text REFERENCES data_sources
);
CREATE TABLE shelters (
  shelter_id text PRIMARY KEY, name text NOT NULL, kind text,
  geom geometry(Point,4326) NOT NULL, geom_utm geometry(Point,32644),
  zone_id text REFERENCES zones, capacity int, capacity_known boolean NOT NULL DEFAULT false,
  has_medical boolean NOT NULL DEFAULT false, accessible boolean, contact text,
  flood_safety real,                                -- 1 minus susceptibility at the location
  source_id text REFERENCES data_sources
);
CREATE TABLE zone_static_features (
  zone_id text PRIMARY KEY REFERENCES zones, feature_version text NOT NULL,
  s_mean real, s_p90 real, elev_p10_m real, hand_p10_m real, pct_area_hand_lt_1m real,
  sink_depth_max_m real, drain_density_km_km2 real, imperv_frac real, hist_freq real,
  pop_total real, pop_u5_share real, pop_o65_share real, bldg_count int, road_km real,
  e_score real, v_score real, exposure_components jsonb, vulnerability_components jsonb,
  computed_at timestamptz NOT NULL DEFAULT now()
);
```

### 7.3 DDL part 2 — observations, history, predictions, decisions, learning, audit

```sql
CREATE TABLE stations (
  station_id text PRIMARY KEY, name text,
  kind text NOT NULL CHECK (kind IN ('IMD_STATION','GRID_IMD','GRID_IMERG','GRID_ERA5','FORECAST_POINT','SIM_GAUGE')),
  geom geometry(Point,4326) NOT NULL, geom_utm geometry(Point,32644),
  zone_id text REFERENCES zones, elevation_m real,
  is_simulated boolean NOT NULL DEFAULT false, active boolean NOT NULL DEFAULT true
);
CREATE TABLE rainfall_observations (
  station_id text NOT NULL REFERENCES stations, observed_at timestamptz NOT NULL,   -- END of interval, UTC
  interval_minutes smallint NOT NULL CHECK (interval_minutes > 0),
  rain_mm real NOT NULL CHECK (rain_mm >= 0),
  intensity_mm_hr real GENERATED ALWAYS AS ((rain_mm * 60.0 / interval_minutes)::real) STORED,
  source text NOT NULL,
  quality_flag text NOT NULL DEFAULT 'OK' CHECK (quality_flag IN ('OK','SUSPECT','BAD','FILLED')),
  ingested_at timestamptz NOT NULL DEFAULT now(), run_id uuid REFERENCES ingestion_runs,
  PRIMARY KEY (station_id, observed_at, interval_minutes)
);
CREATE TABLE rainfall_forecasts (
  station_id text NOT NULL REFERENCES stations, issued_at timestamptz NOT NULL, valid_at timestamptz NOT NULL,
  interval_minutes smallint NOT NULL DEFAULT 60, source text NOT NULL, model text NOT NULL DEFAULT 'default',
  rain_mm real NOT NULL CHECK (rain_mm >= 0), p10_mm real, p90_mm real,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (station_id, issued_at, valid_at, source, model)
);
CREATE TABLE water_level_sensors (
  sensor_id text PRIMARY KEY CHECK (sensor_id ~ '^[A-Za-z0-9_-]+$'),
  drain_edge_id text REFERENCES drainage_edges, zone_id text NOT NULL REFERENCES zones,
  geom geometry(Point,4326) NOT NULL, geom_utm geometry(Point,32644),
  sensor_type text NOT NULL DEFAULT 'SIMULATED' CHECK (sensor_type IN ('SIMULATED','ULTRASONIC','RADAR','PRESSURE')),
  is_simulated boolean NOT NULL DEFAULT true,
  drain_depth_cm real NOT NULL, warn_cm real NOT NULL, critical_cm real NOT NULL,
  status text NOT NULL DEFAULT 'ONLINE' CHECK (status IN ('ONLINE','DEGRADED','OFFLINE','MAINTENANCE')),
  installed_at timestamptz, last_seen_at timestamptz, battery_percent real, meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  CHECK (warn_cm < critical_cm AND critical_cm <= drain_depth_cm * 1.2),
  CHECK (is_simulated = (sensor_type = 'SIMULATED'))
);
CREATE TABLE water_level_observations (
  sensor_id text NOT NULL REFERENCES water_level_sensors, observed_at timestamptz NOT NULL,
  level_cm real NOT NULL CHECK (level_cm BETWEEN 0 AND 1000), rise_rate_cm_min real,
  battery_percent real, signal_dbm real, status text NOT NULL DEFAULT 'ONLINE',
  quality_flag text NOT NULL DEFAULT 'OK' CHECK (quality_flag IN ('OK','SUSPECT','BAD')),
  sensor_confidence real NOT NULL DEFAULT 1 CHECK (sensor_confidence BETWEEN 0 AND 1),
  received_at timestamptz NOT NULL DEFAULT now(), is_simulated boolean NOT NULL DEFAULT true,
  PRIMARY KEY (sensor_id, observed_at)
);
CREATE TABLE context_series (
  series_id text NOT NULL, kind text NOT NULL CHECK (kind IN ('TIDE','RESERVOIR','OTHER')),
  observed_at timestamptz NOT NULL, value real NOT NULL, unit text NOT NULL,
  is_simulated boolean NOT NULL DEFAULT false, PRIMARY KEY (series_id, observed_at)
);

CREATE TABLE historical_flood_events (
  event_id text PRIMARY KEY, name text NOT NULL, start_at timestamptz NOT NULL, end_at timestamptz,
  peak_rain_mm_24h real, description text, source_id text REFERENCES data_sources,
  confidence text NOT NULL DEFAULT 'MEDIUM' CHECK (confidence IN ('LOW','MEDIUM','HIGH')),
  validation_status text NOT NULL DEFAULT 'UNVERIFIED', feature_vector jsonb   -- for similarity search
);
CREATE TABLE flood_extents (
  extent_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), event_id text REFERENCES historical_flood_events,
  kind text NOT NULL CHECK (kind IN ('OBSERVED_SAR','OBSERVED_KML','GFD','HAZARD_ZONE','INDICATIVE_PREDICTED','SIM_TRUTH')),
  valid_from timestamptz, valid_to timestamptz,
  geom geometry(MultiPolygon,4326) NOT NULL, geom_utm geometry(MultiPolygon,32644),
  area_km2 real, return_period_years int, prediction_id uuid, confidence real, source_id text REFERENCES data_sources
);
CREATE TABLE flood_incidents (
  incident_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), event_id text REFERENCES historical_flood_events,
  geom geometry(Point,4326) NOT NULL, depth_cm real, reported_at timestamptz,
  zone_id text REFERENCES zones, source_id text REFERENCES data_sources
);

CREATE TABLE risk_predictions (
  prediction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id text NOT NULL REFERENCES zones, issued_at timestamptz NOT NULL,
  horizon_minutes int NOT NULL CHECK (horizon_minutes > 0),
  status text NOT NULL DEFAULT 'OK' CHECK (status IN ('OK','INSUFFICIENT_EVIDENCE','DEGRADED')),
  probability real CHECK (probability BETWEEN 0 AND 1),
  hazard_score real CHECK (hazard_score BETWEEN 0 AND 1), exposure_score real CHECK (exposure_score BETWEEN 0 AND 1),
  vulnerability_score real CHECK (vulnerability_score BETWEEN 0 AND 1), impact_index real, risk_index real,
  risk_level text CHECK (risk_level IN ('LOW','MEDIUM','HIGH','VERY_HIGH')),
  time_to_impact_min int, confidence_score real CHECK (confidence_score BETWEEN 0 AND 1),
  confidence_level text CHECK (confidence_level IN ('LOW','MEDIUM','HIGH')), confidence_components jsonb,
  model_version_ids uuid[] NOT NULL DEFAULT '{}', config_version text REFERENCES config_versions,
  inputs_hash text NOT NULL, feature_snapshot jsonb NOT NULL,
  mode text NOT NULL DEFAULT 'replay' CHECK (mode IN ('replay','backtest','live')), scenario_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (zone_id, issued_at, horizon_minutes, inputs_hash),
  CHECK (status <> 'OK' OR (probability IS NOT NULL AND risk_level IS NOT NULL AND confidence_score IS NOT NULL))
);
ALTER TABLE flood_extents ADD CONSTRAINT fk_extent_prediction FOREIGN KEY (prediction_id) REFERENCES risk_predictions(prediction_id);
CREATE TABLE evidence (
  evidence_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('RAIN_OBS','SENSOR_OBS','FORECAST','TERRAIN_STAT','DRAINAGE_STAT','HISTORICAL_EVENT','MODEL_OUTPUT','RULE','KB_CHUNK')),
  ref_table text, ref_key text, observed_at timestamptz, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE risk_factors (
  factor_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions ON DELETE CASCADE,
  factor_key text NOT NULL, driver_group text NOT NULL, value real, unit text, contribution_pct real,
  direction text CHECK (direction IN ('INCREASES','DECREASES')), impact_band text CHECK (impact_band IN ('HIGH','MEDIUM','LOW')),
  evidence_id uuid REFERENCES evidence, rank smallint
);
CREATE TABLE explanations (
  explanation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions ON DELETE CASCADE,
  mode text NOT NULL CHECK (mode IN ('template','llm')), llm_model text,
  text_en text NOT NULL, text_ta text, structured jsonb NOT NULL,
  verified boolean NOT NULL DEFAULT false, verification_report jsonb,
  similar_event_ids text[] NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE alerts (
  alert_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions, zone_id text NOT NULL REFERENCES zones,
  severity text NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','VERY_HIGH')),
  status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','AI_GENERATED','PENDING_REVIEW','CHANGES_REQUESTED','REJECTED','APPROVED','DISPATCHED','ACTIVE','RESOLVED','EXPIRED','SUPERSEDED','CANCELLED')),
  headline text NOT NULL, body_en text NOT NULL, body_ta text, channels text[] NOT NULL DEFAULT '{}',
  payload jsonb NOT NULL, requires_review boolean NOT NULL DEFAULT true, low_confidence boolean NOT NULL DEFAULT false,
  valid_until timestamptz, supersedes_alert_id uuid REFERENCES alerts, created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), approved_at timestamptz, dispatched_at timestamptz,
  is_simulated boolean NOT NULL DEFAULT true, mode text NOT NULL DEFAULT 'replay'
);
CREATE TABLE subscribers (
  subscriber_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), zone_id text NOT NULL REFERENCES zones,
  channel text NOT NULL CHECK (channel IN ('SMS','APP','EMAIL','IVRS')), address_hash text NOT NULL,
  language text NOT NULL DEFAULT 'en' CHECK (language IN ('en','ta')),
  consent boolean NOT NULL DEFAULT false, is_synthetic boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE alert_recipients (
  alert_id uuid NOT NULL REFERENCES alerts ON DELETE CASCADE, subscriber_id uuid NOT NULL REFERENCES subscribers,
  channel text NOT NULL, status text NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','SIMULATED_SENT','RETRY','FAILED')),
  attempts smallint NOT NULL DEFAULT 0, sent_at timestamptz, error text,
  PRIMARY KEY (alert_id, subscriber_id, channel)
);
CREATE TABLE evacuation_routes (
  route_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions, alert_id uuid REFERENCES alerts,
  origin_zone_id text NOT NULL REFERENCES zones, origin geometry(Point,4326) NOT NULL,
  shelter_id text NOT NULL REFERENCES shelters, profile text NOT NULL CHECK (profile IN ('walk','drive')),
  rank smallint NOT NULL, distance_m real NOT NULL, duration_s real NOT NULL,
  safety_score real NOT NULL CHECK (safety_score BETWEEN 0 AND 100), max_segment_risk real, mean_segment_risk real,
  blocked_edges int NOT NULL DEFAULT 0, geom geometry(LineString,4326) NOT NULL,
  graph_version text NOT NULL, computed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE recommended_actions (
  action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions, alert_id uuid REFERENCES alerts,
  action_type text NOT NULL CHECK (action_type IN ('MONITOR','PREPARE','ISSUE_ALERT','OPEN_SHELTER','EVACUATION_ROUTE','DEPLOY_TEAM','NOTIFY_AUTHORITY','PRIORITISE_FACILITY','ALLOCATE_RESOURCE')),
  priority smallint NOT NULL, target jsonb NOT NULL DEFAULT '{}'::jsonb, rationale text NOT NULL,
  policy_rule_ids text[] NOT NULL DEFAULT '{}', requires_approval boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','APPROVED','REJECTED','DONE'))
);
CREATE TABLE human_reviews (
  review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id uuid NOT NULL REFERENCES alerts, reviewer_id uuid NOT NULL REFERENCES users,
  decision text NOT NULL CHECK (decision IN ('APPROVE','MODIFY_APPROVE','REJECT','REQUEST_CHANGES')),
  comment text, modifications jsonb, evidence_opened boolean NOT NULL DEFAULT false,
  acknowledged_low_confidence boolean NOT NULL DEFAULT false, decided_at timestamptz NOT NULL DEFAULT now(),
  CHECK (decision NOT IN ('REJECT','REQUEST_CHANGES') OR comment IS NOT NULL)
);
CREATE TABLE response_actions (
  response_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id uuid NOT NULL REFERENCES alerts, action_id uuid REFERENCES recommended_actions,
  action_type text NOT NULL, assigned_to text,
  status text NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED','DISPATCHED','ON_SITE','COMPLETED','CANCELLED')),
  resource jsonb NOT NULL DEFAULT '{}'::jsonb, is_simulated boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE prediction_outcomes (
  outcome_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id uuid NOT NULL REFERENCES risk_predictions, zone_id text NOT NULL REFERENCES zones,
  observed_flooded boolean NOT NULL, observed_onset_at timestamptz, observed_peak_level_cm real,
  observed_flood_area_km2 real, lead_time_min real,
  label_source text NOT NULL CHECK (label_source IN ('SENSOR','SAR','REPORT','SIM_TRUTH','MANUAL')),
  outcome_confidence real, iou real, classification text CHECK (classification IN ('TP','FP','FN','TN')),
  evaluated_at timestamptz NOT NULL DEFAULT now(), UNIQUE (prediction_id, label_source)
);
CREATE TABLE feedback (
  feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id uuid REFERENCES alerts, outcome_id uuid REFERENCES prediction_outcomes, author_id uuid REFERENCES users,
  kind text NOT NULL CHECK (kind IN ('FALSE_ALARM','MISSED_EVENT','USEFUL','LOCAL_KNOWLEDGE','ROUTE_BLOCKED','SHELTER_ISSUE','OTHER')),
  text text, geom geometry(Point,4326), applied boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE audit_logs (
  audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),
  actor_type text NOT NULL CHECK (actor_type IN ('USER','AGENT','SERVICE','SYSTEM')), actor_id text NOT NULL,
  action text NOT NULL, entity_type text NOT NULL, entity_id text, before jsonb, after jsonb,
  request_id text, prev_hash text, hash text NOT NULL            -- hash chain, written by the application
);
CREATE TABLE agent_runs (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), trigger text NOT NULL, zone_id text REFERENCES zones,
  started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
  status text NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING','DONE','ABSTAINED','FAILED')), state jsonb, error text
);
CREATE TABLE tool_calls (
  call_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), run_id uuid NOT NULL REFERENCES agent_runs ON DELETE CASCADE,
  agent text NOT NULL, tool text NOT NULL, input jsonb, output_hash text, latency_ms int,
  ok boolean NOT NULL DEFAULT true, error text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE kb_chunks (
  chunk_id text PRIMARY KEY, doc text NOT NULL, section text, body text NOT NULL,
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', body)) STORED
);
CREATE TABLE scenarios (
  scenario_id text PRIMARY KEY, name text NOT NULL, definition jsonb NOT NULL,
  seed int NOT NULL DEFAULT 42, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE sim_state (
  id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  mode text NOT NULL DEFAULT 'replay' CHECK (mode IN ('replay','backtest','live')),
  scenario_id text REFERENCES scenarios, sim_now timestamptz, speed real NOT NULL DEFAULT 1,
  running boolean NOT NULL DEFAULT false, updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO sim_state DEFAULT VALUES;
```

### 7.4 Triggers, immutability and indexes

```sql
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['zones','grid_cells','drainage_nodes','drainage_edges','roads','buildings',
                           'critical_facilities','shelters','stations','water_level_sensors','flood_extents'] LOOP
    EXECUTE format('CREATE TRIGGER trg_%s_utm BEFORE INSERT OR UPDATE OF geom ON %I FOR EACH ROW EXECUTE FUNCTION set_geom_utm()', t, t);
  END LOOP;
END $$;

CREATE OR REPLACE FUNCTION audit_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs is append-only';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_audit_immutable BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION audit_immutable();

-- GiST index on every geometry column
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT table_name, column_name FROM information_schema.columns
           WHERE table_schema = 'public' AND udt_name = 'geometry' LOOP
    EXECUTE format('CREATE INDEX IF NOT EXISTS gix_%s_%s ON %I USING GIST (%I)', r.table_name, r.column_name, r.table_name, r.column_name);
  END LOOP;
END $$;

CREATE INDEX ix_rain_time     ON rainfall_observations (observed_at DESC);
CREATE INDEX ix_forecast_valid ON rainfall_forecasts (valid_at);
CREATE INDEX ix_wlo_time      ON water_level_observations (observed_at DESC);
CREATE INDEX ix_sensor_zone   ON water_level_sensors (zone_id);
CREATE INDEX ix_grid_zone     ON grid_cells (zone_id);
CREATE INDEX ix_roads_zone    ON roads (zone_id);
CREATE INDEX ix_bldg_cell     ON buildings (cell_id);
CREATE INDEX ix_pred_zone_time ON risk_predictions (zone_id, issued_at DESC);
CREATE INDEX ix_factor_pred   ON risk_factors (prediction_id);
CREATE INDEX ix_evidence_pred ON evidence (prediction_id);
CREATE INDEX ix_alert_status  ON alerts (status, created_at DESC);
CREATE INDEX ix_alert_zone    ON alerts (zone_id, created_at DESC);
CREATE INDEX ix_outcome_pred  ON prediction_outcomes (prediction_id);
CREATE INDEX ix_audit_entity  ON audit_logs (entity_type, entity_id, ts DESC);
CREATE INDEX ix_kb_tsv        ON kb_chunks USING GIN (tsv);
```

Volume check: 50 sensors at one reading per minute is about 72,000 rows per day; the composite primary key plus ix\_wlo\_time are sufficient. If real telemetry later multiplies this, convert water\_level\_observations and rainfall\_observations to TimescaleDB hypertables on observed\_at without changing the application.

## 8. Geospatial Architecture

### 8.1 Coordinate reference systems

| CRS | Use | Rule |
| --- | --- | --- |
| EPSG:4326 (WGS 84) | Storage, GeoJSON, API payloads | Column name geom. Never measure distance or area in it |
| EPSG:32644 (WGS 84 / UTM zone 44N) | All distances, areas, buffers, raster analysis | Chennai (about 80.3 E) lies inside zone 44 (78 to 84 E); scale error is far below 0.1 percent |
| EPSG:3857 | Display tiles in MapLibre only | Never used for analysis |

Rules: (1) every file read asserts crs is not None and fails fast; (2) call to\_crs(32644) before buffer, area, length, nearest or overlay; (3) in PostGIS use geom\_utm, or cast to geography for ST\_DWithin in metres; (4) a mixed-SRID error is a bug and is never silenced with ST\_SetSRID; (5) all rasters are resampled onto one 30 m UTM grid with a stored origin; (6) a CI test per layer asserts SRID and bounds.

### 8.2 Spatial units and aggregation

- Ward (table zones) is the reporting and alert unit. The 250 m cell (grid\_cells) is the modelling unit. Native layers keep native resolution and are aggregated to cells by zonal statistics: mean, minimum and 10th percentile for elevation; sum for population; count and area for buildings; length for roads and drains.
- Cells are assigned to wards by centroid. Boundary effects are accepted for the MVP and listed in docs/LIMITATIONS.md.
- Ward values combine cell values with both an average and a tail statistic (for example the 90th percentile of susceptibility and the share of area with HAND below 1 m), so large wards do not average away a flood-prone pocket.

### 8.3 Terrain and hydrology pipeline (scripts/build\_terrain.py)

1. Mosaic DEM tiles, clip to AOI plus 10 km, reproject to EPSG:32644 at 30 m with bilinear resampling, fill voids.
2. Fill pits and depressions with pysheds. Sink depth equals filled DEM minus original DEM (metres, zero or more).
3. Rasterise drains, canals, rivers and permanent water (JRC occurrence above 80 percent) into a stream mask.
4. HAND-approx: for every cell, elevation minus the elevation of the nearest stream cell (Euclidean nearest through a distance transform). Negative values mean the cell sits below the nearest channel and are kept, clipped at -2 m.
5. Slope from the filled DEM; flow direction, flow accumulation and TWI from pysheds after flat resolution.
6. Zonal statistics to cells with rasterstats; write terrain\_features and a sidecar JSON.

Flat-terrain warning: Chennai's relief is a few metres, comparable to DEM error. Flow direction, accumulation and TWI are therefore secondary features, flagged low-reliability. Sink depth and HAND-approx are the primary terrain indices. Both are relative indices and are never shown as flood depth.

### 8.4 Core workflows (representative code)

```python
import geopandas as gpd, numpy as np, pandas as pd
from shapely.geometry import box
from scipy import ndimage as ndi

UTM = 32644

def build_grid(wards_utm: gpd.GeoDataFrame, size: float = 250.0) -> gpd.GeoDataFrame:
    minx, miny, maxx, maxy = wards_utm.total_bounds
    x0, y0 = np.floor(minx / size) * size, np.floor(miny / size) * size
    xs, ys = np.arange(x0, maxx, size), np.arange(y0, maxy, size)
    cells = gpd.GeoDataFrame(
        {'cell_id': [f'G250_{int((x - x0) // size)}_{int((y - y0) // size)}' for x in xs for y in ys]},
        geometry=[box(x, y, x + size, y + size) for x in xs for y in ys], crs=wards_utm.crs)
    cents = cells.copy()
    cents['geometry'] = cells.geometry.centroid
    j = gpd.sjoin(cents, wards_utm[['zone_id', 'geometry']], how='inner', predicate='within')
    return cells.merge(j[['cell_id', 'zone_id']], on='cell_id', how='inner')

def hand_approx(dem: np.ndarray, stream_mask: np.ndarray) -> np.ndarray:
    # distance_transform_edt measures distance to the nearest zero, so invert the mask
    _, (iy, ix) = ndi.distance_transform_edt(~stream_mask, return_indices=True)
    return np.clip(dem - dem[iy, ix], -2.0, 30.0)

def drain_features(cells: gpd.GeoDataFrame, drains: gpd.GeoDataFrame) -> pd.DataFrame:
    assert cells.crs.to_epsg() == UTM and drains.crs.to_epsg() == UTM
    near = gpd.sjoin_nearest(cells[['cell_id', 'geometry']], drains[['geometry']],
                             how='left', distance_col='dist_drain_m')
    near = near.drop_duplicates('cell_id')[['cell_id', 'dist_drain_m']]
    pieces = gpd.overlay(drains[['geometry']], cells[['cell_id', 'geometry']], how='intersection')
    km = (pieces.length / 1000.0).groupby(pieces['cell_id']).sum().rename('drain_km').reset_index()
    out = near.merge(km, on='cell_id', how='left').fillna({'drain_km': 0.0})
    area_km2 = cells.set_index('cell_id').geometry.area / 1e6
    out['drain_density_km_km2'] = out['drain_km'] / out['cell_id'].map(area_km2)
    return out
```

Sink depth with pysheds (check method names against the pinned version):

```python
from pysheds.grid import Grid
grid = Grid.from_raster('data/processed/dem_utm44_30m.tif')
dem = grid.read_raster('data/processed/dem_utm44_30m.tif')
filled = grid.fill_depressions(grid.fill_pits(dem))
sink_depth = filled - dem            # metres, zero or more
```

PostGIS: population at risk per ward, and nearest flood-safe shelters (KNN on the UTM index):

```sql
SELECT c.zone_id,
       SUM(p.pop_total * COALESCE(t.susceptibility, 0)) AS pop_at_risk,
       SUM(p.pop_total) AS pop_total
FROM grid_cells c
JOIN terrain_features t ON t.cell_id = c.cell_id
JOIN population_grids p ON p.cell_id = c.cell_id AND p.year = :year
GROUP BY c.zone_id;

SELECT shelter_id, name, capacity, capacity_known,
       ST_Distance(geom_utm, ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32644)) AS straight_m
FROM shelters
WHERE flood_safety >= 0.7
ORDER BY geom_utm <-> ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 32644)
LIMIT 8;
```

### 8.5 Geospatial tests

- CRS: every loaded layer has the expected SRID and lies inside the Chennai bounding box.
- Assignment: every cell has exactly one ward; ward count is 200; no cell centroid falls outside the GCC boundary.
- Conservation: population summed over cells equals the raster total within 0.5 percent after clipping; building counts equal the source count inside the AOI.
- Intersections: drain length per cell summed over cells equals the total drain length inside the boundary within 0.1 percent.
- Routes: every stored route geometry starts at the origin and ends at the shelter within 50 m and uses only graph edges.

## 9. Data Ingestion

### 9.1 Pipeline

| Stage | Responsibility | Module |
| --- | --- | --- |
| Connector | Fetch with timeout, retry and cache | ewf.ingestion.adapters |
| Validation | Schema, range, timestamp, duplicate checks | ewf.ingestion.validators |
| Normalisation | Units (mm, mm/hr, cm), UTC, ids | adapter normalise functions |
| Spatial transformation | Station or sensor to ward and cell; CRS | ewf.geo |
| Feature engineering | Windows, rates, percentiles | ewf.features |
| Storage | Idempotent upsert, provenance, dead letter | ewf.db.repositories |
| Model input | Feature rows for M2 and M3 | ewf.features.builder |

### 9.2 Rules common to every ingestion path

| Topic | Rule |
| --- | --- |
| Timestamps | Must be timezone-aware ISO 8601. Naive values are rejected unless the adapter config declares source\_tz. Everything is converted to UTC at the boundary. Readings more than 120 s in the future are rejected. If received\_at minus observed\_at exceeds 10 min the reading is flagged SUSPECT |
| Missing values | Never fabricated. A missing reading produces no row. Stored data is never interpolated; the feature builder may bridge gaps of up to 3 minutes (sensors) or one interval (rainfall) and records the filled fraction as a data-quality input |
| Duplicates | Idempotent insert on the natural key (sensor\_id, observed\_at) or (station\_id, observed\_at, interval\_minutes); first write wins. A duplicate with a materially different value goes to rejected\_records with reason DUPLICATE\_CONFLICT |
| Outliers | Range, rate-of-change, Hampel spike and stuck-sensor checks (§9.4). Outliers are stored with quality\_flag SUSPECT or BAD and excluded from features |
| Errors | Per-record failures go to rejected\_records with a reason code. ingestion\_runs.status is PARTIAL if any record was rejected. Batch endpoints return 202 with counts; 422 for a malformed batch; 413 for an oversized batch |
| Provenance | Every run writes ingestion\_runs; every stored row carries source and run\_id where the table has them |

### 9.3 Contract per source

| Endpoint or adapter | Input | Validation | Output | Error handling |
| --- | --- | --- | --- | --- |
| POST /api/v1/data/rainfall | source, records\[\] of station\_id, observed\_at, interval\_minutes, rain\_mm (at most 5,000) | Station exists; interval in 5, 10, 15, 30, 60, 1440; 0 to 400 mm per interval; tz-aware | 202 with accepted, rejected, run\_id | 422 malformed; 413 too large; 401 or 403 role |
| POST /api/v1/data/water-level | readings\[\] of sensor\_id, timestamp, water\_level\_cm, battery\_percent, signal\_dbm, status (at most 2,000) | Sensor registered; rules in §9.4 | 202 with counts and a quality-flag histogram | Unknown sensor goes to rejected\_records as UNKNOWN\_SENSOR |
| Open-Meteo forecast adapter | Latitude and longitude of AOI centroids | Hourly arrays of equal length; values non-negative | rainfall\_forecasts rows (valid\_at is the end of the hour) | Retry 3 times with 1, 2, 4 s back-off, then cached forecast up to 6 h old flagged stale, else no forecast and reduced confidence |
| IMERG adapter | Earthdata credentials, bounding box, time range | Fill value to missing; 0 to 300 mm/hr | rainfall\_observations (GRID\_IMERG, 30 min) | Authentication or latency failure switches to the rainfall fallback chain: gauge, IMERG, Open-Meteo recent hours, none (abstain) |
| IMD gridded loader | Yearly GRD files | -999 to NULL; 0 to 1000 mm/day | Daily rows (GRID\_IMD) | Corrupt file aborts that year only |
| Static loaders (wards, drains, DEM, buildings, shelters, labels) | Files or ArcGIS REST | CRS present; geometry valid; row counts against expectations | Tables plus a per-ward coverage report | Whole load is one transaction; any failure rolls it back |

### 9.4 Sensor validation algorithm

1. Range: 0 up to 1.2 times drain\_depth\_cm, otherwise BAD.
2. Rate of change: absolute change per minute above 10 cm/min (config) is SUSPECT.
3. Spike (Hampel): compare with the median of the last 7 readings; if the deviation exceeds 4 times the larger of the scaled MAD and 0.5 cm, mark SUSPECT.
4. Stuck: identical value for 15 or more consecutive readings while sensors within 1.5 km vary by more than 2 cm marks SUSPECT.
5. sensor\_confidence is the product of: freshness exp(-age\_min / 10); battery factor (1 at 20 percent or above, otherwise battery/20); quality factor (OK 1, SUSPECT 0.5, BAD 0); signal factor (1 above -100 dBm, otherwise 0.7).

### 9.5 Simulated IoT sensor system

Purpose: GCC does not publish dense live drain telemetry, so the platform receives a simulated stream through the same contract a real gateway would use. Everything simulated is labelled: id prefix SIM-, is\_simulated true in every row, an on-screen SIM badge, and a notice in exported reports. It is a prototype simulation, not a hydraulic model and not calibrated to Chennai drains.

Sensor message (illustrative coordinates):

```json
{
  "sensor_id": "SIM-SWD-W112-004",
  "drain_id": "SWD-0001234",
  "timestamp": "2026-10-09T09:30:00+00:00",
  "latitude": 13.0405,
  "longitude": 80.2337,
  "water_level_cm": 45.2,
  "rise_rate_cm_min": 1.8,
  "battery_percent": 88,
  "signal_dbm": -92,
  "status": "ONLINE",
  "is_simulated": true
}
```

Placement strategy (scripts/place\_sensors.py):

1. Candidates are drainage edges inside AOI wards. Weight = cell susceptibility times (1 plus historical frequency).
2. Guarantee at least 4 sensors in the hero ward and at least 2 in every other AOI ward.
3. Add sensors by weighted farthest-point sampling with a 400 m minimum separation until the configured count (default 50, minimum 30).
4. Snap each to the nearest drain geometry. Default drain depth 120 cm, varied by plus or minus 30 percent; warn at 0.60 times depth, critical at 0.85 times depth (PROTOTYPE values).

Behaviour model (linear reservoir with lag; parameters derived per sensor from geospatial attributes):

```text
r_eff[t+1] = r_eff[t] + (dt / tau) * (rain[t] - r_eff[t])            # lagged effective rain, mm/hr
inflow     = alpha * r_eff[t]                                        # cm/min
outflow    = beta * (1 - blockage) * max(h[t] - h0, 0)               # cm/min
h[t+1]     = clip(h[t] + dt * (inflow - outflow), 0, 1.15 * depth)
reading    = h[t+1] + kappa * tide_cm + noise                        # kappa = 0 for inland wards
alpha      = alpha0 * (imperv / 0.8) * (catchment_ha / 5.0)
overtopping = h[t+1] >= depth                                        # used only for simulated truth
```

Starting values (PROTOTYPE, tune in roadmap phase 6): alpha0 0.055 cm/min per mm/hr (tuned in §37.1), beta 0.015 per min, tau 20 min (range 10 to 40), h0 5 cm (range 3 to 10), blockage drawn from Beta(2, 8) per sensor, noise 0.4 cm with 0.1 cm quantisation. Tune so that the hero-ward median sensor crosses warn at about T+25 to 30 min and critical at about T+40 to 45 min under DEMO-STORM-01, with a peak rise of about 3 cm/min. Do not tune further to make the models look better.

Fault injection (all scheduled by the scenario file, seeded):

| Fault | Behaviour | Detected by |
| --- | --- | --- |
| Packet loss | Bernoulli 2 percent plus short bursts | Missing rows; sensor availability metric |
| Comms outage | A ward cluster silent for 5 to 15 min | Staleness; sensor\_confidence falls |
| Stuck value | Repeats last value for 20 readings | Stuck rule |
| Spike | One reading at 5 to 15 times noise, or 2 times depth | Hampel and range rules |
| Drift | Plus 0.02 cm/min after an onset time | Neighbour comparison; shown in drift analysis |
| Battery | Decays 0.03 percent per hour; below 15 percent the interval doubles; below 5 percent offline | Battery factor |
| Clock skew and duplicates | Skew of 0 to 120 s on a few sensors; 0.5 percent resent packets | Timestamp rules; duplicate rule |

Simulation clock: every time-dependent component calls Clock.now(). SimClock(t0, speed) advances simulated time at the configured speed (default one simulated minute per real second). The simulator posts one batch per simulated minute to /api/v1/data/water-level using a system\_service token; the worker triggers ward assessments every 5 simulated minutes.

Simulated truth and independence: ground truth for outcomes is injected at the scenario's flood time as a SIM\_TRUTH extent derived from the historical observed extent (2015 or 2023 labels) inside the hero AOI, never from the model's own susceptibility surface. A ward counts as flooded in simulation when at least 30 percent of its sensors (minimum 2) stay overtopped for 3 consecutive minutes. Report whatever IoU results; do not adjust the scenario to improve it.

Replacement path: real sensors publish the same message to the same endpoint (or to MQTT with an MQTT-to-HTTP bridge); sensor\_type changes from SIMULATED to a hardware type and is\_simulated becomes false. No model or agent code changes.

## 10. Feature Engineering

### 10.1 Principles

- A feature is a pure function of data with timestamps at or before an as\_of time. The same code runs in training, backtests and serving.
- Features are versioned (feature\_version). Every feature has a name, unit, window, source and missing-data policy.
- Missing stays missing (NaN). LightGBM handles NaN natively; the hazard function imputes a neutral value and records the gap, which lowers confidence.

### 10.2 Feature catalogue

| Group | Feature | Definition | Unit | Missing policy |
| --- | --- | --- | --- | --- |
| Rainfall | rain\_15, rain\_30, rain\_60, rain\_180 | Accumulation over (as\_of minus window, as\_of\] from the ward's primary source | mm | NaN if coverage is under 80 percent of the window |
| Rainfall | rain\_int\_now, rain\_int\_max\_60, rain\_hr\_eq | Latest interval intensity; maximum intensity in the last 60 min; rain\_hr\_eq is the larger of rain\_60 and 4 x rain\_15 (hourly-equivalent rate) | mm/hr | NaN |
| Rainfall | rain\_ante\_24h, rain\_ante\_72h | Accumulation before the last 60 min | mm | NaN |
| Rainfall | rain\_trend | Least-squares slope of intensity over the last 60 min | mm/hr per 30 min | NaN if under 3 points |
| Forecast | rain\_fcst\_30, 60, 120, 6h | Forecast accumulation after as\_of from the latest forecast issued at or before as\_of | mm | NaN plus fcst\_missing flag |
| Water level | level\_cm, util | Latest valid reading; level divided by critical\_cm | cm, ratio | NaN if older than 10 min |
| Water level | level\_lag\_5, 10, 15, 30 | Reading at as\_of minus lag, nearest within 1.5 min | cm | NaN |
| Water level | rise\_5, rise\_10 | Theil-Sen slope over the last 5 and 10 min, at least 4 valid points | cm/min | NaN |
| Water level | rise\_accel | rise\_5 minus rise\_10 shifted by 5 min | cm/min per 5 min | NaN |
| Water level | tt\_critical\_lin | (critical\_cm minus level) / max(rise\_10, 0.05), capped at 240 | min | 240 when rise is under 0.05 |
| Ward aggregate | util\_max, util\_p75, rise\_max, frac\_above\_warn, n\_healthy, sensor\_conf\_mean | Over healthy sensors in the ward and neighbours within 1.5 km | mixed | n\_healthy of 0 sets sensor\_missing |
| Tide | tide\_cm | Latest context series value | cm | 0 plus tide\_missing for inland wards |
| Static (ward) | s\_mean, s\_p90, elev\_p10, hand\_p10, pct\_hand\_lt\_1m, sink\_max, drain\_density, imperv, hist\_freq, is\_coastal | From zone\_static\_features at the stated feature\_version | various | Never missing; a failed build blocks the run |

### 10.3 Windowing and leakage rules

- Windows are right-closed: (as\_of minus w, as\_of\]. A rainfall interval is usable only if its end is at or before as\_of; a forecast only if issued\_at is at or before as\_of.
- Every builder asserts max(timestamp) is at or before as\_of and raises LeakageError otherwise.
- Training samples are generated by looping as\_of over each scenario; the target at as\_of plus h is never visible to the features.
- Label vintage: when backtesting event E, hist\_freq and M1 are rebuilt without E and without any later event.
- Splits are by scenario or event, never by random row. M1 uses spatial block cross-validation (2 km blocks) plus leave-one-event-out.

## 11. Forecasting Engine

### 11.1 Four separate problems

| Layer | Question | Method | Output | Honest status in the MVP |
| --- | --- | --- | --- | --- |
| A Rainfall outlook | How much rain in the next 1 to 48 h? | Forecast feed plus trend extrapolation, no ML | Accumulation outlook per ward | Real feeds, coarse resolution |
| B Water-level forecast | Where will drain levels be in 15 to 120 min? | M2 LightGBM | Level, P10 and P90, exceedance probability, time to impact | Demonstrated on synthetic data |
| C Flood probability | How likely is flooding in this ward within the horizon? | M3 hazard function | H | Calibrated expert prior |
| D Flood risk and extent | Which wards, which areas? | Risk engine plus indicative footprint | Level, footprint | Indicative only |

### 11.2 Rainfall outlook (A)

Ingest hourly forecasts (Open-Meteo primary; ECMWF open data optional) and IMERG 30-minute observations. The outlook is the forecast accumulation for the next 60 and 120 min, 6 h and 24 h plus the recent trend. In replay mode the scenario supplies a forecast curve with configured error (bias factor and timing shift) so forecast error is part of the demonstration. No claim of 15-minute rainfall nowcasting is made: that needs radar QPE, which is not available. Optical-flow extrapolation (OpenCV Dual TV-L1) of consecutive IMERG fields is an optional experiment only; at about 11 km grid spacing it cannot resolve a ward.

### 11.3 Water-level forecasting (B)

| Candidate | Role | Verdict |
| --- | --- | --- |
| Persistence (level stays) | Skill baseline | Mandatory baseline |
| Linear-rate extrapolation (level plus rise times h, capped at depth) | Physical baseline | Mandatory baseline |
| Moving average, ridge regression on lags | Linear baseline | Baseline |
| Random Forest | Non-linear benchmark | Offline comparison only |
| LightGBM direct multi-horizon with P10 and P90 | Production model | SELECTED (MVP advanced model) |
| XGBoost | Equivalent to LightGBM | Not used; one library is enough |
| LSTM, GRU | Sequence benchmark | Offline notebook only. Promote only if it beats LightGBM by at least 10 percent MAE on held-out scenarios and real telemetry exists. Beating LightGBM on simulator data proves nothing |
| ConvLSTM, Transformer | Spatial or long-sequence models | Not applicable: no real gridded training data |

Design:

- Target: delta equals level(t+h) minus level(t) for h in 15, 30, 60, 120 min. Predicting the change makes persistence the zero forecast and the skill score meaningful. Three LightGBM models per horizon (median, 0.1 and 0.9 quantiles), 12 in total.
- Features: sensor lags, rise\_5, rise\_10, rise\_accel, rain accumulations and current intensity, forecast rain for the next 30 and 60 min, tide, and static sensor attributes (depth, imperviousness, catchment). Hidden simulator parameters (blockage, tau) are never features; the model must infer them from the response.
- Monotone constraints: forecast rain, current intensity and rise rates are non-decreasing in the predicted delta.
- Training data: 400 simulated scenarios (seeds 0 to 399) varying peak intensity 30 to 140 mm/hr, duration 30 to 240 min, single or double peak, onset time, forecast error, fault schedule and sensor parameter draws, plus replayed historical storms (IMERG-derived hyetographs for 2015, 2021, 2023) pushed through the simulator. Scenario-level split: 70 percent train, 15 percent validation, 15 percent test. DEMO-STORM-01 is excluded from all three sets.
- Exceedance probability: from the three quantile forecasts, approximate the predictive CDF with a piecewise-linear curve through (q10, 0.1), (q50, 0.5), (q90, 0.9) with tails extended by the half-width of the nearer side; check with a reliability diagram on test scenarios and apply isotonic correction if needed. Ward probability equals the mean of the two highest sensor probabilities, which resists a single bad sensor.
- Time to impact: smallest horizon whose ward exceedance probability reaches 0.5 (config). If none, report no impact within 120 min.
- Metrics: MAE, RMSE and R-squared on level; skill equals one minus MAE(model) over MAE(persistence); coverage of the P10 to P90 band (target about 80 percent); precision, recall, F1, PR-AUC and Brier score for critical-level exceedance; warning lead time. MAPE is not reported because levels near zero make it unstable. All numbers from simulated data carry the label synthetic-validation.

### 11.4 Flood probability calibration (C)

M3 outputs a probability from an expert-prior logistic function (§12.3). Calibration fits two parameters, an intercept shift b and a temperature T, by minimising log-loss of sigmoid((z minus b) / T) on ward-hour samples from backtests and simulated truth. Acceptance checks: monotone in every dynamic input, probability under 0.05 on a dry day for every ward, and a reliability diagram on events not used for fitting. If the checks fail, the priors are revised by people, not tuned silently.

## 12. Flood Risk Engine

### 12.1 Definitions

- H (hazard): calibrated probability of flood-impacting inundation in ward z within horizon h, given data at time t. It includes physical susceptibility (terrain, drainage, land use, history) through the M1 output S. Label definition: in simulation, a ward flooded per the §9.5 truth rule; in backtests, a ward overlapping an observed extent by at least 5 percent of its area or containing an incident point inside the event window. Labels are coarse and biased towards reported places, so recall is a lower bound and precision is uncertain.
- E (exposure): what is located in flood-prone parts of the ward, weighted by susceptibility.
- V (vulnerability): how badly the people and services there are affected: social and service fragility. Physical susceptibility is deliberately not repeated here, which avoids double counting.

### 12.2 Why the plain weighted sum is not enough

The proposal's Risk = 0.4H + 0.3E + 0.3V is kept as the explainable decomposition but not as the alert rule, for five reasons:

1. It is compensatory. A dense, low-lying ward on a dry day with H = 0.05, E = 0.9, V = 0.9 scores 0.4 x 0.05 + 0.3 x 0.9 + 0.3 x 0.9 = 0.56, a mid-range score with no rain at all. An early-warning system must not warn on a dry day.
2. It mixes a probability with consequences, so the output can be neither calibrated nor interpreted as a likelihood.
3. It double counts susceptibility when terrain and drainage appear in both hazard and vulnerability.
4. The slides' own numbers do not reconcile (0.775 against 0.82), and 0.82 is read both as a score and as an 82 percent probability.
5. The weights are unvalidated, so any single set is arbitrary; sensitivity must be tested (§32).

### 12.3 Final formulation (all weights and edges are PROTOTYPE values in config/risk.yaml)

Hazard function. z = b0 + sum(w\_j x f\_j); H = sigmoid((z minus b) / T) with b0 = -7.5, b = 0 and T = 1 until calibrated.

| ID | Feature | Scaling | Weight | Driver group |
| --- | --- | --- | --- | --- |
| f1 | rain\_hr\_eq | clip(rain\_hr\_eq / 50, 0, 1.5), where rain\_hr\_eq = max(rain\_60, 4 x rain\_15) | 1.6 | Extreme rainfall |
| f2 | rain\_fcst\_60 | clip(rain\_fcst\_60 / 50, 0, 1.5) | 0.8 | Extreme rainfall |
| f3 | rain\_ante\_24h | clip(rain\_ante\_24h / 100, 0, 1.5) | 0.6 | Extreme rainfall |
| f4 | util\_max | clip(util\_max, 0, 1.2) | 1.4 | Drainage stress |
| f5 | rise\_max | clip(rise\_max / 2.0, 0, 1.5) | 1.2 | Rapid water-level rise |
| f6 | exceed\_60 (from M2) | probability, 0 to 1 | 1.4 | Rapid water-level rise |
| f7 | s\_p90 (from M1) | 0 to 1 | 1.0 | Terrain and susceptibility |
| f8 | low\_elev | 1 minus clip(hand\_p10 / 3, 0, 1) | 0.6 | Terrain and susceptibility |
| f9 | hist\_freq | 0 to 1 | 0.6 | History and land use |
| f10 | imperv | 0 to 1 | 0.4 | History and land use |
| f11 | tide | clip(tide\_cm / 100, 0, 1), coastal wards only | 0.5 | Tide |

Sensor-loss variant (rain\_static): when sensor features are unavailable, use weights f1 2.4, f2 1.2, f3 0.8, f7 1.0, f8 0.6, f9 0.6, f10 0.4, f11 0.5 with intercept -6.0, mark the result degraded and cap confidence at MEDIUM. Silently dropping sensor terms would lower H exactly when sensors fail, which is the unsafe direction. The mirror case has its own variant: when rainfall is unavailable, sensor\_static uses weights util\_max 2.0, rise\_max 1.6, exceed\_60 1.8, s\_p90 1.0, low\_elev 0.6, hist\_freq 0.6 and imperv 0.4 with intercept -5.0, and is also marked degraded with confidence capped at MEDIUM.

Exposure. E = 0.40 x P(pop\_at\_risk) + 0.15 x P(bldg\_at\_risk) + 0.15 x P(road\_km\_at\_risk) + 0.30 x P(crit\_at\_risk), where each at\_risk quantity is a sum over cells weighted by susceptibility S, P(.) is the percentile rank across all wards (robust to outliers), and critical facilities are weighted hospital 5, power and water 4, school 3, fire and police 3, shelter 2, counted where S is at least 0.5.

Vulnerability. V = 0.40 x P(sensitive\_pop\_share) + 0.25 x P(shelter\_gap) + 0.20 x P(egress\_exposure) + 0.15 x P(density), where sensitive\_pop\_share is the share under 5 or over 65 (WorldPop age structure), shelter\_gap is the distance to the nearest flood-safe shelter, egress\_exposure is the share of the ward's road length with high static susceptibility, and density is population per km2. Optional informal-settlement data would be added only if a verified source is found.

Impact and risk index. I = (0.5 x E + 0.5 x V). R = H x ((1 minus 0.6) + 0.6 x I), so R never exceeds H.

Risk level (matrix on H and I):

| Hazard band | I below 0.33 | I 0.33 to 0.66 | I at least 0.66 |
| --- | --- | --- | --- |
| H below 0.30 | LOW | LOW | LOW |
| H 0.30 to 0.60 | LOW | MEDIUM | MEDIUM |
| H 0.60 to 0.85 | MEDIUM | HIGH | HIGH |
| H at least 0.85 | HIGH | VERY\_HIGH | VERY\_HIGH |

The confidence gate (§17) is applied last: LOW confidence caps the level at MEDIUM and forces review; insufficient evidence yields the abstention outcome instead of a level. The map shows the level; R only orders wards within a level.

Worked example (arithmetic from default priors and illustrative inputs, not a measured result):

| Feature | Value | Weight | Contribution to z |
| --- | --- | --- | --- |
| rain\_hr\_eq | 92 mm/hr gives 1.50 | 1.6 | 2.40 |
| rain\_fcst\_60 | 50 mm gives 1.00 | 0.8 | 0.80 |
| rain\_ante\_24h | 55 mm gives 0.55 | 0.6 | 0.33 |
| util\_max | 0.95 | 1.4 | 1.33 |
| rise\_max | 1.8 cm/min gives 0.90 | 1.2 | 1.08 |
| exceed\_60 | 0.80 | 1.4 | 1.12 |
| s\_p90 | 0.72 | 1.0 | 0.72 |
| low\_elev | HAND p10 0.9 m gives 0.70 | 0.6 | 0.42 |
| hist\_freq | 3 of 5 events gives 0.60 | 0.6 | 0.36 |
| imperv | 0.80 | 0.4 | 0.32 |
| tide | inland, 0 | 0.5 | 0.00 |

Sum 8.88; z = -7.5 + 8.88 = 1.38; H = 0.80. With E = 0.75 and V = 0.70, I = 0.725 and R = 0.80 x (0.4 + 0.6 x 0.725) = 0.67. H is in the 0.60 to 0.85 band and I is at least 0.66, so the level is HIGH. The dry-day ward from §12.2 gives z = -7.5 + 1.82 = -5.68, H = 0.003 and level LOW, whatever E and V are.

Driver shares for the explanation use contributions relative to a reference (dynamic features at 0, static features at the city median, assumed here as S 0.30, low\_elev 0.35, hist 0.20, imperv 0.50): extreme rainfall 3.53, rapid water-level rise 2.20, drainage stress 1.33, terrain and susceptibility 0.63, history and land use 0.36, total 8.05, which is 44, 27, 17, 8 and 4 percent. The engine reports these as computed.

### 12.4 Flood extent: what the MVP predicts

| Option | Decision |
| --- | --- |
| A Flood probability per ward | Primary output (H) |
| D Zone risk level per ward | Primary output (level) |
| C Extent polygon | Provided as an indicative susceptibility footprint, labelled indicative |
| B Flood depth | Not predicted. Sensors give qualitative water state only |

A true hydraulic inundation model cannot be built, calibrated and validated in hackathon time, and drain capacities are unpublished. The hybrid approach is: ML risk (H) plus terrain and drainage constraints plus historical footprints.

Indicative footprint for a ward with H at least 0.5 (PROTOTYPE parameters):

1. Susceptibility cut-off tau(H) = 0.8 minus 0.5 x H (0.40 at H = 0.8).
2. Height cut-off h(H) = 0.5 + 2.5 x H metres of HAND-approx.
3. Footprint cells = cells with S at least tau and HAND at most h, plus cells with sink depth at least 0.3 m and S at least tau minus 0.1.
4. Constrain to the union of historical observed extents buffered by 150 m plus all sink cells, so the footprint cannot appear where flooding was never plausible.
5. Dissolve cells to polygons and store in flood\_extents with kind INDICATIVE\_PREDICTED. Store an inner and outer envelope using H minus 0.15 and H plus 0.15.

It is evaluated by IoU, precision and recall against observed history (§32). Expect modest values and report them as they are. It must never be described as a hydraulic simulation.

### 12.5 Versioning, sensitivity and interface

- risk.yaml is stored in config\_versions (sha256) and referenced by every prediction. Changing a weight creates a new config\_version; old predictions remain reproducible.
- Sensitivity: perturb every weight and edge by plus or minus 20 percent in a Monte Carlo run and report the Spearman rank correlation of ward order and the share of wards whose level changes. This is part of the evaluation report.
- Interface: RiskEngine.assess(features, static, confidence\_inputs) returns a RiskResult (§14). The function is pure, so it is property-tested for monotonicity.

## 13. Multi-Agent Architecture

### 13.1 Design rules

- Six agents and no others. Each is a typed Python class with a deterministic core; two of them have an optional LLM step.
- Agents never talk to each other directly. They read and write fields of one shared AssessState (§15) through the contracts in §14. The orchestrator owns order and routing.
- Anything numeric, spatial or safety-relevant is computed by tools: ordinary functions in ewf.models, ewf.risk, ewf.geo and ewf.routing. Agents call tools, log each call in tool\_calls and carry results forward.
- The LLM appears in three optional places only: the RCA narrative, decision rationale text, and Tamil or English drafting from reviewed templates. It never produces numbers, state changes, routes or policy outcomes.

### 13.2 Agent specifications

**Orchestrator Agent**

| Field | Specification |
| --- | --- |
| Purpose | Run the assess\_zone workflow, route on conditions, enforce guardrails, persist run state |
| Inputs | AgentRequest: trigger, zone\_id, as\_of, mode, horizon |
| Outputs | Final AssessState: RiskResult, Explanation, Recommendation, AlertDraft or an abstention, plus the run trace |
| Tools | LangGraph graph, repositories, policy engine, Clock |
| Memory | Per-run state only (agent\_runs.state). No cross-run memory; recent predictions are read from the database |
| Allowed | Call agents in order, retry, choose fallback branches, create DRAFT or PENDING\_REVIEW alerts through the alerts service |
| Forbidden | Producing numbers, calling dispatch, approving anything, editing thresholds, skipping the policy check |
| Failure handling | Per-node retry (maximum 2, back-off 1 s then 2 s); a failed node marks the run degraded; an unrecoverable error marks the run FAILED with an audit entry. Idempotency key (zone\_id, as\_of bucket, inputs\_hash) prevents duplicate predictions and alerts |
| Insufficient evidence | Routes to the abstain node |
| Abstention | Any condition in §17.4 |
| Confidence | Passes it through; LOW forces mandatory review |

**Data & Retrieval Agent**

| Field | Specification |
| --- | --- |
| Purpose | Assemble a validated, time-consistent evidence package for one ward at one time |
| Inputs | zone\_id, as\_of |
| Outputs | DataPackage: features, static features, freshness, missing list, fallbacks used, data\_quality, sensor\_confidence, evidence rows |
| Tools | get\_feature\_package, get\_rain\_series, get\_sensor\_series, get\_static\_features, find\_similar\_events, search\_kb |
| Memory | None (stateless) |
| Allowed | Read the database; call ingestion adapters (cached); flag gaps; apply the documented fallback chain |
| Forbidden | Fabricating or silently imputing values; using data later than as\_of; writing predictions |
| Failure handling | Adapter failure leads to the fallback chain: gauge, IMERG, Open-Meteo recent hours, none. Cached data is marked stale |
| Insufficient evidence | Returns abstain\_recommended true with reasons |
| Abstention | No rainfall source and no healthy sensors; static features missing |
| Confidence | Computes data\_quality and sensor\_confidence |

**Forecasting Agent**

| Field | Specification |
| --- | --- |
| Purpose | Run M2 water-level forecasts and assemble the rainfall outlook |
| Inputs | DataPackage |
| Outputs | ForecastResult: per-horizon P10, P50, P90, exceedance probability, time to impact, rainfall outlook, model version, confidence |
| Tools | forecast\_water\_level, exceedance\_and\_tti, baseline models |
| Memory | None |
| Allowed | Run registered models; fall back to persistence and linear-rate baselines |
| Forbidden | Changing model weights; forecasting beyond 120 min; emitting a forecast without input timestamps |
| Failure handling | Model load failure leads to the baseline model with degraded true |
| Insufficient evidence | No fresh sensors: rainfall-only outlook with available false for water level |
| Abstention | None by itself; reports availability |
| Confidence | c\_forecast from interval width and agreement with the baseline |

**Flood Risk Analysis Agent**

| Field | Specification |
| --- | --- |
| Purpose | Compute H, E, V, I, R, level and the indicative footprint |
| Inputs | DataPackage, ForecastResult |
| Outputs | RiskResult including factors and evidence ids |
| Tools | compute\_hazard, assess\_risk, build\_footprint |
| Memory | None |
| Allowed | Deterministic computation only |
| Forbidden | LLM calls; changing configuration; creating alerts |
| Failure handling | Invalid configuration fails the run (it cannot degrade safely) |
| Insufficient evidence | Uses the rain\_static variant if sensors are unavailable (degraded); abstains if rainfall is also unavailable |
| Abstention | Conditions in §17.4 |
| Confidence | Composes the overall confidence (§17) |

**RCA & Explanation Agent**

| Field | Specification |
| --- | --- |
| Purpose | Explain why: rank drivers, bind evidence, find similar events, write the explanation |
| Inputs | RiskResult, DataPackage, ForecastResult |
| Outputs | Explanation: drivers with evidence ids, similar events, limitations, text in English and optionally Tamil, verification report |
| Tools | explain\_risk, find\_similar\_events, search\_kb, render\_template, verify\_text, optional LLM adapter |
| Memory | None |
| Allowed | Verbalise computed facts; compare with history; state what is unknown |
| Forbidden | Inventing causes, numbers or events; claiming certainty above the stated confidence; citing evidence ids that do not exist |
| Failure handling | LLM failure or guard rejection leads to template text with mode template |
| Insufficient evidence | States limitations and lists missing inputs |
| Abstention | No explanation for an abstained risk, only the reason |
| Confidence | Copies RiskResult confidence and adds the verification result |

**Decision & Recommendation Agent**

| Field | Specification |
| --- | --- |
| Purpose | Turn risk and explanation into actions, routes, shelters and a draft alert |
| Inputs | RiskResult, Explanation, policy configuration, shelters, routing graph |
| Outputs | Recommendation and AlertDraft |
| Tools | apply\_policy, rank\_shelters, compute\_routes, draft\_alert, render\_template |
| Memory | Reads active alerts for the ward to avoid duplicates and to handle escalation |
| Allowed | Propose; create an alert in PENDING\_REVIEW through the alerts service |
| Forbidden | Authorising evacuation, dispatching, editing official thresholds, sending anything to citizens, presenting itself as an order |
| Failure handling | Routing failure leads to straight-line shelters and static corridors marked unverified; policy engine failure leads to no alert and an operator banner |
| Insufficient evidence | Low confidence gives an advisory-level recommendation and an explicit review request |
| Abstention | Mirrors upstream abstention |
| Confidence | Carried into the draft as low\_confidence |

### 13.3 Tool registry

| Tool | Used by | Module |
| --- | --- | --- |
| get\_feature\_package(zone, as\_of) | Data | ewf.features.builder (enforces as\_of) |
| get\_rain\_series, get\_sensor\_series, get\_static\_features | Data, Risk | ewf.db.repositories (read-only) |
| find\_similar\_events(features) | Data, RCA | ewf.explain.similarity |
| search\_kb(query) | RCA, Decision | ewf.explain.kb (PostgreSQL full-text) |
| forecast\_water\_level(package) | Forecasting | ewf.models.forecast (M2 plus baselines) |
| exceedance\_and\_tti(quantiles) | Forecasting | ewf.models.forecast.exceed |
| compute\_hazard(features) | Risk | ewf.models.hazard (M3 and variants) |
| assess\_risk(...) | Risk | ewf.risk.engine |
| build\_footprint(zone, H) | Risk | ewf.geo.footprint |
| explain\_risk(...), verify\_text(...) | RCA | ewf.explain.drivers, ewf.explain.verifier |
| rank\_shelters(origin), compute\_routes(...) | Decision | ewf.routing |
| apply\_policy(risk, confidence) | Decision | ewf.decision.policy |
| draft\_alert(...), render\_template(...) | Decision | ewf.alerts.drafting, ewf.decision.i18n |

## 14. Agent Contracts

All cross-agent data uses these Pydantic v2 models (src/ewf/agents/contracts.py). Rules: extra fields are forbidden; models are frozen; all datetimes are timezone-aware; a RiskResult cannot exist without evidence and factors unless it is an abstention; AlertDraft.requires\_review is literally True; a rejection needs a comment.

```python
from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Level(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    VERY_HIGH = 'VERY_HIGH'


class ConfidenceLevel(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


class AgentRequest(Contract):
    request_id: UUID = Field(default_factory=uuid4)
    trigger: Literal['schedule', 'api', 'demo', 'backtest']
    zone_id: str
    as_of: AwareDatetime
    mode: Literal['replay', 'backtest', 'live'] = 'replay'
    horizon_minutes: int = Field(60, gt=0, le=120)
    requested_by: str = 'system'


class AgentResponse(Contract):
    request_id: UUID
    agent: str
    status: Literal['OK', 'DEGRADED', 'ABSTAIN', 'ERROR']
    started_at: AwareDatetime
    finished_at: AwareDatetime
    warnings: list[str] = []
    payload: dict[str, Any] = {}


class Evidence(Contract):
    evidence_id: UUID = Field(default_factory=uuid4)
    kind: Literal['RAIN_OBS', 'SENSOR_OBS', 'FORECAST', 'TERRAIN_STAT', 'DRAINAGE_STAT',
                  'HISTORICAL_EVENT', 'MODEL_OUTPUT', 'RULE', 'KB_CHUNK']
    ref_table: str | None = None
    ref_key: str | None = None
    observed_at: AwareDatetime | None = None
    payload: dict[str, Any]


class DataPackage(Contract):
    zone_id: str
    as_of: AwareDatetime
    features: dict[str, float | None]
    static: dict[str, float | None]
    freshness_min: dict[str, float] = {}
    missing: list[str] = []
    fallbacks_used: list[str] = []
    sensor_ids_used: list[str] = []
    data_quality: float = Field(ge=0, le=1)
    sensor_confidence: float = Field(ge=0, le=1)
    abstain_recommended: bool = False
    abstain_reasons: list[str] = []
    evidence: list[Evidence] = []


class HorizonForecast(Contract):
    horizon_minutes: Literal[15, 30, 60, 120]
    p10_cm: float
    p50_cm: float
    p90_cm: float
    exceed_prob: float = Field(ge=0, le=1)


class ForecastResult(Contract):
    zone_id: str
    as_of: AwareDatetime
    input_timestamp: AwareDatetime
    available: bool
    degraded: bool = False
    horizons: list[HorizonForecast] = []
    time_to_impact_min: int | None = None
    rain_outlook_mm: dict[str, float] = {}
    confidence: float = Field(ge=0, le=1)
    model_version_id: UUID | None = None


class RiskFactor(Contract):
    factor_key: str
    driver_group: str
    value: float | None = None
    unit: str | None = None
    contribution_pct: float = Field(ge=0, le=100)
    direction: Literal['INCREASES', 'DECREASES'] = 'INCREASES'
    impact_band: Literal['HIGH', 'MEDIUM', 'LOW']
    evidence_ids: list[UUID]


class RiskResult(Contract):
    prediction_id: UUID = Field(default_factory=uuid4)
    zone_id: str
    timestamp: AwareDatetime
    horizon_minutes: int
    status: Literal['OK', 'DEGRADED', 'INSUFFICIENT_EVIDENCE']
    probability: float | None = Field(None, ge=0, le=1)
    hazard_score: float | None = Field(None, ge=0, le=1)
    exposure_score: float | None = Field(None, ge=0, le=1)
    vulnerability_score: float | None = Field(None, ge=0, le=1)
    impact_index: float | None = None
    risk_index: float | None = None
    risk_level: Level | None = None
    time_to_impact_min: int | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    confidence_level: ConfidenceLevel | None = None
    confidence_components: dict[str, float] = {}
    key_factors: list[RiskFactor] = []
    evidence_ids: list[UUID] = []
    footprint_extent_id: UUID | None = None
    model_version_ids: list[UUID] = []
    config_version: str
    inputs_hash: str
    abstain_reasons: list[str] = []

    @model_validator(mode='after')
    def _consistency(self) -> 'RiskResult':
        if self.status == 'INSUFFICIENT_EVIDENCE':
            if not self.abstain_reasons:
                raise ValueError('abstention needs at least one reason')
            return self
        missing = [n for n in ('probability', 'risk_level', 'confidence') if getattr(self, n) is None]
        if missing:
            raise ValueError(f'missing fields for status {self.status}: {missing}')
        if not self.evidence_ids or not self.key_factors:
            raise ValueError('a risk result without evidence and factors is not allowed')
        return self


class Explanation(Contract):
    prediction_id: UUID
    mode: Literal['template', 'llm']
    text_en: str
    text_ta: str | None = None
    drivers: list[RiskFactor]
    similar_event_ids: list[str] = []
    limitations: list[str] = []
    verified: bool
    verification_report: dict[str, Any] = {}


class ShelterOption(Contract):
    shelter_id: str
    name: str
    capacity: int | None = None
    capacity_known: bool
    flood_safety: float = Field(ge=0, le=1)
    straight_line_m: float


class RouteOption(Contract):
    route_id: UUID
    shelter_id: str
    profile: Literal['walk', 'drive']
    distance_m: float
    duration_s: float
    safety_score: float = Field(ge=0, le=100)
    max_segment_risk: float = Field(ge=0, le=1)
    blocked_edges: int = 0
    geometry: dict[str, Any]            # GeoJSON LineString


class ActionItem(Contract):
    action_type: Literal['MONITOR', 'PREPARE', 'ISSUE_ALERT', 'OPEN_SHELTER', 'EVACUATION_ROUTE',
                         'DEPLOY_TEAM', 'NOTIFY_AUTHORITY', 'PRIORITISE_FACILITY', 'ALLOCATE_RESOURCE']
    priority: int = Field(ge=1, le=5)
    target: dict[str, Any] = {}
    rationale: str
    policy_rule_ids: list[str] = []
    requires_approval: bool = True


class Recommendation(Contract):
    prediction_id: UUID
    level: Level
    actions: list[ActionItem]
    routes: list[RouteOption] = []
    shelters: list[ShelterOption] = []
    notes: list[str] = []


class AlertDraft(Contract):
    alert_id: UUID = Field(default_factory=uuid4)
    prediction_id: UUID
    zone_id: str
    severity: Level
    headline: str
    body_en: str
    body_ta: str | None = None
    channels: list[Literal['DASHBOARD', 'SMS', 'APP', 'EMAIL', 'IVRS']]
    valid_until: AwareDatetime
    low_confidence: bool
    requires_review: Literal[True] = True
    is_simulated: bool = True
    payload: dict[str, Any]


class HumanReview(Contract):
    alert_id: UUID
    reviewer_id: UUID
    decision: Literal['APPROVE', 'MODIFY_APPROVE', 'REJECT', 'REQUEST_CHANGES']
    comment: str | None = None
    modifications: dict[str, Any] | None = None
    evidence_opened: bool
    acknowledged_low_confidence: bool = False
    decided_at: AwareDatetime

    @model_validator(mode='after')
    def _comment_rules(self) -> 'HumanReview':
        if self.decision in ('REJECT', 'REQUEST_CHANGES') and not self.comment:
            raise ValueError('a comment is required to reject or request changes')
        if self.decision == 'MODIFY_APPROVE' and not self.modifications:
            raise ValueError('MODIFY_APPROVE needs the modifications')
        return self


class OutcomeFeedback(Contract):
    prediction_id: UUID
    zone_id: str
    observed_flooded: bool
    label_source: Literal['SENSOR', 'SAR', 'REPORT', 'SIM_TRUTH', 'MANUAL']
    observed_onset_at: AwareDatetime | None = None
    observed_peak_level_cm: float | None = None
    observed_flood_area_km2: float | None = None
    outcome_confidence: float = Field(1.0, ge=0, le=1)
    notes: str | None = None
```

## 15. Orchestration

### 15.1 Workflow (assess\_zone)

| Node | Agent | Reads | Writes | Next |
| --- | --- | --- | --- | --- |
| fetch\_data | Data & Retrieval | request | data | abstain if abstain\_recommended, else forecast |
| forecast | Forecasting | data | forecast | assess\_risk |
| assess\_risk | Flood Risk Analysis | data, forecast | risk | abstain if INSUFFICIENT\_EVIDENCE; end if LOW; else explain |
| explain | RCA & Explanation | risk, data, forecast | explanation | decide |
| decide | Decision & Recommendation | risk, explanation | recommendation | policy\_check |
| policy\_check | Policy engine | recommendation, risk | recommendation (gated) | draft\_alert if an alert-class action survives, else end |
| draft\_alert | Alert service | recommendation, risk | alert (PENDING\_REVIEW) | end |
| abstain | Abstention recorder | risk or data | abstention record | end |

### 15.2 Conditional routing rules

- Insufficient rainfall data: the Data agent walks the fallback chain (gauge, IMERG, Open-Meteo recent hours). If every source is stale or absent it recommends abstention.
- Sensor failure: use healthy neighbours within 1.5 km; if none, switch the hazard function to the rain\_static variant, mark the result degraded and cap confidence at MEDIUM.
- Low model confidence: cap the level at MEDIUM, set low\_confidence on any draft and make review mandatory with an acknowledgement.
- Risk below threshold: level LOW ends the run with no alert. The prediction is still stored so that false negatives can be evaluated later.
- High risk with high confidence: draft a critical alert in PENDING\_REVIEW with routes and shelters.
- Critical action: every ISSUE\_ALERT, EVACUATION\_ROUTE, DEPLOY\_TEAM and NOTIFY\_AUTHORITY action has requires\_approval true; the policy engine rejects any draft that sets it to false.
- De-escalation: if an alert is ACTIVE and the level has been LOW for 3 consecutive ticks, propose RESOLVE for human approval.
- Duplicate suppression: if an equal-or-higher PENDING\_REVIEW or ACTIVE alert exists for the ward, update its evidence instead of creating another; a higher severity supersedes the older alert.

### 15.3 LangGraph implementation (src/ewf/agents/graph.py)

The routing logic lives in plain functions, so the same flow can run without LangGraph in tests (a tiny SequentialRunner calls the same node and router functions).

```python
import operator
from typing import Annotated, TypedDict
from langgraph.graph import END, START, StateGraph
from ewf.agents.contracts import (AgentRequest, AlertDraft, DataPackage, Explanation, ForecastResult,
                                  Level, Recommendation, RiskResult)


class AssessState(TypedDict, total=False):
    request: AgentRequest
    data: DataPackage
    forecast: ForecastResult
    risk: RiskResult
    explanation: Explanation
    recommendation: Recommendation
    alert: AlertDraft
    warnings: Annotated[list[str], operator.add]
    outcome: str                      # DRAFTED, NO_ALERT, ABSTAINED


def route_after_data(state: AssessState) -> str:
    return 'abstain' if state['data'].abstain_recommended else 'go'


def route_after_risk(state: AssessState) -> str:
    risk = state['risk']
    if risk.status == 'INSUFFICIENT_EVIDENCE':
        return 'abstain'
    if risk.risk_level == Level.LOW:
        return 'no_alert'
    return 'explain'


def route_after_policy(state: AssessState) -> str:
    alert_actions = ('ISSUE_ALERT', 'EVACUATION_ROUTE')
    return 'draft' if any(a.action_type in alert_actions for a in state['recommendation'].actions) else 'no_alert'


def build_assess_graph(agents):
    g = StateGraph(AssessState)
    g.add_node('fetch_data', agents.data.run)
    g.add_node('forecast', agents.forecasting.run)
    g.add_node('assess_risk', agents.risk.run)
    g.add_node('explain', agents.rca.run)
    g.add_node('decide', agents.decision.run)
    g.add_node('policy_check', agents.policy.run)
    g.add_node('draft_alert', agents.alerts.run)
    g.add_node('abstain', agents.abstain.run)
    g.add_edge(START, 'fetch_data')
    g.add_conditional_edges('fetch_data', route_after_data, {'go': 'forecast', 'abstain': 'abstain'})
    g.add_edge('forecast', 'assess_risk')
    g.add_conditional_edges('assess_risk', route_after_risk,
                            {'explain': 'explain', 'abstain': 'abstain', 'no_alert': END})
    g.add_edge('explain', 'decide')
    g.add_edge('decide', 'policy_check')
    g.add_conditional_edges('policy_check', route_after_policy, {'draft': 'draft_alert', 'no_alert': END})
    g.add_edge('draft_alert', END)
    g.add_edge('abstain', END)
    return g.compile()
```

Each agent exposes run(state) and returns only the keys it owns, for example {'data': package}. Check the node and conditional-edge signatures against the pinned LangGraph version.

### 15.4 Orchestrator wrapper, state and idempotency

- Orchestrator.assess(request) opens an agent\_runs row, invokes the graph with {'request': request, 'warnings': \[\]}, and records the final state (contracts dumped to JSON) and status DONE, ABSTAINED or FAILED. Exceptions are caught, logged, audited and re-raised to the scheduler.
- Context passing is by AssessState only. State is persisted at the end of every node into agent\_runs.state, so a failed run can be inspected; there is no checkpoint-resume in the MVP.
- Time budget: 30 s per ward and 60 s per tick. A ward that exceeds its budget is marked degraded and retried next tick.
- Idempotency: risk\_predictions is unique on (zone\_id, issued\_at, horizon\_minutes, inputs\_hash); alert creation applies the duplicate-suppression rule above.
- Every node is wrapped by a tracing decorator that writes a tool\_calls row (agent, tool, latency, ok) and increments metrics (§30).

### 15.5 Dispatch is not part of the graph

Approval, modification, rejection and dispatch are separate service calls from the review API (§18). The assessment graph ends at PENDING\_REVIEW. A second small function, dispatch\_alert(alert\_id, reviewer), re-checks that the alert is APPROVED by a permitted role, that it has not expired and that the prediction is still current, then writes simulated notifications. No agent holds a reference to it.

## 16. Explainability

### 16.1 The four questions

| Question | Answered by | Fields |
| --- | --- | --- |
| WHERE | Ward, indicative footprint, affected assets | zone\_id, footprint\_extent\_id, people, buildings, road km and facilities inside the footprint |
| WHEN | Time to impact, horizon, forecast band, trend | time\_to\_impact\_min, ForecastResult horizons, rainfall outlook |
| WHY | Ranked drivers with values, shares, evidence ids, similar past events | key\_factors, evidence, similar\_event\_ids |
| WHAT ACTION | Recommended actions, routes, shelters with policy rule ids | Recommendation |

### 16.2 Driver computation (deterministic)

- For the hazard function, contribution\_j = w\_j x (f\_j minus f\_ref\_j) in log-odds, where the reference is 0 for dynamic features and the city median for static features. Contributions are summed by driver group. Shares are normalised over positive contributions only, so they add to 100 percent. Negative contributions (for example good drainage) are listed separately as mitigating factors.
- impact\_band: HIGH at a share of 25 percent or more, MEDIUM from 10 to 25, LOW below 10 (PROTOTYPE).
- Drill-down (on demand): SHAP for the LightGBM models (shap.TreeExplainer): why a cell has a high susceptibility (M1) and why a sensor forecast rises (M2). It is a secondary view, not the headline explanation.

### 16.3 Evidence binding

Every driver points to Evidence rows created in the same run: RAIN\_OBS (the observation keys behind rain\_60), SENSOR\_OBS (sensor ids and timestamps), FORECAST (issue and valid keys), TERRAIN\_STAT and DRAINAGE\_STAT (the zone\_static\_features row and utilisation), HISTORICAL\_EVENT (event ids), MODEL\_OUTPUT (model version ids and outputs), RULE (policy rule ids), KB\_CHUNK (knowledge chunk ids). The payload holds the facts shown to users. The API will not return a risk without its evidence, and a test enforces it.

### 16.4 Similar historical events

Feature vector: peak rain\_60, rain\_180, rain\_ante\_24h, peak rise rate, tide. Standardise with event-table statistics and rank by Euclidean distance; similarity equals 1 / (1 + distance). Require at least two candidate events with vectors, show the top three with the event name, similarity, whether this ward was flooded in that event (label and source). With fewer than two candidates the explanation says no sufficiently similar documented event exists. Historical analogy is context, not proof.

### 16.5 Text generation

Template first. The deterministic template always works and is the fallback:

```text
{level_text}: {ward_name} (Ward {ward_no}). Estimated {prob_pct}% chance of flooding within about {tti} minutes (confidence {conf_level}).
Main reasons: {driver_1}; {driver_2}; {driver_3}. {history_sentence} {limitation_sentence}
```

Example output (illustrative): High flood risk: Ward 112. Estimated 80% chance of flooding within about 30 minutes (confidence High). Main reasons: extreme rainfall, 92 mm/hr (44% of the risk); rapid water-level rise, +18 cm in 10 min (27%); drain water level at 95% of the critical level (17%). This ward was flooded in 3 of 5 documented events. Water-level sensors are simulated.

Optional LLM mode. Input is structured JSON only (drivers, values, evidence ids, limitations, confidence, level, time to impact, history). Output must be JSON with text\_en and claims, each claim listing evidence ids. The verifier then checks:

1. Every number in the text matches an allowed value from the payload within rounding.
2. Every claim cites at least one evidence id that exists for this prediction.
3. No certainty phrases (will definitely, guaranteed, certain to). If confidence is not HIGH the text must carry the limitation sentence.
4. Only names present in the payload appear (ward, events, shelters); no other places, events or agencies.
5. At most 120 words.

On failure, retry once with the list of violations; on a second failure use the template. explanations.mode and explanations.verified record what happened. Tamil text comes from reviewed static templates filled by code with the same numbers. LLM Tamil is an optional stretch, marked unreviewed until a person confirms it, and an alert with unreviewed Tamil cannot be dispatched.

### 16.6 Evaluating explanations

Evidence completeness (every driver has at least one evidence id), factual consistency (verifier pass rate, zero numeric mismatches in tests), traceability (every number in the UI opens its evidence) and usefulness (operator rating from 1 to 5 stored in feedback). No target value is claimed in advance.

## 17. Uncertainty

### 17.1 Five different things

| Notion | Measures | Computed from | Used for |
| --- | --- | --- | --- |
| Data quality (c\_data) | Freshness and completeness of inputs | Age beyond expected latency; weighted share of required features present | Confidence, abstention |
| Sensor confidence (c\_sensor) | Trust in sensor readings | Quality flags, battery, signal, staleness, number of healthy sensors | Confidence, weighting of ward aggregates |
| Forecast uncertainty (c\_forecast) | Spread of M2 forecasts and agreement with the baseline | P10 to P90 width against the critical level; baseline disagreement | Confidence, time-to-impact caveat |
| Model confidence (c\_model) | Whether the model is inside its experience | Share of features outside the training 1st to 99th percentile; calibration status | Confidence |
| Prediction uncertainty (c\_pred) | Sensitivity of H to the prior weights | 200 draws with hazard weights perturbed by plus or minus 20 percent; 5th to 95th percentile of H | Confidence; displayed as a range |

### 17.2 Composition

- c\_data = F x C. F = exp(-max(0, age\_min minus expected\_latency\_min) / tau) with tau 30 min for rain and sensors and 120 min for forecasts, taking the minimum over required sources (expected latencies come from config: gauge 5 min, sensors 3 min, IMERG Early 240 min, forecast 180 min). C = weight of required features present divided by weight required.
- c\_sensor = (sum of w\_i x s\_i / sum of w\_i) x min(1, n\_healthy / 3), with w\_i equal to 1 for sensors inside the ward and 0.5 for neighbours within 1.5 km.
- c\_forecast = clip(1 minus the mean over horizons of (P90 minus P10) / (2 x critical\_cm), 0, 1), multiplied by 0.7 if M2 and the linear baseline differ by more than half the critical level at 60 min. If no forecast is available, 0.5.
- c\_model = (1 minus ood\_fraction) x (1 if calibrated, otherwise 0.85).
- c\_pred = 1 minus (H\_95 minus H\_05).
- Overall c = c\_data^0.25 x c\_sensor^0.25 x c\_forecast^0.15 x c\_model^0.15 x c\_pred^0.20 (weighted geometric mean, so one weak link drags the result down).
- Levels: HIGH at 0.75 or above, MEDIUM from 0.50, LOW below 0.50. Hard rule: any component below 0.30 forces LOW.
- Example: c\_data 0.90, c\_sensor 0.85, c\_forecast 0.70, c\_model 0.85, c\_pred 0.80 gives c = 0.83 (HIGH).
- Confidence describes the quality of the internal evidence. It is not a validated probability of being right; calibration is tracked separately with reliability diagrams (§32). Simulated sensors are indicated by the SIM badge, not by a hidden penalty.

### 17.3 Effect on decisions

| Confidence | Effect |
| --- | --- |
| HIGH | Normal flow |
| MEDIUM | Draft allowed; reviewer must open the evidence panel before approving |
| LOW | Level capped at MEDIUM; low\_confidence flag; approval requires an explicit acknowledgement; a field-verification action is added |
| INSUFFICIENT\_EVIDENCE | No level and no alert draft; the abstention record is shown to operators |

### 17.4 Abstention (INSUFFICIENT\_EVIDENCE)

Triggered by any of: no rainfall source within its freshness limit and no healthy sensor; static features for the ward missing; conflicting sensors (two or more healthy sensors in the ward whose utilisation differs by more than 0.6 while rainfall is low and no neighbour explains it); required model or configuration unavailable; overall confidence below 0.20. Response format:

```text
Cannot confidently determine risk.
Reason: <specific reason>
Missing inputs: <list>
Recommended action: human review / obtain additional data
```

Uncertainty is never converted into an arbitrary high-confidence prediction.

## 18. Human Oversight

### 18.1 Alert state machine

| From | To | Trigger and actor | Preconditions |
| --- | --- | --- | --- |
| (new) | DRAFT | Decision agent creates a draft (system) | RiskResult exists |
| DRAFT | AI\_GENERATED | Draft text and routes completed (system) | Verifier passed or template used |
| AI\_GENERATED | PENDING\_REVIEW | Policy check passed (system) | requires\_review true |
| PENDING\_REVIEW | APPROVED | APPROVE (permitted reviewer) | Evidence opened; acknowledgement if low confidence; not expired; prediction fresh |
| PENDING\_REVIEW | APPROVED | MODIFY\_APPROVE (permitted reviewer) | As above; modifications recorded; text re-verified |
| PENDING\_REVIEW | REJECTED | REJECT (permitted reviewer) | Comment required |
| PENDING\_REVIEW | CHANGES\_REQUESTED | REQUEST\_CHANGES (permitted reviewer) | Comment required; triggers a new analysis whose draft supersedes this one |
| APPROVED | DISPATCHED | dispatch\_alert (system) | Re-check of expiry and freshness; channels simulated |
| DISPATCHED | ACTIVE | First channel confirmation (system) | At least one simulated send succeeded |
| ACTIVE | RESOLVED | Approved resolve action | Reviewer approval |
| PENDING\_REVIEW or APPROVED | EXPIRED | Time passes (system) | valid\_until reached, or prediction older than the freshness limit (30 min) without reconfirmation |
| Any non-terminal | SUPERSEDED or CANCELLED | Newer alert for the ward, or operator cancels | Reason recorded |

Terminal states: REJECTED, RESOLVED, EXPIRED, SUPERSEDED, CANCELLED. The transition table is a dictionary in ewf.alerts.state\_machine; every change runs UPDATE ... WHERE status = expected (optimistic concurrency) and writes an audit entry.

Approval authority (separation of duties: administrators manage users and configuration but do not approve alerts):

| Severity | Who may approve |
| --- | --- |
| MEDIUM (internal advisory) | municipal\_operator, emergency\_coordinator |
| HIGH | municipal\_operator, emergency\_coordinator |
| VERY\_HIGH | emergency\_coordinator; optional two-person rule (config two\_person\_rule) |

A reviewer may edit the headline, message text, channels, selected shelters and valid\_until. Probability, level and evidence cannot be edited because they come from the model; a reviewer who disagrees uses a severity override with a mandatory comment, which is stored as an override and shown in the audit view.

### 18.2 Review screen

Shows risk level and probability, time to impact, confidence components, the drivers with evidence links, affected population and assets, the map with ward, indicative footprint, routes and shelters, the draft message, and the recommended actions as a checklist the reviewer can toggle. Buttons: Approve, Modify and approve, Request changes, Reject. Approve stays disabled until the evidence panel has been opened; a low-confidence draft also requires the acknowledgement tick.

### 18.3 Server-side enforcement and audit

- POST /alerts/{id}/approve checks: role permitted for the severity, status PENDING\_REVIEW, evidence\_opened true, acknowledgement when low\_confidence, not expired, prediction freshness within limit (otherwise 409 STALE and the reviewer must refresh), reviewer is not a system\_service.
- Every decision writes a human\_reviews row and audit\_logs entries with before and after JSON, actor, request id and a hash chain: hash = sha256(prev\_hash plus canonical JSON of the entry). scripts/verify\_audit.py recomputes the chain.
- Citizens never see drafts. Only DISPATCHED or ACTIVE alerts are visible to the citizen view.
- Demo autopilot: a demo driver script may call the approve endpoint as a seeded demo\_operator user. The server cannot tell and does not need to; the audit entry carries meta simulated\_approval true, the demo router is not mounted when APP\_ENV is production, and ALLOW\_LIVE\_DISPATCH stays false.

## 19. Decision Engine

### 19.1 Policy table (PROTOTYPE thresholds, not official)

| Level | Meaning | Actions proposed | Approval | Channels |
| --- | --- | --- | --- | --- |
| LOW | Monitor | MONITOR | None | None |
| MEDIUM | Prepare | PREPARE (internal advisory, check shelters, pre-position), PRIORITISE\_FACILITY | None for display-only internal items | Dashboard |
| HIGH | Warn | ISSUE\_ALERT, EVACUATION\_ROUTE, OPEN\_SHELTER (3 nearest safe), DEPLOY\_TEAM (pre-position), NOTIFY\_AUTHORITY, PRIORITISE\_FACILITY | Required | Dashboard, SMS, app |
| VERY\_HIGH | Urgent | As HIGH plus ALLOCATE\_RESOURCE, assistance for vulnerable groups, coordination | Required (coordinator) | Dashboard, SMS, app, IVRS and public announcement (simulated) |

These levels are not IMD colour-coded warnings and not GCC, TN SDMA or NDMA operating thresholds. IMD issues its own impact-based colour-coded warnings; this system must never present its levels as IMD warnings. Mapping to official procedures requires the authorities and is a production step.

Any action that leaves the operator console or commits resources (ISSUE\_ALERT, EVACUATION\_ROUTE, OPEN\_SHELTER, DEPLOY\_TEAM, NOTIFY\_AUTHORITY, ALLOCATE\_RESOURCE) requires approval. Resource recommendations name types and priorities (which facilities and roads first), not quantities, because no inventory data exists; quantities are left to the coordinator.

### 19.2 Rule format (config/policy.yaml)

Rules are structured data evaluated by a small interpreter. There is no eval and no free-form expression language.

```yaml
rules:
  - id: R-MED-PREPARE
    when: {level: MEDIUM}
    then:
      - {action: PREPARE, priority: 3, approval: false, channels: [DASHBOARD]}
  - id: R-HIGH-WARN
    when: {level_at_least: HIGH, confidence_not: LOW}
    then:
      - {action: ISSUE_ALERT, priority: 1, approval: true, channels: [DASHBOARD, SMS, APP]}
      - {action: EVACUATION_ROUTE, priority: 1, approval: true}
      - {action: OPEN_SHELTER, priority: 2, approval: true, count: 3}
      - {action: NOTIFY_AUTHORITY, priority: 2, approval: true}
  - id: R-VERY-HIGH-URGENT
    when: {level: VERY_HIGH, confidence_not: LOW}
    then:
      - {action: ALLOCATE_RESOURCE, priority: 1, approval: true}
      - {action: DEPLOY_TEAM, priority: 1, approval: true}
  - id: R-LOW-CONFIDENCE
    when: {confidence: LOW}
    then:
      - {action: PREPARE, priority: 2, approval: false, note: low-confidence-field-check}
```

### 19.3 Hard policy checks

1. No ISSUE\_ALERT with confidence LOW unless the reviewer acknowledges it.
2. requires\_approval can never be false for public-facing or resource-committing actions; the engine rejects such a draft.
3. In replay and backtest modes every alert body carries the marker PROTOTYPE - SIMULATED DATA.
4. At most one PENDING\_REVIEW alert per ward (duplicate rule, §15.2); at most 3 dispatched alerts per ward per hour (config).
5. English and reviewed Tamil text must both be present before dispatch.
6. Prioritisation: critical facilities inside the footprint are ranked by weight times flood probability (hospitals first); roads by class, underpass flag and flood probability.

## 20. Evacuation Routing

### 20.1 Graph

Build the drive and walk graphs for the AOI polygon plus a 5 km buffer with OSMnx (graph\_from\_polygon, network\_type drive or walk, simplified), add speeds and travel times (ox.routing.add\_edge\_speeds and add\_edge\_travel\_times in OSMnx 2.x; older versions expose them at top level), save as GraphML and record a graph\_version (download date plus parameters hash). This keeps the graph in the tens of thousands of edges. At build time stamp every edge with zone\_id, s\_e (static susceptibility: the maximum of S sampled every 25 m along the edge; underpasses are floored at 0.8) and is\_underpass (tunnel tag or negative layer).

### 20.2 Costs and the safe-route score (PROTOTYPE parameters)

```text
p_e    = clip(H_ward * s_e * (1 + 0.5 * underpass_e), 0, 1)     probability the edge is impassable now
blocked  if p_e >= 0.60                                         edge removed from the working graph
cost_e = travel_time_e * (1 + 8 * p_e)
SRS    = 100 * (1 - (0.5 * R_max + 0.3 * R_mean + 0.2 * min(1, T / 1800)))   R_max, R_mean: max and length-weighted mean of p_e on the route; T in seconds
shelter_score = 0.45 * SRS/100 + 0.25 * (1 - min(1, T/1800)) + 0.15 * capacity_score + 0.15 * flood_safety
```

capacity\_score is min(1, capacity / expected\_evacuees) when capacity is known and 0.5 with a visible capacity unknown flag otherwise. Weights are starting values.

```python
import networkx as nx

def penalise(G, ward_hazard: dict, p_block: float = 0.60, lam: float = 8.0):
    H = G.copy()
    for u, v, k, d in list(H.edges(keys=True, data=True)):
        p = min(1.0, ward_hazard.get(d.get('zone_id'), 0.0) * d.get('s_e', 0.0) * (1 + 0.5 * d.get('is_underpass', 0)))
        d['p_flood'] = p
        if p >= p_block:
            H.remove_edge(u, v, k)
        else:
            d['cost'] = d['travel_time'] * (1 + lam * p)
    return H

def routes_to_shelters(H, origin_node, shelter_nodes: dict, cutoff_s: float = 2400):
    dist, paths = nx.single_source_dijkstra(H, origin_node, cutoff=cutoff_s, weight='cost')
    return {sid: (dist[n], paths[n]) for sid, n in shelter_nodes.items() if n in dist}
```

### 20.3 Procedure

1. Origins: the ward's population-weighted centroid plus up to four of its highest population-times-susceptibility cells.
2. Candidate shelters: the 8 nearest by straight line with flood\_safety at least 0.7, not themselves in a ward with H of 0.6 or more, snapped to graph nodes.
3. Build the penalised graph once per assessment, run one Dijkstra per origin and profile (walk for shelters within 2 km, drive beyond), rank by shelter\_score, keep the top 3 routes per origin set, build geometries from edge geometries, store in evacuation\_routes with prediction\_id, alert\_id and graph\_version.
4. Recompute at approval time, because hazard may have changed. The reviewer sees the routes that would be sent.
5. Fallbacks: graph missing leads to straight-line nearest safe shelters and static corridors marked unverified; no reachable safe shelter leads to the message No safe route found, escalate to the coordinator. Routes are never fabricated.
6. Tests: a route avoids a blocked edge; an unreachable shelter is reported; a route ends within 50 m of the shelter; results are deterministic for the same inputs; one request takes under 3 s on the AOI graph.

## 21. Alert System

### 21.1 Channels (all external delivery is simulated in the MVP)

| Channel | MVP behaviour | Production path |
| --- | --- | --- |
| Dashboard | Real: alert queue, banners and toasts for operators | Same |
| SMS | Simulated adapter writes alert\_recipients rows and shows the message in a phone mockup | Licensed SMS gateway; commercial SMS in India requires registered sender IDs and templates (TRAI DLT) |
| Mobile notification | Simulated; shown in the citizen view | FCM and APNs |
| IVRS | Simulated call log holding the spoken text | IVR provider |
| Email | Simulated; used for municipal authorities | SMTP or provider |
| Public announcement | Operator checklist item only | Existing GCC procedures |
| CAP export | XML file generated for each dispatched alert, never transmitted | Integration with a national alerting platform only after official onboarding |

The UI labels every delivery SIMULATED DELIVERY. The system never claims that a message reached a person. Tamil text is Unicode: an SMS segment holds about 70 characters, so Tamil SMS bodies are kept under about 140 characters or split deliberately.

### 21.2 Alert payload

Fields: alert\_id, zone (id, name, ward\_no), severity, status, headline, message (en, ta), time\_to\_impact\_min, probability (rounded) with confidence level, valid\_until, public instructions (avoid low-lying roads, follow route, shelter names and distances), routes (ids and summaries), channels, issued\_at, approved\_by (role), is\_simulated, disclaimer. A full example is in §44.

### 21.3 Dispatch

1. dispatch\_alert(alert\_id) takes a row lock (SELECT ... FOR UPDATE), verifies status APPROVED and not expired, and verifies the prediction is still current.
2. Recipients: subscribers in the ward with consent and a matching channel (synthetic subscribers in the MVP).
3. For each channel adapter: send with up to 3 attempts (back-off 2, 4, 8 s). Idempotency comes from the primary key (alert\_id, subscriber\_id, channel).
4. Fallback order if a channel keeps failing: SMS, then app, then IVRS (config).
5. Set the alert DISPATCHED, then ACTIVE after the first simulated success; write metrics and audit entries.

Adapter interface: ChannelAdapter.send(alert, recipient) returns SendResult(ok, error). Implementations SimulatedSMS, SimulatedApp, SimulatedIVRS and SimulatedEmail succeed by default, with configurable failure injection (for example 3 percent) so retries and fallbacks can be demonstrated.

### 21.4 CAP 1.2 mapping (prototype status is Exercise)

| CAP element | Value |
| --- | --- |
| identifier, sent, expires | alert\_id, dispatched\_at, valid\_until |
| status | Exercise (never Actual in the prototype) |
| msgType, scope | Alert, Update or Cancel; Public |
| info.category, event | Met; Urban flood warning |
| info.responseType | Prepare or Evacuate according to the approved actions |
| info.urgency, severity, certainty | Expected or Immediate; HIGH maps to Severe and VERY\_HIGH to Extreme (MEDIUM to Moderate); Likely if probability is at least 0.6, else Possible |
| headline, description, instruction | Alert headline, explanation text, public instructions |
| area.areaDesc, area.polygon | Ward name; ward polygon as latitude,longitude pairs |

## 22. Frontend

### 22.1 Architecture

Single-page app in web/: React 18, TypeScript, Vite, MapLibre GL JS, ECharts, TanStack Query (polling), Zustand (UI state), Tailwind CSS, i18next (English and Tamil). TypeScript types are generated from the FastAPI OpenAPI schema with openapi-typescript. The access token is held in memory (sessionStorage for the demo). Routes are guarded by a RoleGate component that mirrors the server's RBAC; the server is the authority.

### 22.2 Views

| # | View | Purpose | Main components | Data (endpoints) |
| --- | --- | --- | --- | --- |
| 1 | City Overview | Situation at a glance | MapView with WardLayer coloured by level, KpiStrip (wards by level, active alerts, sensors online, data freshness), SimClockBar, EventTimeline, LayerPanel | /zones, /risk, /alerts, /health |
| 2 | Live Rainfall | Observed and forecast rain | HyetographChart (bars: observed, forecast), station and grid points, accumulation table | /data/rainfall |
| 3 | Water Levels | Sensor state and forecasts | SensorLayer, SensorSeriesChart with warn and critical lines and P10-P90 band, sensor health table | /sensors, /data/water-level, /forecast |
| 4 | Flood Risk Map | Spatial risk | WardLayer, FootprintLayer (indicative, inner and outer envelope), drains, roads at risk, shelters, time slider in replay | /risk, /events |
| 5 | Zone Details | One ward in depth | RiskCard (H, E, V, I, R, level), ConfidenceBreakdown, ForecastChart, assets impacted | /risk/{zone\_id} |
| 6 | Explainability Panel | Why this ward | DriverBars, EvidenceList with links, similar events, explanation text with verified badge, limitations | /explanations/{id} |
| 7 | Alerts | Queue, review, history | AlertQueue, AlertReviewPanel (§18.2), PhoneMockup for simulated deliveries | /alerts and actions |
| 8 | Evacuation Routes | Safe routes | RouteLayer, RouteTable with safety score, blocked segments, walk or drive toggle | /routes |
| 9 | Shelters | Destinations | ShelterLayer, ShelterTable (capacity unknown flagged, flood safety) | /shelters |
| 10 | Emergency Resources | What to prioritise | ActionChecklist by priority, facility and road priority lists, simulated response status board | /risk/{zone\_id}, /alerts |
| 11 | Historical Events | Context | Event list, extents on the map, rainfall curves, similar-event comparison | /events |
| 12 | Model Performance | Quality evidence | MetricsCards (labelled synthetic-validation or backtest), ReliabilityChart, ConfusionMatrix, lead-time histogram, ModelRegistryTable | /models |
| 13 | Continuous Learning | Prediction versus outcome | OutcomeSwipeMap (predicted against observed), error analysis, candidate model table with a promote action for administrators, accuracy-over-time chart | /outcomes, /models |

Citizen view (/citizen): ward selector, current level in plain language, dispatched alerts, routes and shelters, English and Tamil. It shows no drafts, no scores and no operator data.

### 22.3 UX rules

- A SimBadge is visible on every screen showing simulated data, plus a DegradedBanner whenever any fallback or degraded flag is active.
- Levels use the proposal's colours (Very High red, High orange, Medium yellow, Low green) and always a text label and icon, so colour is never the only signal.
- Times display in IST with the UTC value in a tooltip. Numbers shown in the UI open their evidence on click.
- The map works without any external basemap (plain background plus our layers); an optional PMTiles basemap for the Chennai extent adds offline context.
- Polling intervals in demo: risk 5 s, sensors 5 s, alerts 3 s; polling pauses while the tab is hidden. Ward GeoJSON is simplified (ST\_Simplify at 5 m) and cached.
- Keyboard-accessible review buttons, reduced-motion respect, error boundaries and skeleton loaders on every panel.

## 23. API Specification

### 23.1 Conventions

- Base path /api/v1. JSON only. Timestamps are ISO 8601 with an explicit offset (UTC). A request id is accepted in X-Request-ID or generated, echoed in the response and logged.
- Authentication: POST /auth/login returns a JWT (60 min); send Authorization: Bearer token. Roles: citizen, municipal\_operator, emergency\_coordinator, administrator, researcher, system\_service. §29 holds the permission matrix.
- Pagination: limit (default 50, maximum 500) and cursor.
- Error envelope: an object with error.code, error.message, error.details and error.request\_id. Codes: 400 BAD\_REQUEST, 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 NOT\_FOUND, 409 CONFLICT, STALE\_PREDICTION or INVALID\_TRANSITION, 413 PAYLOAD\_TOO\_LARGE, 422 VALIDATION\_ERROR, 429 RATE\_LIMITED, 500 INTERNAL, 503 DEGRADED\_DEPENDENCY.
- Ingestion endpoints return 202 with accepted, rejected and run\_id; they are idempotent on the natural key.

### 23.2 Endpoints

| Method and path | Roles | Request | Response | Errors |
| --- | --- | --- | --- | --- |
| POST /auth/login | public | username, password | access\_token, token\_type, expires\_in, role | 401 |
| GET /health | public | none | status, db, models, clock, mode, degraded list, version | 503 if the database is down |
| POST /data/rainfall | system\_service, administrator | RainfallBatch: source, records\[\] | IngestResult | 413, 422 |
| POST /data/water-level | system\_service | SensorBatch: readings\[\] | IngestResult with quality-flag histogram | 413, 422 |
| GET /data/rainfall | operators, researcher | zone\_id or station\_id, from, to | series | 404, 422 |
| GET /data/water-level | operators, researcher | sensor\_id or zone\_id, from, to | series with quality flags | 404, 422 |
| GET /sensors | operators, researcher | zone\_id (optional) | sensors with status and last\_seen | 403 |
| GET /zones | any authenticated | include=risk (optional) | GeoJSON FeatureCollection of wards; citizens receive public fields only | 401 |
| GET /risk | operators; citizen limited | level\_at\_least, zone\_ids, as\_of | latest risk summaries | 422 |
| GET /risk/{zone\_id} | operators; citizen limited | history=true (optional) | latest RiskResult (history if asked) | 404 |
| GET /explanations/{risk\_id} | operators, researcher | none | Explanation with evidence | 404 |
| POST /forecast | operators, researcher, system\_service | zone\_id, as\_of | ForecastResult (read-only, computed now) | 404, 409 no fresh data |
| POST /risk/analyze | operators, system\_service | zone\_id or zone\_ids, as\_of | outcome (DRAFTED, NO\_ALERT, ABSTAINED), RiskResult, alert\_id | 404, 422, 503 |
| GET /alerts | operators; citizen sees dispatched only | status, zone\_id | alerts (public fields for citizens) | 403 |
| POST /alerts | municipal\_operator, emergency\_coordinator | manual draft: zone\_id, severity, headline, body\_en | Alert in PENDING\_REVIEW; the author cannot approve it | 409, 422 |
| POST /alerts/{id}/approve | per severity (§18.1) | evidence\_opened, acknowledged\_low\_confidence, comment, modifications, severity\_override | Alert with delivery summary | 403, 409 STALE\_PREDICTION or INVALID\_TRANSITION |
| POST /alerts/{id}/reject | per severity | comment (required) | Alert (REJECTED) | 403, 409, 422 |
| POST /alerts/{id}/request-changes | per severity | comment (required) | Alert (CHANGES\_REQUESTED) and new analysis id | 403, 409, 422 |
| GET /alerts/{id}/cap | operators | none | CAP 1.2 XML with status Exercise | 404 |
| GET /routes | operators; citizen limited | alert\_id, prediction\_id or zone\_id | RouteOption list | 404 |
| GET /shelters | any authenticated | zone\_id, near=lon,lat, limit | shelters with capacity\_known | 422 |
| GET /events | any authenticated | from, to | historical events; GET /events/{id}/extents returns geometries | 404 |
| POST /feedback | operators, researcher; citizen limited | alert\_id or outcome\_id, kind, text, optional point | Feedback | 422 |
| POST /outcomes | operators, researcher, system\_service | OutcomeFeedback | stored and evaluated outcome | 404, 422 |
| GET /models | operators (read), researcher, administrator | status filter | model\_versions with metrics | 403 |
| POST /models/{id}/promote | administrator | comment | model promoted; previous PRODUCTION retired | 403, 409 if the candidate has not passed evaluation |
| POST /demo/control, GET /demo/state | administrator (not mounted in production) | action: start, pause, reset, set\_speed, jump; scenario\_id; speed | simulation state | 403, 409 |

### 23.3 Behaviour notes

- /risk/analyze runs the assessment graph synchronously for one ward (target under 30 s) and returns 202 with a run id for several wards.
- Approval is atomic: the approve call validates, transitions to APPROVED, runs dispatch and returns the final state, so a reviewer never leaves an alert half-approved.
- Citizen responses are filtered by a response model that omits drafts, scores, evidence and operator comments.
- Rate limits (per token): 60 requests per minute for operators, 600 for system\_service ingestion; exceeding returns 429.
- Request and response models for every endpoint are Pydantic classes in ewf.api.schemas; OpenAPI is the source of the frontend types. Examples for each endpoint are in §44.

## 24. Repository Structure

### 24.1 File tree

```text
chennai-ewf/
├── README.md  Makefile  pyproject.toml  uv.lock  .env.example  .gitignore  .pre-commit-config.yaml  docker-compose.yml
├── docker/        api.Dockerfile  web.Dockerfile  nginx.conf
├── config/        app.yaml aoi.yaml datasets.yaml risk.yaml policy.yaml sensors.yaml routing.yaml alerts.yaml logging.yaml
│   └── scenarios/ demo_storm_01.yaml  fault_schedule_demo.yaml  backtest_2015.yaml  backtest_2023.yaml
├── data/          raw/ interim/ processed/ models/ graphs/ (git-ignored)   manifest.yaml  README.md
├── db/            alembic.ini  migrations/versions/0001_baseline.py  sql/0001_baseline.sql  seeds/ (users, subscribers, kb/, events.yaml)
├── src/ewf/
│   ├── core/         settings clock logging errors ids timeutil crs hashing
│   ├── db/           engine  repositories/ (rainfall sensors zones risk alerts audit ...)
│   ├── ingestion/    base contracts validators  adapters/ (openmeteo imerg imd_grid ecmwf replay sensor_http gcc_arcgis)
│   ├── geo/          grid terrain hand zonal drainage exposure footprint history  loaders/
│   ├── features/     rainfall waterlevel static builder leakage
│   ├── models/       susceptibility/ forecast/ (baselines train predict exceed) hazard/ (function calibrate) registry metrics calibration
│   ├── risk/         engine exposure vulnerability matrix confidence config
│   ├── explain/      drivers evidence similarity templates verifier kb
│   ├── decision/     policy actions resources  i18n/ (en.yaml ta.yaml)
│   ├── routing/      graph costs shelters engine
│   ├── alerts/       state_machine drafting dispatcher cap  channels/ (base simulated)
│   ├── learning/     outcomes evaluation recalibrate candidates promote
│   ├── agents/       contracts base data_agent forecasting_agent risk_agent rca_agent decision_agent graph orchestrator  llm/ (client providers guard)
│   ├── simulation/   clock scenario hyetograph sensor_model faults placement truth runner
│   ├── api/          main deps auth rbac middleware  routers/ (auth health data zones risk alerts routes events feedback models demo)  schemas/
│   └── worker/       main jobs
├── web/           package.json vite.config.ts  src/ (api components views hooks store i18n theme)
├── scripts/       fetch_data build_db build_grid build_terrain build_static_features build_roads_graph place_sensors
│                  train_susceptibility train_forecaster calibrate_hazard seed_demo run_demo backtest verify_audit replay_prediction
├── notebooks/     eda_rainfall  labels_qc  forecast_models  risk_sensitivity
├── tests/         unit integration geo models agents api sim e2e conftest.py
├── docs/          ARCHITECTURE DATA LIMITATIONS RUNBOOK DEMO  MODEL_CARDS/  ADR/
└── .github/workflows/ci.yml
```

### 24.2 Responsibilities

| Folder | Responsibility |
| --- | --- |
| config/ | Domain configuration in YAML (versioned); scenarios for the simulator |
| data/ | Files only: raw, interim, processed, models, graphs; manifest is the only committed file besides the README |
| db/ | Alembic revisions and the SQL they run; seed data |
| src/ewf/core | Settings, Clock, logging, errors, timezone and CRS helpers shared by everything |
| src/ewf/ingestion | Adapters and validators; the only code that talks to external data sources |
| src/ewf/geo, features | Geospatial processing and leak-free feature builders |
| src/ewf/models | M1, M2, M3, registry, metrics |
| src/ewf/risk, explain, decision | Deterministic engines: risk, explanation, policy |
| src/ewf/routing, alerts | Route computation; alert state machine, drafting, simulated dispatch, CAP |
| src/ewf/agents | Contracts, six agents, graph, orchestrator, LLM adapter and guard |
| src/ewf/simulation | Sensor simulator, scenarios, faults, simulated truth |
| src/ewf/api, worker | HTTP application and scheduler; thin layers over the domain packages |
| web/ | React application |
| scripts/ | Reproducible command-line entry points for data build, training and demo |
| tests/ | By layer; e2e runs the full storyline |

### 24.3 Conventions

- Dependency direction is enforced in CI with import-linter: core, then db, then ingestion, geo and features, then models, risk, explain and routing, then decision, alerts and learning, then agents, then api and worker. api routers contain no business logic.
- No network calls at import time; no module reads environment variables except ewf.core.settings.
- Every script is idempotent, accepts --aoi and --dry-run where meaningful, and writes a sidecar JSON.
- Make targets: make setup, make data, make db, make train, make up, make seed, make demo, make test, make lint.

## 25. Configuration

### 25.1 Principles

Environment variables hold secrets and environment differences. YAML holds domain parameters. Pydantic validates both at start-up and the application refuses to run on invalid configuration. .env is never committed; .env.example is. Risk and policy configuration is hashed and stored in config\_versions so every prediction can name the exact version used.

### 25.2 .env.example

```text
APP_ENV=development              # development, demo, production
APP_MODE=replay                  # replay, backtest, live
DATABASE_URL=postgresql+psycopg2://ewf:change-me@db:5432/ewf
JWT_SECRET=change-me-long-random
JWT_EXPIRES_MIN=60
ALLOW_LIVE_DISPATCH=false
LLM_MODE=template                # off, template, llm
LLM_PROVIDER=anthropic           # anthropic, google, ollama
LLM_MODEL=claude-haiku-5-5       # verify availability and price at build time
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
OLLAMA_BASE_URL=http://host.docker.internal:11434
EARTHDATA_USERNAME=
EARTHDATA_PASSWORD=
OPENMETEO_BASE_URL=https://api.open-meteo.com/v1/forecast
DISPLAY_TIMEZONE=Asia/Kolkata
DATA_DIR=/app/data
LOG_LEVEL=INFO
```

### 25.3 config/risk.yaml (PROTOTYPE values)

```yaml
version: risk-2026-10-v1
provenance: prototype              # not official thresholds
hazard:
  intercept: -7.5
  calibration: {shift_b: 0.0, temperature_t: 1.0}
  features:
    rain_hr_eq:       {scale: 50,  clip: 1.5, weight: 1.6, group: extreme_rainfall}
    rain_fcst_60:  {scale: 50,  clip: 1.5, weight: 0.8, group: extreme_rainfall}
    rain_ante_24h: {scale: 100, clip: 1.5, weight: 0.6, group: extreme_rainfall}
    util_max:      {scale: 1.0, clip: 1.2, weight: 1.4, group: drainage_stress}
    rise_max:      {scale: 2.0, clip: 1.5, weight: 1.2, group: rapid_water_rise}
    exceed_60:     {scale: 1.0, clip: 1.0, weight: 1.4, group: rapid_water_rise}
    s_p90:         {scale: 1.0, clip: 1.0, weight: 1.0, group: terrain}
    low_elev:      {hand_ref_m: 3.0,       weight: 0.6, group: terrain}
    hist_freq:     {scale: 1.0, clip: 1.0, weight: 0.6, group: history_land_use}
    imperv:        {scale: 1.0, clip: 1.0, weight: 0.4, group: history_land_use}
    tide:          {scale: 100, clip: 1.0, weight: 0.5, group: tide, coastal_only: true}
  rain_static_variant:       # sensors unavailable
    intercept: -6.0
    weights: {rain_hr_eq: 2.4, rain_fcst_60: 1.2, rain_ante_24h: 0.8, s_p90: 1.0, low_elev: 0.6, hist_freq: 0.6, imperv: 0.4, tide: 0.5}
  sensor_static_variant:     # rainfall unavailable
    intercept: -5.0
    weights: {util_max: 2.0, rise_max: 1.6, exceed_60: 1.8, s_p90: 1.0, low_elev: 0.6, hist_freq: 0.6, imperv: 0.4}
exposure:
  weights: {pop: 0.40, buildings: 0.15, roads: 0.15, critical: 0.30}
  critical_weights: {hospital: 5, power: 4, water_works: 4, school: 3, fire_station: 3, police: 3, shelter: 2}
  facility_min_susceptibility: 0.5
vulnerability:
  weights: {sensitive_pop: 0.40, shelter_gap: 0.25, egress: 0.20, density: 0.15}
impact: {w_exposure: 0.5, w_vulnerability: 0.5}
risk_index: {gamma: 0.6}
matrix:
  hazard_edges: [0.30, 0.60, 0.85]
  impact_edges: [0.33, 0.66]
  table:                     # rows hazard band 0..3, columns impact band 0..2; 0 LOW, 1 MEDIUM, 2 HIGH, 3 VERY_HIGH
    - [0, 0, 0]
    - [0, 1, 1]
    - [1, 2, 2]
    - [2, 3, 3]
confidence:
  weights: {data: 0.25, sensor: 0.25, forecast: 0.15, model: 0.15, pred: 0.20}
  levels: {high: 0.75, medium: 0.50}
  hard_floor: 0.30
  abstain_below: 0.20
  expected_latency_min: {gauge: 5, sensor: 3, imerg_early: 240, forecast: 180}
  tau_min: {rain: 30, sensor: 30, forecast: 120}
footprint: {tau_base: 0.8, tau_slope: 0.5, hand_base_m: 0.5, hand_slope_m: 2.5, envelope_delta: 0.15, hist_buffer_m: 150}
```

### 25.4 config/app.yaml

```yaml
cadence: {sensor_tick_s: 60, assess_tick_s: 300, forecast_refresh_s: 1800}
horizons_min: [15, 30, 60, 120]
freshness: {rain_max_age_min: 360, sensor_max_age_min: 10, forecast_max_age_min: 360}
alerts: {prediction_ttl_min: 30, max_dispatch_per_ward_hour: 3, two_person_rule: false}
tti: {exceed_prob: 0.5}
routing: {p_block: 0.60, lambda: 8.0, cutoff_s: 2400, walk_max_m: 2000, shelter_candidates: 8, shelter_min_safety: 0.7}
simulation: {speed: 60, seed: 42, sensors: 50}
llm: {max_tokens: 600, cache: true, max_calls_per_alert: 2}
```

Other files: datasets.yaml (the manifest source of truth for fetch\_data), aoi.yaml (hero ward, neighbour rings, cap of 15 wards), sensors.yaml (placement parameters, fault rates), policy.yaml (§19.2), alerts.yaml (channel order, retry settings, helpline text placeholders to be filled and verified), scenarios/ (§37, §45).

### 25.5 Secrets and validation

- Secrets live only in .env, CI secrets or the deployment environment. docker-compose reads env\_file. detect-secrets runs in pre-commit and CI.
- Earthdata and other data-download credentials are needed only on the machine that runs make data, not at demo time.
- On start-up the app loads and validates every YAML file, computes its sha256 and inserts a config\_versions row if the hash is new. Changing a weight therefore creates a new version automatically.

## 26. MLOps

### 26.1 Practical scope

| Concern | Approach (MVP) |
| --- | --- |
| Dataset versioning | data/manifest.yaml plus sidecar JSON per processed file. A training run stores data\_manifest\_sha256 (hash of the manifest entries it used) and the ids of its train, validation and test scenarios or events |
| Experiment tracking | Each run writes runs/model/timestamp/ with params.json, metrics.json, feature\_importance.csv, plots, the model file, pip freeze and the git commit. No tracking server |
| Model card | Auto-generated docs/MODEL\_CARDS/name-version.md: intended use, data, metrics with their label (real, backtest, synthetic-validation), limitations |
| Registry | model\_versions table; artifacts under data/models/name/version/. Status CANDIDATE, STAGING, PRODUCTION, RETIRED; a partial unique index allows exactly one PRODUCTION per name |
| Loading | The loader reads the PRODUCTION row and verifies the artifact checksum before use |
| Rollback | POST /models/id/promote on the previous version; the current PRODUCTION row becomes RETIRED |
| Reproducibility | Predictions store model\_version\_ids, config\_version, inputs\_hash and the feature snapshot. scripts/replay\_prediction.py recomputes a stored prediction and a test asserts the result matches |

### 26.2 Promotion gate (tolerances are PROTOTYPE values in config)

A candidate may be promoted only if, on the frozen test set: its primary metric is no worse than the current PRODUCTION model (MAE skill for M2, PR-AUC for M1); recall for high-risk wards is not lower by more than 0.02; expected calibration error is not higher by more than 0.02; the candidate has a model card; and an administrator supplies a comment. Failing any rule blocks promotion (409). MLflow, DVC, a feature store and Kubeflow are deliberately not used in the MVP; they are options once real telemetry and several maintainers exist.

## 27. Continuous Learning

### 27.1 The loop

| Step | Component | Result |
| --- | --- | --- |
| 1 Prediction | Risk engine | risk\_predictions with inputs hash and versions |
| 2 Actual outcome | ewf.learning.outcomes | prediction\_outcomes from sensors, simulated truth, SAR labels, reports or manual confirmation |
| 3 Comparison | ewf.learning.evaluation | TP, FP, FN, TN; lead time; Brier score; calibration; footprint IoU |
| 4 Error analysis | evaluation report | Where and why errors occurred (for example a missed low-lying pocket) |
| 5 Dataset update | Controlled script | New verified event added to historical\_flood\_events; labels and hist\_freq rebuilt under the vintage rule |
| 6 Candidate | recalibrate, train scripts | New calibration (b, T), config or model as CANDIDATE |
| 7 Evaluation | Offline, on held-out events | Comparison with PRODUCTION through the gate in §26.2 |
| 8 Approval and promotion | Administrator | New versioned PRODUCTION; audit entry |
| 9 Better future prediction | Same pipeline | Next assessments use the new version |

### 27.2 Outcome matching and metrics

- An outcome matches a prediction by ward and the window from issued\_at to issued\_at plus horizon. Decision metrics treat level HIGH or above as a positive prediction; probability metrics use H directly (Brier score, reliability).
- lead\_time is the observed onset minus the dispatch time of the alert (or the prediction time if none was dispatched). IoU is computed in UTM between the predicted indicative footprint and the observed extent.
- Reported per event and as a rolling window: precision, recall, F1, false alarm ratio, miss rate, lead-time distribution, Brier score, calibration error, IoU, alert latency.

### 27.3 What may change, and how

| Change | Mechanism | Approval |
| --- | --- | --- |
| Calibration (b, T) | Automated candidate from recent outcomes | Administrator, after the gate |
| Thresholds, matrix edges, policy rules | Proposal from error analysis, new config\_version | Emergency coordinator and administrator |
| Model retraining (M1 with new labels, M2 with new scenarios or real telemetry) | New CANDIDATE | Administrator, after the gate |
| Knowledge (events, local notes, hist\_freq) | Verified additions under the vintage rule | Researcher with a second reviewer |

There is no online learning and no automatic deployment. Events used to build a candidate are excluded from that candidate's evaluation, and evaluation is always on later or held-out events.

### 27.4 Hackathon demonstration

At T plus 1 day: (1) the simulated truth (and the 2023 analog) is ingested as outcomes; (2) the comparison view shows predicted against observed with IoU and lead time; (3) error analysis lists the missed or over-warned areas; (4) scripts/recalibrate.py proposes a candidate calibration; (5) the offline evaluation compares it with the current model on held-out events; (6) an administrator promotes it only if the gate passes; (7) the next assessment shows the new version. If the candidate does not improve, the screen says so and nothing is promoted. That is also a valid and honest result.

## 28. Failure Handling

### 28.1 Failure matrix

| Case | Detection | Fallback | User-visible behaviour | Logging | Severity |
| --- | --- | --- | --- | --- | --- |
| No rainfall data | Freshness check fails for every source in the chain | Chain: gauge, IMERG, Open-Meteo recent hours. If none, use the sensor\_static hazard variant and cap confidence at MEDIUM | Banner: rainfall feed unavailable, using sensors only | WARN rainfall\_feed\_down | High |
| No forecast | Forecast missing or older than the limit | Forecast features set to 0 with fcst\_missing; c\_forecast 0.5; time to impact from sensors only | Banner: forecast unavailable | WARN forecast\_missing | Medium |
| Sensor offline | No reading for more than 10 min | Exclude; use validated neighbours within 1.5 km; if none, rain\_static variant | Sensor shown grey; banner if a ward has fewer than 2 healthy sensors | INFO per sensor, WARN per ward | Medium |
| Sensor anomaly | Validator flags SUSPECT or BAD | Exclude from features; if half of a ward's sensors are anomalous apply the conflict rule | Flag icon and a data-quality note | WARN sensor\_anomaly | Medium |
| Database unavailable | Connection errors; /health fails | Writes return 503 DEGRADED\_DEPENDENCY; reads serve the last ward summary from a 60 s in-memory cache marked stale; sensor gateway retries with back-off | Full-width banner: database unavailable, data may be stale | ERROR db\_down | Critical |
| LLM unavailable | Timeout, 5xx, auth or quota error, or guard rejects twice | Template explanation; mode recorded as template | Explanation tagged standard wording | WARN llm\_fallback | Low |
| Routing unavailable | Graph missing, exception, or no path | Straight-line nearest safe shelters and static corridors marked unverified | Route panel shows unverified; coordinator message if no safe route | ERROR routing\_down | High |
| Low confidence | Overall confidence below 0.50 | Cap level at MEDIUM; mandatory acknowledgement; add field-verification action | Amber low-confidence tag with the weak components | INFO low\_confidence | Medium |
| Conflicting sources | Gauge shows 0 mm while sensors rise fast; IMERG and Open-Meteo differ by more than 3 times; sensors disagree | Prefer observations over models; keep both values as evidence; lower c\_data; apply the abstention rule for sensor conflict | Sources disagree card showing both values | WARN source\_conflict | Medium |
| Missing historical event | Similarity search returns fewer than 2 events | Omit the history sentence and say none documented | Text states no sufficiently similar documented event | INFO no\_analog | Low |
| Invalid geometry | ST\_IsValid false, SRID mismatch, empty geometry | Repair with make\_valid; if still invalid reject to rejected\_records; a static load that fails rolls back | Admin data-quality panel | ERROR bad\_geometry | Medium (High for ward boundaries) |
| Stale data | Age beyond the freshness limit | Stop using the input, flag it stale, c\_data falls | Stale badge showing the age | WARN stale\_input | Medium |
| Notification failure | Adapter error | 3 retries, then fallback channel; record failure; alert the operator | Delivery summary lists failures | ERROR notify\_failed | High |
| Model load failure | Missing artifact, checksum mismatch, exception | Previous PRODUCTION version, else baselines (persistence, linear rate) and hazard priors | Degraded-model banner | ERROR model\_load | High |
| Agent or node failure | Exception in a node | Up to 2 retries, then run FAILED with no partial alert; next tick retries; idempotency prevents duplicates | Assessment failed for the ward; operator can re-run | ERROR agent\_failed | High |
| Clock anomaly | Sensor skew above 120 s; simulation clock jump | Use received\_at for skewed readings and flag them; simulation jumps handled through as\_of | None | WARN clock\_skew | Low |

### 28.2 Safety floors (deterministic, applied after the risk matrix)

A smooth hazard function must never hide direct observations. After the matrix and before the confidence gate the engine applies floors that can only raise the level, never lower it (PROTOTYPE values, recorded as RULE evidence):

- F1: a healthy sensor at or above its critical level raises the level to at least HIGH (at least MEDIUM if confidence is LOW).
- F2: a healthy sensor with utilisation of 0.9 or more and a rise of at least 0.5 cm/min raises the level to at least MEDIUM.
- F3: rain\_hr\_eq of 100 mm/hr or more raises the level to at least MEDIUM.

In the MVP the floor constants live in apply\_floors (§36.9); move them into risk.yaml under a floors key if they need tuning. Tests T06 and T20 in §31 cover them.

## 29. Security

### 29.1 Roles and permissions

| Capability | citizen | municipal\_operator | emergency\_coordinator | administrator | researcher | system\_service |
| --- | --- | --- | --- | --- | --- | --- |
| View dispatched alerts, public level, shelters, routes | Yes | Yes | Yes | Yes | Yes | No |
| View scores, drivers, evidence, forecasts | No | Yes | Yes | Yes | Yes | No |
| View drafts and the review queue | No | Yes | Yes | No | No | No |
| Create a manual alert draft | No | Yes | Yes | No | No | No |
| Approve or reject HIGH | No | Yes | Yes | No | No | No |
| Approve or reject VERY\_HIGH | No | No | Yes | No | No | No |
| Request a forecast (POST /forecast) | No | Yes | Yes | No | Yes | Yes |
| Run an assessment (POST /risk/analyze) | No | Yes | Yes | No | No | Yes |
| Ingest data | No | No | No | Rainfall only | No | Yes |
| Submit feedback or outcomes | Feedback only | Yes | Yes | No | Yes | Outcomes only |
| View the model registry | No | Yes | Yes | Yes | Yes | No |
| Promote a model | No | No | No | Yes | No | No |
| Manage users and configuration | No | No | No | Yes | No | No |
| Read the audit log | No | No | Yes | Yes | Yes | No |
| Demo control (not in production) | No | No | No | Yes | No | No |

### 29.2 Controls

- Authentication: JWT (HS256 in the MVP, secret from the environment, 60 min expiry, claims sub, role, jti); bcrypt (cost 12) for seeded demo passwords; five failed logins lock the account for 5 minutes. Service tokens for the simulator and worker carry only the system\_service role. Production: OIDC (Keycloak or Azure AD), short-lived tokens, multi-factor authentication for approvers.
- API: CORS allow-list; request size limits; Pydantic validation on every body; parameterised SQL only; rate limits (§23.3); nginx security headers (content security policy, X-Content-Type-Options, X-Frame-Options DENY, HSTS in production); the OpenAPI UI is disabled or authenticated in production.
- Separation of duties: no agent can dispatch; an author cannot approve their own manual draft; administrators cannot approve alerts; every approval is audited.
- Audit: audit\_logs is append-only (trigger §7.4) with the hash chain from §18.3. The application database role has INSERT but not UPDATE or DELETE on it. A supporting endpoint GET /audit (coordinator, administrator, researcher) filters by entity.
- Secrets: environment only, never in images or git; detect-secrets in pre-commit and CI; separate keys per environment; the LLM key is restricted and spend-capped.
- Privacy: subscribers hold a salted hash of the contact address (synthetic in the MVP); logs never contain contact details; location is ward-level; consent is a column. Before real subscriber data is handled, obtain legal review under India's Digital Personal Data Protection Act, 2023.
- LLM exposure: prompts contain only system-generated JSON. No user text, feedback or external feed text enters a prompt, which removes the prompt-injection path. The LLM has no tools and its output passes the verifier.
- Supply chain: pinned lockfile, pip-audit and npm audit in CI.

## 30. Observability

### 30.1 Logging

structlog emits JSON with ts (UTC), level, event, request\_id, run\_id, zone\_id, agent, tool, latency\_ms, model\_version, config\_version, alert\_id and actor. No personal data. Event names: ingest.batch, sensor.status\_change, model.infer, agent.run, tool.call, risk.assessed, alert.created, review.decided, notify.sent, learning.candidate\_created, and error.\* for failures.

### 30.2 Metrics (prometheus\_client at /metrics, access restricted)

| Metric | Type | Meaning |
| --- | --- | --- |
| ewf\_ingest\_latency\_seconds{source} | histogram | Stored time minus observed\_at |
| ewf\_ingest\_records\_total{source,outcome} | counter | Accepted, rejected, duplicate |
| ewf\_data\_freshness\_seconds{source} | gauge | Age of the newest record |
| ewf\_sensor\_availability\_ratio{zone} | gauge | Healthy sensors over registered sensors |
| ewf\_prediction\_latency\_seconds{stage} | histogram | Per node and end to end |
| ewf\_assessment\_total{outcome} | counter | DRAFTED, NO\_ALERT, ABSTAINED, FAILED |
| ewf\_alert\_latency\_seconds{leg} | histogram | Risk to PENDING\_REVIEW; approval to dispatch |
| ewf\_notification\_total{channel,status} | counter | Simulated deliveries |
| ewf\_model\_confidence | histogram | Overall confidence of assessments |
| ewf\_forecast\_mae\_cm{horizon,label} | gauge | From learning jobs, labelled synthetic-validation or backtest |
| ewf\_false\_positive\_total, ewf\_false\_negative\_total | counters | From outcomes |
| ewf\_llm\_calls\_total{result}, ewf\_llm\_guard\_rejections\_total | counters | LLM use and verifier rejections |
| ewf\_degraded\_mode{reason} | gauge | 1 while a fallback is active |

### 30.3 Dashboards, alerts and traces

An optional Grafana profile in Compose holds three boards: pipeline health, model quality, alerting. Suggested alert rules: no sensor data for 5 min; ingestion failing; assessments failing; median confidence below 0.5; notification failure rate above 20 percent. agent\_runs and tool\_calls are the lightweight trace store; OpenTelemetry is a production option.

## 31. Testing

### 31.1 Strategy

| Layer | Scope | Tools |
| --- | --- | --- |
| Unit | Feature calculations, risk formula (property tests for monotonicity with hypothesis), geo helpers, validators, state-machine transitions | pytest, hypothesis |
| Integration | Ingestion to features to risk; risk to explanation; explanation to recommendation; approval to dispatch | pytest with a PostGIS service container |
| Geospatial | CRS, assignment, conservation, routes (§8.5) | pytest, geopandas |
| Model | Scenario and event holdout, calibration, baselines, leakage | pytest, LightGBM |
| Agent | Valid input, missing data, contradictory data, tool failure, abstention for each agent | pytest with fakes |
| API | Authentication, RBAC matrix (parametrised over §29.1), validation errors, idempotency | httpx TestClient |
| Simulation | Same seed gives the same series; injected faults are detected | pytest |
| End to end | The full storyline of §37 | pytest plus the demo driver; Playwright smoke test of the dashboard (optional) |

### 31.2 Named test cases

| ID | Scenario | Expected |
| --- | --- | --- |
| T01 | Rainfall spike: rain\_hr\_eq jumps from 5 to 110 mm/hr while sensors are still flat | Hazard rises monotonically with the spike; floor F3 raises the level to at least MEDIUM at the first assessment; HIGH only after the sensors respond |
| T02 | Sensor spike: one reading at twice the drain depth, rain low | Flagged SUSPECT, excluded; level unchanged; no alert; sensor\_confidence reduced |
| T03 | Missing sensors: every sensor in the ward offline, heavy rain | rain\_static variant; status DEGRADED; confidence at most MEDIUM; review requires opening the evidence |
| T04 | High rainfall in a low-elevation ward (HAND p10 0.3 m, S 0.85) versus a high ward (3 m, 0.2) | Hazard and level are higher for the low ward (monotonicity) |
| T05 | High rainfall with good drainage (low utilisation, low rise, low S) | Hazard lower than T04; level at most MEDIUM |
| T06 | Low rainfall with a high water level (utilisation 0.9, rise 0.6 cm/min) | Level at least MEDIUM through floor F2 |
| T07 | Historical similarity: event vector close to December 2015 | similar\_event\_ids lists it first; history sentence appears only when the ward has a label for that event |
| T08 | High risk with LOW confidence (c\_sensor forced to 0.2) | Level capped at MEDIUM; low\_confidence true; approve without acknowledgement fails; with it succeeds |
| T09 | Critical alert approval | HIGH alert PENDING\_REVIEW; approve as operator with evidence\_opened; status DISPATCHED then ACTIVE; recipients SIMULATED\_SENT; human\_reviews and audit rows exist; hash chain verifies |
| T10 | Alert rejection | Reject without comment returns 422; with comment REJECTED; no recipients; a later approve returns 409 INVALID\_TRANSITION |
| T11 | Citizen visibility | Citizen cannot read drafts, scores or evidence |
| T12 | LLM guard | An invented number or unknown evidence id is rejected; template text is used |
| T13 | Leakage | Feature builder raises LeakageError for data after as\_of |
| T14 | Idempotent ingestion | The same batch twice stores one set of rows |
| T15 | Simulator determinism | Same seed and scenario give identical series |
| T16 | Routing | Route avoids a blocked underpass; unreachable shelter reported |
| T17 | Abstention | No rainfall source and no healthy sensors gives INSUFFICIENT\_EVIDENCE and no draft |
| T18 | Clock jump | Simulation jump creates no duplicate alert |
| T19 | Audit immutability | UPDATE or DELETE on audit\_logs raises |
| T20 | Floors and live mode | F1 raises the level as specified; dispatch is refused when ALLOW\_LIVE\_DISPATCH is false in live mode |

CI: ruff, mypy (strict on risk, alerts and agents.contracts), import-linter, pytest on a postgis/postgis:16-3.4 service container, web lint, unit tests and build, Docker build. The end-to-end job runs nightly and before the demo. Coverage aims (targets, not results): 80 percent line coverage on risk, alerts, agents and ingestion; every state-machine transition exercised.

## 32. Evaluation

### 32.1 Key performance indicators (targets are design targets, not results)

| Area | Metric | Design target | Achieved |
| --- | --- | --- | --- |
| Forecasting (synthetic-validation) | MAE, RMSE, R-squared per horizon; skill against persistence | Skill at or above 0 at all horizons and at least 0.10 at 30 and 60 min | From reports/metrics.json |
| Forecasting | P10 to P90 coverage | 0.70 to 0.90 | From reports |
| Exceedance | Precision, recall, F1, PR-AUC, Brier | Report; recall prioritised over precision | From reports |
| M1 susceptibility (real labels) | PR-AUC against prevalence, ROC-AUC, Brier under spatial block and leave-one-event-out | PR-AUC at least twice the prevalence | From reports |
| M3 hazard | Reliability, Brier, calibration error, dry-day maximum | Dry-day H below 0.05 for every ward (hard check) | From reports |
| Flood mapping | IoU, precision, recall against observed extents; compared with trivial baselines | Report; must state whether it beats the historical-frequency baseline | From reports |
| Operational | False alarm ratio, missed-event rate, lead time | Recall at least 0.8 for HIGH or above on backtests; false alarm ratio at most 0.5 in the prototype | From reports |
| System | Assessment latency per ward; tick for a 15-ward AOI; alert latency; data freshness; sensor availability | At most 5 s; at most 60 s; risk to PENDING\_REVIEW at most 10 s and approval to dispatch at most 5 s; median sensor data age at most 3 min; availability at least 90 percent excluding injected faults | From metrics |
| Explainability | Evidence completeness, factual consistency, traceability | 100 percent in tests | From tests |

### 32.2 Protocols

- Forecasting: scenario-level holdout; compare with persistence, linear rate and ridge; report by horizon, by storm intensity and under injected faults.
- M1: spatial block cross-validation (2 km blocks) and leave-one-event-out; labels are positive-unlabeled, so negatives are confident negatives only (cells never flagged and more than 500 m from any flag); report PR-AUC and calibration and map the residuals.
- M3 and levels: ward-hour backtests on 2015, 2020, 2021 and 2023 with leave-one-event-out calibration; state the label caveats from §12.1.
- Footprint: IoU, precision and recall against observed extents, and against two baselines: a thresholded historical-frequency map and all low-lying cells. If the footprint does not beat them, report that.
- Sensitivity: the Monte Carlo test of §12.5. Calibration drift: tracked per rolling window from outcomes.
- Reporting: scripts/backtest.py writes reports/metrics.json and reports/EVALUATION.md. Every metric carries a label (real, backtest, synthetic-validation) and a sample size, and the Model Performance view reads that file. Synthetic-validation numbers are never quoted as real-world skill.

## 33. MVP Architecture

### 33.1 What the MVP contains

Public datasets; historical flood labels; rainfall and forecast ingestion; terrain; drainage; the geospatial engine; M1 susceptibility, M2 forecaster and the M3 hazard function; the risk engine; six agents on one LangGraph graph; explainability with evidence; the dashboard and citizen view; the simulated sensor stream; simulated alert delivery; the real approval screen (with an optional demo autopilot that calls the same API); and the continuous-learning demonstration. Topology: §4.3.

### 33.2 MVP definition of done

- The 16-step storyline of §37 runs from `make demo` on a clean checkout, deterministically, twice in a row.
- Tests T01 to T20 pass; the evaluation report exists with labelled metrics.
- It runs with the network off using the prepared data bundle.
- LIMITATIONS.md states every simulation and every unverified dataset.
- Section 41 lists what must not be built.

## 34. Production Architecture

| Concern | MVP | Production |
| --- | --- | --- |
| Sensors and transport | Simulated, HTTP ingestion | Radar or ultrasonic level sensors over LoRaWAN or NB-IoT through an edge gateway; MQTT with TLS and per-device certificates; Kafka for durable streams and a schema registry; device management and calibration schedules |
| Stream processing | APScheduler ticks | Windowed consumers on Kafka; Flink or Spark only if volume demands |
| Storage | One PostgreSQL with PostGIS | Managed highly available PostgreSQL with point-in-time recovery, TimescaleDB for telemetry, read replicas, S3-compatible object storage |
| Model serving | In-process | Containerised model service with canary releases; feature store (for example Feast) once several consumers exist; GPUs only if deep learning is adopted on real data |
| Orchestration | Compose | Kubernetes with Helm, autoscaling, Argo CD; Prefect or CronJobs for batch |
| Routing | OSMnx and NetworkX | OSRM or GraphHopper with live closure and traffic feeds, agreed with traffic police |
| Integrations | None | GCC control room, TN SDMA, NDMA (CAP through the official platform after onboarding), IMD (API and radar QPE access), CMWSSB reservoir feeds, INCOIS tide and surge, hospital and shelter capacity registry, licensed SMS gateway with DLT registration, authority-operated cell broadcast, IVR provider |
| Security | JWT, seeded roles | OIDC with multi-factor authentication for approvers, network segmentation, WAF, secrets manager, penetration test, DPDP compliance, audit retention policy |
| Resilience | Single machine | Multi-zone deployment, tested degraded modes, agreed recovery objectives, chaos exercises |
| Observability | Logs, /metrics, optional Grafana | Prometheus, Grafana, Loki, tracing, service-level objectives for alert latency and data freshness, on-call rota |
| Model and threshold governance | Candidate, gate, administrator approval | Independent hydrological validation, change control with authority sign-off for any threshold, periodic recalibration, incident reviews |
| Science | Statistical and ML models, indicative footprints | Radar nowcasting, calibrated 1D/2D hydraulic models (SWMM, HEC-RAS or coupled) for priority basins, tide and surge coupling, measured drain capacity and blockage data, ensemble forecasts, sensor data assimilation |

## 35. Implementation Roadmap

Assume four to six engineers (backend, geospatial and data, ML, frontend, DevOps and QA). Critical path: P0, P2, P3, P4, P8, P9, P12, P15. Parallel tracks: the frontend can start in P2 against a mock server, the simulator (P6) runs alongside P4 and P5. Sizes: S small, M medium, L large.

### Phase 0 — Repository initialisation (S)

- Goal: anyone can clone the repo and run make test.
- Inputs: this manual. Depends on: none.
- Outputs: the tree of §24, pyproject and lockfile, Makefile, docker/, compose with the database only, CI, pre-commit, .env.example, docs stubs.
- Tasks: settings, Clock, logging, errors; ruff, mypy, import-linter; CI with a PostGIS service container.
- Tests: import smoke test; settings validation. Done when: make setup and make test pass on a clean machine and CI is green.

### Phase 1 — Chennai datasets (M)

- Goal: every MVP layer downloaded, checksummed and documented.
- Inputs: datasets.yaml, Earthdata account. Depends on: P0.
- Outputs: data/raw, data/manifest.yaml, docs/DATA.md, scripts/fetch\_data.py.
- Tasks: D01 and D08 to D18 first; IMERG and Open-Meteo samples; record licences; choose the DEM route (§6.4); record what is blocked (radar, capacities).
- Tests: manifest completeness and hash match; 200 wards. Done when: DATA.md lists real, simulated and missing status per dataset.

### Phase 2 — Database and PostGIS (S)

- Goal: schema deployed with repositories and seeds.
- Depends on: P0. Outputs: 0001\_baseline.sql, Alembic revision, engine, repositories, build\_db.py, seeds for six roles and data\_sources.
- Tasks: apply §7; load wards; trigger and constraint checks.
- Tests: migration up and down; SRID and CHECK constraints; geom\_utm trigger; T19. Done when: make db loads 200 valid wards.

### Phase 3 — Geospatial preprocessing (L)

- Goal: grid, terrain, drainage, exposure and static ward features.
- Depends on: P1, P2. Outputs: build\_grid, build\_terrain, build\_static\_features, build\_roads\_graph; grid\_cells, terrain\_features (without S), population\_grids, buildings, roads, facilities, shelters, zone\_static\_features, coverage flags.
- Tasks: §8.3 pipeline; zonal statistics; load drains; population; buildings; graph build.
- Tests: §8.5. Done when: geospatial tests pass and a QGIS check of grid, HAND and sinks looks right around the Adyar and Velachery.

### Phase 4 — Historical flood pipeline and M1 (L)

- Goal: labelled events and the susceptibility model.
- Depends on: P3. Outputs: historical\_flood\_events, flood\_extents, flood\_incidents, geo/history.py, train\_susceptibility.py, M1 in the registry, S and hist\_freq on cells, ward aggregates, E and V.
- Tasks: load OpenCity KML labels; derive Sentinel-1 masks for 2015, 2021, 2023 (urban caveat); confident-negative labelling; spatial CV; calibration; E and V per §12.3.
- Tests: label QC notebook; vintage rule; metric report with labels. Done when: M1 is STAGING with a model card and the S map has been reviewed by a person.

### Phase 5 — Rainfall and forecast pipeline (M)

- Goal: ingestion with fallbacks, plus replay.
- Depends on: P2 (P3 for ward mapping). Outputs: adapters (openmeteo, imerg, imd\_grid, replay), validators, POST /data/rainfall, stations, hyetograph builder, DEMO-STORM-01 definition.
- Tasks: adapters and fallback chain; deduplication; IMERG samples for the 2015 and 2023 events.
- Tests: T14; timezone tests; failure of each adapter. Done when: a week of IMERG and one Open-Meteo forecast are stored and the replay storm enters through the API.

### Phase 6 — Sensor simulator (M)

- Goal: 50 SIM sensors with faults posting to the API.
- Depends on: P2, P3, P5. Outputs: simulation/\*, place\_sensors.py, sensors in the database, POST /data/water-level with validator, SimClock.
- Tasks: §9.5 placement, behaviour and faults; tune alpha0, beta, tau to the storyline; truth injection.
- Tests: T02, T15, fault detection; the timeline acceptance test (warn at about T+25 to 30, critical at about T+40 to 45). Done when: the hero ward follows the storyline and the validator flags every injected fault.

### Phase 7 — Forecasting model M2 (M)

- Goal: M2 trained, evaluated, registered, with baselines.
- Depends on: P5, P6. Outputs: features/*, models/forecast/*, the 400-scenario generator, train\_forecaster.py, exceed.py, registry entry, labelled metrics.
- Tests: T13; scenario holdout; reliability; baseline comparison. Done when: the report shows whether M2 beats persistence at 30 and 60 min on held-out scenarios. If it does not, investigate before moving on.

### Phase 8 — Risk engine (M)

- Goal: H, E, V, I, R, matrix, floors, confidence, footprint.
- Depends on: P4, P7. Outputs: models/hazard/*, risk/*, geo/footprint.py, risk.yaml and config\_versions, calibrate\_hazard.py, prediction writer.
- Tests: T04, T05, T06, property tests, dry-day check, sensitivity run, replay\_prediction. Done when: all AOI wards are assessed each tick and dry-day H stays below 0.05.

### Phase 9 — Agent system (M)

- Goal: six agents, orchestrator and the LangGraph graph.
- Depends on: P5 to P8. Outputs: agents/\*, tool wrappers that write tool\_calls, agent\_runs.
- Tests: agent tests (valid, missing, contradictory, tool failure, abstention), T17, routing tests, parity between the graph and SequentialRunner. Done when: POST /risk/analyze runs end to end for a ward.

### Phase 10 — Explainability (M)

- Goal: drivers, evidence, similarity, templates, verifier, optional LLM.
- Depends on: P8, P9. Outputs: explain/\*, kb seeds, LLM client and guard.
- Tests: T07, T12, evidence completeness, template snapshots, guard fuzzing. Done when: every risk has drivers with evidence and the system works with LLM\_MODE off or template.

### Phase 11 — Decision engine (S)

- Goal: policy rules, actions, alert drafts, i18n.
- Depends on: P10. Outputs: decision/\*, alerts/drafting.py, policy.yaml, English and Tamil templates (Tamil reviewed by a native speaker).
- Tests: rule table per level and confidence; hard checks (§19.3). Done when: HIGH and VERY\_HIGH produce the right drafts and MEDIUM an internal advisory.

### Phase 12 — Human approval (M)

- Goal: state machine, review API, audit chain, simulated dispatch.
- Depends on: P11, P2. Outputs: state\_machine, dispatcher, simulated adapters, alert routers, human\_reviews, audit writer, verify\_audit.py, RBAC.
- Tests: T08 to T11, T19, T20, transition matrix, double-approve concurrency. Done when: the approval flow works through the API and the audit chain verifies.

### Phase 13 — Routing and shelters (M)

- Goal: risk-aware routes to safe shelters.
- Depends on: P3, P8, P11. Outputs: routing/\*, graph files, GET /routes and /shelters.
- Tests: T16; route validity; under 3 s per request. Done when: routes for the hero ward render and the unverified fallback works.

### Phase 14 — Dashboard (L)

- Goal: the 13 views and the citizen view.
- Depends on: API shapes from P2 (start early with a mock server). Outputs: web/\*, generated API types, i18n, SimBadge and DegradedBanner.
- Tests: component tests; Playwright smoke (login, overview, review, approve). Done when: every view renders live data and role gating works.

### Phase 15 — End-to-end integration (M)

- Goal: the storyline with scheduler and simulation clock.
- Depends on: P6 to P14. Outputs: worker/\*, demo router, run\_demo.py, scenario files, make demo.
- Tests: e2e storyline (includes T09), T18. Done when: the scripted run reproduces the §37 timeline twice in a row.

### Phase 16 — Testing and evaluation (M)

- Goal: full suite, backtests, evaluation report.
- Depends on: all. Outputs: tests/*, backtest.py, reports/*, model cards, final LIMITATIONS.md.
- Tests: coverage targets, sensitivity, leakage suite. Done when: CI is green and the labelled metrics are generated with known issues listed.

### Phase 17 — Demo hardening (S)

- Goal: survive a live demo.
- Depends on: P15, P16. Outputs: data bundle, optional offline basemap, recorded fallback video, DEMO.md runbook, rehearsal log; optional MQTT bridge as a stretch.
- Tasks: three dry runs on the demo machine; kill-switch tests (LLM off, network off, sensor outage); freeze dependencies; prepare answers on limitations.
- Tests: the chaos checklist in §39. Done when: three consecutive clean offline rehearsals and a recorded fallback exist.

## 36. Code Skeletons

### 36.1 Implementation order and dependencies

Do not generate thousands of lines at once. Build in this order, defining interfaces before implementations.

| Order | Files | Why here |
| --- | --- | --- |
| 1 | core/settings, clock, timeutil, errors, hashing | Everything depends on them; time and Clock rules must exist before any data code |
| 2 | db/engine, repositories | The persistence boundary |
| 3 | agents/contracts | The shapes every module exchanges; written before the modules (§14) |
| 4 | ingestion/base (protocols), validators, adapters | Data in |
| 5 | simulation/\* | Produces test data for steps 6 to 9 |
| 6 | geo/\* scripts and features/\* | Model inputs |
| 7 | models/*, risk/* | The numbers |
| 8 | explain/*, decision/*, alerts/*, routing/* | Meaning and action |
| 9 | agents/graph, orchestrator, agents | Wiring (§15) |
| 10 | api/*, worker/* | Exposure |
| 11 | web/\* | Can start at step 3 against a mock server |

Interfaces to define first: Clock; RainfallAdapter; ChannelAdapter; the ForecastModel protocol (predict returns P10, P50, P90 per horizon); RiskConfig (parsed risk.yaml); the contracts of §14; repository function signatures. Agent contracts are in §14 and the LangGraph workflow is in §15; this section covers the remaining critical components. The skeletons are representative and untested; complete them with the tests of each roadmap phase.

### 36.2 Settings, Clock and time helpers

```python
# src/ewf/core/settings.py
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_env: str = 'development'
    app_mode: str = 'replay'
    database_url: str
    jwt_secret: str
    jwt_expires_min: int = 60
    allow_live_dispatch: bool = False
    llm_mode: str = Field('template', pattern='^(off|template|llm)$')
    data_dir: str = 'data'
    config_dir: str = 'config'


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# src/ewf/core/clock.py  (every time-dependent component calls clock.now())
from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimClock:
    # simulated time advances speed simulated seconds per real second while running
    def __init__(self, t0: datetime, speed: float = 60.0):
        assert t0.tzinfo is not None, 't0 must be timezone-aware'
        self._base_sim, self._speed, self._running = t0, speed, False
        self._base_real = datetime.now(timezone.utc)

    def start(self) -> None:
        self._base_real, self._running = datetime.now(timezone.utc), True

    def pause(self) -> None:
        self._base_sim, self._running = self.now(), False

    def set_speed(self, speed: float) -> None:
        self._base_sim, self._base_real, self._speed = self.now(), datetime.now(timezone.utc), speed

    def jump(self, to: datetime) -> None:
        self._base_sim, self._base_real = to, datetime.now(timezone.utc)

    def now(self) -> datetime:
        if not self._running:
            return self._base_sim
        elapsed = (datetime.now(timezone.utc) - self._base_real).total_seconds()
        return self._base_sim + timedelta(seconds=elapsed * self._speed)
```

```python
# src/ewf/core/timeutil.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def to_utc(ts: datetime | str, source_tz: str | None = None) -> datetime:
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)          # accepts offsets and Z on Python 3.11+
    if ts.tzinfo is None:
        if source_tz is None:
            raise ValueError('naive timestamp without a declared source_tz')
        ts = ts.replace(tzinfo=ZoneInfo(source_tz))
    return ts.astimezone(timezone.utc)
```

### 36.3 PostGIS connection and repositories

```python
# src/ewf/db/engine.py
from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from ewf.core.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_size=10, max_overflow=10, pool_pre_ping=True)


def check_postgis() -> str:
    with get_engine().connect() as conn:
        return conn.execute(text('SELECT postgis_version()')).scalar_one()
```

```python
# src/ewf/db/repositories/zones.py and rainfall.py
import geopandas as gpd
from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from ewf.db.engine import get_engine

_meta = MetaData()


def _table(name: str) -> Table:
    return Table(name, _meta, autoload_with=get_engine())      # reflected once per process


def load_wards_utm() -> gpd.GeoDataFrame:
    sql = 'SELECT zone_id, ward_no, ward_name, geom_utm AS geom FROM zones'
    return gpd.read_postgis(sql, get_engine(), geom_col='geom', crs='EPSG:32644')


def zone_for_point(lon: float, lat: float) -> str | None:
    sql = text('SELECT zone_id FROM zones WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))')
    with get_engine().connect() as conn:
        return conn.execute(sql, {'lon': lon, 'lat': lat}).scalar_one_or_none()


def insert_rainfall(rows: list[dict]) -> int:
    # one multi-row INSERT, idempotent on the natural key; returns rows actually inserted
    if not rows:
        return 0
    stmt = pg_insert(_table('rainfall_observations')).values(rows).on_conflict_do_nothing(
        index_elements=['station_id', 'observed_at', 'interval_minutes'])
    with get_engine().begin() as conn:
        return conn.execute(stmt).rowcount
```

### 36.4 FastAPI application, errors, RBAC and one router

```python
# src/ewf/core/errors.py
class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.details = code, message, status, details or {}
```

```python
# src/ewf/api/main.py
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from ewf.api.routers import alerts, auth, data, health, risk, zones
from ewf.core.errors import AppError
from ewf.core.settings import get_settings


def create_app() -> FastAPI:
    s = get_settings()
    prod = s.app_env == 'production'
    app = FastAPI(title='Chennai EWF', version='1.0.0',
                  docs_url=None if prod else '/docs', openapi_url=None if prod else '/openapi.json')
    app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:8080'],
                       allow_methods=['*'], allow_headers=['*'])

    @app.middleware('http')
    async def request_id(request: Request, call_next):
        rid = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.state.request_id = rid
        response = await call_next(request)
        response.headers['X-Request-ID'] = rid
        return response

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        body = {'error': {'code': exc.code, 'message': exc.message, 'details': exc.details,
                          'request_id': getattr(request.state, 'request_id', None)}}
        return JSONResponse(status_code=exc.status, content=body)

    for r in (auth.router, health.router, data.router, zones.router, risk.router, alerts.router):
        app.include_router(r, prefix='/api/v1')
    if not prod:
        from ewf.api.routers import demo            # demo control is never mounted in production
        app.include_router(demo.router, prefix='/api/v1')
    return app


app = create_app()
```

```python
# src/ewf/api/rbac.py
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ewf.core.errors import AppError
from ewf.core.settings import get_settings

bearer = HTTPBearer(auto_error=False)


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if cred is None:
        raise AppError('UNAUTHENTICATED', 'missing bearer token', 401)
    try:
        claims = jwt.decode(cred.credentials, get_settings().jwt_secret, algorithms=['HS256'])
    except jwt.PyJWTError as exc:
        raise AppError('UNAUTHENTICATED', 'invalid or expired token', 401) from exc
    return {'user_id': claims['sub'], 'role': claims['role']}


def require(*roles: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        role = user['role']
        if role not in roles:
            raise AppError('FORBIDDEN', f'role {role} may not do this', 403)
        return user
    return dep
```

```python
# src/ewf/api/routers/alerts.py  (the approval endpoint; other routers follow the same pattern)
from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ewf.alerts import service
from ewf.api.rbac import require

router = APIRouter(prefix='/alerts', tags=['alerts'])


class ApproveBody(BaseModel):
    evidence_opened: bool
    acknowledged_low_confidence: bool = False
    comment: str | None = None
    modifications: dict | None = None
    severity_override: str | None = Field(None, pattern='^(MEDIUM|HIGH|VERY_HIGH)$')


@router.post('/{alert_id}/approve')
def approve(alert_id: UUID, body: ApproveBody,
            user: dict = Depends(require('municipal_operator', 'emergency_coordinator'))):
    # service.approve checks severity authority, status, expiry, prediction freshness and
    # acknowledgements; applies modifications; transitions to APPROVED; dispatches; audits; returns the alert
    return service.approve(alert_id, reviewer=user, **body.model_dump())
```

### 36.5 Rainfall ingestion

```python
# src/ewf/ingestion/base.py
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol


@dataclass(frozen=True)
class RainfallRecord:
    station_id: str
    observed_at: datetime          # END of the interval, UTC, timezone-aware
    interval_minutes: int
    rain_mm: float
    source: str


class RainfallAdapter(Protocol):
    name: str

    def fetch(self, station_id: str, lat: float, lon: float,
              start: datetime, end: datetime) -> Iterable[RainfallRecord]: ...
```

```python
# src/ewf/ingestion/validators.py
from datetime import datetime, timedelta
from ewf.ingestion.base import RainfallRecord

ALLOWED_INTERVALS = {5, 10, 15, 30, 60, 1440}


def validate_rainfall(rec: RainfallRecord, now: datetime) -> str | None:
    # returns a rejection reason, or None when the record is acceptable
    if rec.observed_at.tzinfo is None:
        return 'NAIVE_TIMESTAMP'
    if rec.observed_at > now + timedelta(seconds=120):
        return 'FUTURE_TIMESTAMP'
    if rec.interval_minutes not in ALLOWED_INTERVALS:
        return 'BAD_INTERVAL'
    if not 0.0 <= rec.rain_mm <= 400.0:
        return 'OUT_OF_RANGE'
    return None
```

```python
# src/ewf/ingestion/adapters/openmeteo.py
import time
from datetime import datetime, timezone
import httpx
from ewf.ingestion.base import RainfallRecord


class OpenMeteoAdapter:
    name = 'openmeteo'

    def __init__(self, client: httpx.Client | None = None,
                 base_url: str = 'https://api.open-meteo.com/v1/forecast'):
        self.client, self.base_url = client or httpx.Client(timeout=10.0), base_url

    def fetch(self, station_id, lat, lon, start, end):
        # hourly precipitation is the sum of the preceding hour, so the timestamp is the interval end
        params = {'latitude': lat, 'longitude': lon, 'hourly': 'precipitation',
                  'timezone': 'UTC', 'past_days': 2, 'forecast_days': 3}
        for attempt, delay in enumerate((1, 2, 4)):
            try:
                resp = self.client.get(self.base_url, params=params)
                resp.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(delay)
        hourly = resp.json()['hourly']
        if len(hourly['time']) != len(hourly['precipitation']):
            raise ValueError('hourly arrays differ in length')
        for stamp, mm in zip(hourly['time'], hourly['precipitation']):
            if mm is None:
                continue                                   # missing stays missing
            valid_at = datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)   # declared source tz: UTC
            if start < valid_at <= end:
                yield RainfallRecord(station_id, valid_at, 60, float(mm), self.name)
```

Use the adapter for rainfall\_forecasts when valid\_at is after the issue time, and for the recent-hours fallback (stored with quality\_flag SUSPECT) otherwise.

```python
# src/ewf/ingestion/service.py
from datetime import datetime
from ewf.db.repositories import ingestion as repo
from ewf.ingestion.validators import validate_rainfall


def ingest_rainfall(records, source_id: str, adapter: str, now: datetime) -> dict:
    run_id = repo.start_run(source_id, adapter)
    good, rejected = [], []
    for rec in records:
        reason = validate_rainfall(rec, now)
        if reason:
            payload = {**rec.__dict__, 'observed_at': rec.observed_at.isoformat()}
            rejected.append({'reason': reason, 'payload': payload})
        else:
            good.append({'station_id': rec.station_id, 'observed_at': rec.observed_at,
                         'interval_minutes': rec.interval_minutes, 'rain_mm': rec.rain_mm,
                         'source': rec.source, 'quality_flag': 'OK', 'run_id': run_id})
    inserted = repo.insert_rainfall(good)
    repo.reject_records(run_id, rejected)
    repo.finish_run(run_id, rows_in=len(good) + len(rejected), rows_ok=inserted, rows_rejected=len(rejected))
    return {'run_id': str(run_id), 'accepted': inserted, 'duplicates': len(good) - inserted, 'rejected': len(rejected)}
```

### 36.6 Sensor simulator

```python
# src/ewf/simulation/sensor_model.py
from dataclasses import dataclass
import numpy as np


@dataclass
class SensorParams:
    sensor_id: str
    depth_cm: float = 120.0
    h0_cm: float = 5.0
    alpha: float = 0.055        # cm/min per mm/hr of effective rain
    beta: float = 0.015        # 1/min recession
    tau_min: float = 20.0
    blockage: float = 0.2      # hidden from the models
    kappa: float = 0.0         # tide coupling, 0 for inland wards
    noise_cm: float = 0.4

    @property
    def warn_cm(self) -> float:
        return 0.60 * self.depth_cm

    @property
    def critical_cm(self) -> float:
        return 0.85 * self.depth_cm


@dataclass
class SensorState:
    level_cm: float
    r_eff: float = 0.0


def step(p: SensorParams, s: SensorState, rain_mm_hr: float, tide_cm: float,
         dt_min: float, rng: np.random.Generator) -> tuple[float, bool]:
    s.r_eff += (dt_min / max(p.tau_min, dt_min)) * (rain_mm_hr - s.r_eff)
    inflow = p.alpha * s.r_eff
    outflow = p.beta * (1.0 - p.blockage) * max(s.level_cm - p.h0_cm, 0.0)
    s.level_cm = float(np.clip(s.level_cm + dt_min * (inflow - outflow), 0.0, 1.15 * p.depth_cm))
    reading = s.level_cm + p.kappa * tide_cm + rng.normal(0.0, p.noise_cm)
    reading = round(max(reading, 0.0), 1)                    # 0.1 cm quantisation
    return reading, s.level_cm >= p.depth_cm                 # reading, overtopping (truth only)
```

```python
# src/ewf/simulation/runner.py
from datetime import datetime, timedelta
import httpx
import numpy as np
from ewf.simulation.sensor_model import SensorParams, SensorState, step


def hyetograph(knots: list[tuple[float, float]]):
    # knots (minute, mm/hr) from the scenario YAML, linear between knots
    xs, ys = zip(*knots)
    return lambda minute: float(np.interp(minute, xs, ys))


def apply_faults(faults, sid, minute, reading, rng, loss_p=0.02):
    if rng.random() < loss_p:
        return None                                           # packet loss
    for f in faults:
        if f['sensor_id'] == sid and f['start_min'] <= minute < f['end_min']:
            if f['kind'] == 'outage':
                return None
            if f['kind'] == 'stuck':
                return f.setdefault('_held', reading)
            if f['kind'] == 'spike' and minute == f['start_min']:
                return reading + 150.0
            if f['kind'] == 'drift':
                return reading + 0.02 * (minute - f['start_min'])
    return reading


def run_scenario(scenario: dict, sensors: dict[str, SensorParams], api: httpx.Client,
                 t0: datetime, minutes: int, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    rain = hyetograph(scenario['rain_knots'])
    tide = hyetograph(scenario.get('tide_knots', [(0, 0.0), (minutes, 0.0)]))
    states = {sid: SensorState(level_cm=p.h0_cm) for sid, p in sensors.items()}
    faults = scenario.get('faults', [])
    for m in range(minutes):
        t = t0 + timedelta(minutes=m + 1)
        batch = []
        for sid, p in sensors.items():
            reading, _overtopping = step(p, states[sid], rain(m), tide(m), 1.0, rng)
            reading = apply_faults(faults, sid, m, reading, rng)
            if reading is not None:
                batch.append({'sensor_id': sid, 'timestamp': t.isoformat(), 'water_level_cm': reading,
                              'status': 'ONLINE', 'is_simulated': True})
        api.post('/api/v1/data/water-level', json={'readings': batch})
```

In replay mode the runner is paced by SimClock: it sleeps until the simulated minute is due, so a 60-minute storm plays in about a minute at the default speed. The overtopping flag is recorded in the simulation truth table and used only for outcome labelling, never sent to the API.

### 36.7 Feature engineering

```python
# src/ewf/features/leakage.py
class LeakageError(RuntimeError):
    pass


def assert_no_future(df, ts_col: str, as_of) -> None:
    if len(df) and df[ts_col].max() > as_of:
        raise LeakageError(f'{ts_col} contains data after as_of {as_of.isoformat()}')
```

```python
# src/ewf/features/rainfall.py
import numpy as np
import pandas as pd
from ewf.features.leakage import assert_no_future


def rainfall_features(obs: pd.DataFrame, as_of: pd.Timestamp) -> dict[str, float]:
    # obs: observed_at (UTC, end of interval), interval_minutes, rain_mm
    assert_no_future(obs, 'observed_at', as_of)
    feats: dict[str, float] = {}
    for w in (15, 30, 60, 180):
        win = obs[(obs.observed_at > as_of - pd.Timedelta(minutes=w)) & (obs.observed_at <= as_of)]
        feats[f'rain_{w}'] = float(win.rain_mm.sum()) if win.interval_minutes.sum() >= 0.8 * w else np.nan
    recent = obs[(obs.observed_at > as_of - pd.Timedelta(minutes=60)) & (obs.observed_at <= as_of)]
    intensity = recent.rain_mm * 60.0 / recent.interval_minutes
    feats['rain_int_now'] = float(intensity.iloc[-1]) if len(recent) else np.nan
    feats['rain_int_max_60'] = float(intensity.max()) if len(recent) else np.nan; feats['rain_hr_eq'] = float(np.fmax(feats['rain_60'], 4.0 * feats['rain_15']))
    for minutes, label in ((24 * 60, 'rain_ante_24h'), (72 * 60, 'rain_ante_72h')):
        win = obs[(obs.observed_at > as_of - pd.Timedelta(minutes=minutes + 60)) &
                  (obs.observed_at <= as_of - pd.Timedelta(minutes=60))]
        feats[label] = float(win.rain_mm.sum()) if len(win) else np.nan
    return feats
```

```python
# src/ewf/features/waterlevel.py
import numpy as np
import pandas as pd
from scipy.stats import theilslopes

WARN_RATIO = 0.60 / 0.85          # warn level over critical level for the default thresholds
_KEYS = ('level_cm', 'util', 'rise_5', 'rise_10', 'rise_accel', 'tt_critical_lin')


def _finite(x: float, default: float = 0.0) -> float:
    return x if np.isfinite(x) else default


def rise_rate(levels: pd.Series, as_of: pd.Timestamp, minutes: int, min_points: int = 4) -> float:
    # robust Theil-Sen slope in cm/min over (as_of - minutes, as_of]; levels indexed by UTC timestamp
    w = levels[(levels.index > as_of - pd.Timedelta(minutes=minutes)) & (levels.index <= as_of)].dropna()
    if len(w) < min_points:
        return float('nan')
    x = np.asarray((w.index - w.index[0]).total_seconds()) / 60.0
    return float(theilslopes(w.to_numpy(dtype=float), x)[0])


def sensor_features(levels: pd.Series, critical_cm: float, as_of: pd.Timestamp, max_age_min: int = 10) -> dict[str, float]:
    cur = levels[levels.index <= as_of].dropna()
    if cur.empty or (as_of - cur.index[-1]) > pd.Timedelta(minutes=max_age_min):
        return {k: float('nan') for k in _KEYS}
    level = float(cur.iloc[-1])
    r5, r10 = rise_rate(levels, as_of, 5), rise_rate(levels, as_of, 10)
    r10_prev = rise_rate(levels, as_of - pd.Timedelta(minutes=5), 10)
    tt = (critical_cm - level) / max(_finite(r10), 0.05)
    return {'level_cm': level, 'util': level / critical_cm, 'rise_5': r5, 'rise_10': r10,
            'rise_accel': r5 - r10_prev, 'tt_critical_lin': float(np.clip(tt, 0.0, 240.0))}


def ward_aggregate(per_sensor: list[dict[str, float]], conf: list[float]) -> dict[str, float]:
    ok = [(f, c) for f, c in zip(per_sensor, conf) if np.isfinite(f['util'])]
    if not ok:
        return {'n_healthy': 0.0, 'sensor_missing': 1.0}
    utils = np.array([f['util'] for f, _ in ok])
    rises = np.array([f['rise_10'] for f, _ in ok if np.isfinite(f['rise_10'])])
    return {'util_max': float(utils.max()), 'util_p75': float(np.percentile(utils, 75)),
            'rise_max': float(rises.max()) if rises.size else float('nan'),
            'frac_above_warn': float((utils >= WARN_RATIO).mean()),
            'n_healthy': float(len(ok)), 'sensor_conf_mean': float(np.mean([c for _, c in ok])),
            'sensor_missing': 0.0}
```

### 36.8 Forecasting model (M2) and exceedance

```python
# src/ewf/models/forecast/train.py
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

HORIZONS = (15, 30, 60, 120)
FEATURES = ['level_cm', 'util', 'level_lag_5', 'level_lag_10', 'level_lag_15', 'level_lag_30',
            'rise_5', 'rise_10', 'rise_accel', 'rain_15', 'rain_30', 'rain_60', 'rain_int_now',
            'rain_fcst_30', 'rain_fcst_60', 'tide_cm', 'depth_cm', 'imperv', 'catchment_ha']
MONOTONE = {'rain_15': 1, 'rain_30': 1, 'rain_60': 1, 'rain_int_now': 1,
            'rain_fcst_30': 1, 'rain_fcst_60': 1, 'rise_5': 1, 'rise_10': 1}
BASE = dict(n_estimators=800, learning_rate=0.03, num_leaves=31, min_child_samples=50,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=42,
            monotone_constraints=[MONOTONE.get(f, 0) for f in FEATURES], verbose=-1)


def make_xy(df: pd.DataFrame, horizon: int):
    # df: one row per (scenario, sensor, minute) on a regular 1-minute grid built from the fault-free
    # simulator output (faults are injected separately for robustness tests); hidden parameters excluded
    df = df.sort_values(['scenario_id', 'sensor_id', 'ts'])
    future = df.groupby(['scenario_id', 'sensor_id'])['level_cm'].shift(-horizon)
    y = future - df['level_cm']                                   # target: change in level
    keep = y.notna()
    return df.loc[keep, FEATURES], y[keep], df.loc[keep, ['scenario_id', 'sensor_id', 'ts', 'level_cm']]


def train_horizon(train: pd.DataFrame, val: pd.DataFrame, horizon: int) -> dict[str, lgb.LGBMRegressor]:
    xtr, ytr, _ = make_xy(train, horizon)
    xva, yva, _ = make_xy(val, horizon)
    models = {}
    for name, extra in (('p50', {'objective': 'regression_l1'}),
                        ('p10', {'objective': 'quantile', 'alpha': 0.1}),
                        ('p90', {'objective': 'quantile', 'alpha': 0.9})):
        m = lgb.LGBMRegressor(**BASE, **extra)
        m.fit(xtr, ytr, eval_set=[(xva, yva)],
              callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])
        models[name] = m
    return models


def evaluate(models, test: pd.DataFrame, horizon: int) -> dict:
    xte, yte, meta = make_xy(test, horizon)
    lvl = meta['level_cm'].to_numpy()
    truth = lvl + yte.to_numpy()
    pred = lvl + models['p50'].predict(xte)
    p10, p90 = lvl + models['p10'].predict(xte), lvl + models['p90'].predict(xte)
    mae, persist = float(np.mean(np.abs(pred - truth))), float(np.mean(np.abs(lvl - truth)))
    return {'horizon': horizon, 'mae_cm': mae, 'rmse_cm': float(np.sqrt(np.mean((pred - truth) ** 2))),
            'r2': float(r2_score(truth, pred)), 'persistence_mae_cm': persist, 'skill': 1.0 - mae / persist,
            'coverage_p10_p90': float(np.mean((truth >= p10) & (truth <= p90))),
            'label': 'synthetic-validation', 'n': int(len(yte))}


def save(models, horizon: int, out_dir: Path) -> None:
    for name, m in models.items():
        m.booster_.save_model(str(out_dir / f'h{horizon}_{name}.txt'))
```

```python
# src/ewf/models/forecast/exceed.py
import lightgbm as lgb
import numpy as np
import pandas as pd
from ewf.models.forecast.train import FEATURES


def exceed_prob(q10: float, q50: float, q90: float, thr: float) -> float:
    # piecewise-linear CDF through (q10, 0.1), (q50, 0.5), (q90, 0.9); tails extended by the nearer half-width
    q10, q50, q90 = (float(v) for v in np.sort([q10, q50, q90]))
    if q90 - q10 < 1e-6:
        return 1.0 if q50 >= thr else 0.0
    xs = [q10 - max(q50 - q10, 1e-3), q10, q50, q90, q90 + max(q90 - q50, 1e-3)]
    xs = [x + 1e-6 * i for i, x in enumerate(xs)]
    return float(np.clip(1.0 - np.interp(thr, xs, [0.0, 0.1, 0.5, 0.9, 1.0]), 0.0, 1.0))


def predict_sensor(boosters: dict[int, dict[str, lgb.Booster]], x: pd.DataFrame, level: float, critical_cm: float) -> dict:
    out = {}
    for h, b in boosters.items():
        d10, d50, d90 = (float(b[k].predict(x[FEATURES])[0]) for k in ('p10', 'p50', 'p90'))
        q10, q50, q90 = level + d10, level + d50, level + d90
        out[h] = {'p10_cm': q10, 'p50_cm': q50, 'p90_cm': q90, 'exceed_prob': exceed_prob(q10, q50, q90, critical_cm)}
    return out


def ward_exceedance(per_sensor: dict[int, list[float]]) -> tuple[dict[int, float], int | None]:
    # per_sensor[h] lists exceedance probabilities of the healthy sensors; use the mean of the two highest
    ward = {h: float(np.mean(sorted(p, reverse=True)[:2])) for h, p in per_sensor.items() if p}
    tti = next((h for h in sorted(ward) if ward[h] >= 0.5), None)
    return ward, tti
```

### 36.9 Hazard function and risk engine

```python
# src/ewf/models/hazard/function.py
import math
import numpy as np


def _scaled(name: str, spec: dict, feats: dict, static: dict) -> float | None:
    if name == 'low_elev':
        h = static.get('hand_p10')
        if h is None or not np.isfinite(h):
            return None
        return 1.0 - min(max(h / spec['hand_ref_m'], 0.0), 1.0)
    v = feats.get(name, feats.get(name + '_cm', static.get(name)))
    if v is None or not np.isfinite(v):
        return None
    return min(max(v / spec.get('scale', 1.0), 0.0), spec.get('clip', 1.0))


def hazard(feats: dict, static: dict, cfg: dict, variant: str | None = None) -> dict:
    spec = cfg['hazard']
    if variant:                                               # rain_static or sensor_static
        weights, intercept = spec[f'{variant}_variant']['weights'], spec[f'{variant}_variant']['intercept']
    else:
        weights, intercept = {k: s['weight'] for k, s in spec['features'].items()}, spec['intercept']
    terms, missing = {}, []
    for name, w in weights.items():
        fspec = spec['features'][name]
        if fspec.get('coastal_only') and not static.get('is_coastal'):
            terms[name] = (0.0, 0.0)
            continue
        x = _scaled(name, fspec, feats, static)
        if x is None:
            missing.append(name)
            x = 0.0
        terms[name] = (x, w * x)                              # (scaled value, contribution to z)
    z = intercept + sum(c for _, c in terms.values())
    b, t = spec['calibration']['shift_b'], spec['calibration']['temperature_t']
    return {'probability': 1.0 / (1.0 + math.exp(-(z - b) / t)), 'z': z, 'terms': terms,
            'missing': missing, 'variant': variant or 'full'}
```

```python
# src/ewf/risk/engine.py
from bisect import bisect_right
import numpy as np

LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']


def impact_index(e: float, v: float, w_e: float = 0.5, w_v: float = 0.5) -> float:
    return (w_e * e + w_v * v) / (w_e + w_v)


def risk_index(h: float, i: float, gamma: float = 0.6) -> float:
    return h * ((1.0 - gamma) + gamma * i)                    # never exceeds h


def matrix_level(h: float, i: float, m: dict) -> int:
    return m['table'][bisect_right(m['hazard_edges'], h)][bisect_right(m['impact_edges'], i)]


def apply_floors(level: int, sensors: list[dict], rain_hr_eq: float | None, conf_low: bool) -> tuple[int, list[str]]:
    rules: list[str] = []
    if any(s['util'] >= 1.0 for s in sensors) and level < (1 if conf_low else 2):
        level, rules = (1 if conf_low else 2), rules + ['R-FLOOR-1']
    if level < 1 and any(s['util'] >= 0.9 and np.isfinite(s['rise_10']) and s['rise_10'] >= 0.5 for s in sensors):
        level, rules = 1, rules + ['R-FLOOR-2']
    if level < 1 and rain_hr_eq is not None and rain_hr_eq >= 100.0:
        level, rules = 1, rules + ['R-FLOOR-3']
    return level, rules                                       # floors only ever raise the level


def overall_confidence(c: dict[str, float], cfg: dict) -> tuple[float, str]:
    w = cfg['confidence']['weights']
    score = float(np.prod([max(c[k], 1e-6) ** w[k] for k in w]))
    if min(c.values()) < cfg['confidence']['hard_floor']:
        return score, 'LOW'
    lv = cfg['confidence']['levels']
    return score, 'HIGH' if score >= lv['high'] else 'MEDIUM' if score >= lv['medium'] else 'LOW'


def assess(h: float, e: float, v: float, conf_level: str, sensors: list[dict], rain_hr_eq: float | None, cfg: dict) -> dict:
    i = impact_index(e, v, cfg['impact']['w_exposure'], cfg['impact']['w_vulnerability'])
    level = matrix_level(h, i, cfg['matrix'])
    level, floors = apply_floors(level, sensors, rain_hr_eq, conf_level == 'LOW')
    if conf_level == 'LOW':
        level = min(level, 1)                                 # cap at MEDIUM
    return {'impact_index': i, 'risk_index': risk_index(h, i, cfg['risk_index']['gamma']),
            'risk_level': LEVELS[level], 'floors_applied': floors, 'review_required': conf_level != 'HIGH'}
```

Property test (hypothesis) for monotonicity:

```python
from hypothesis import given, strategies as st


@given(h1=st.floats(0, 1), h2=st.floats(0, 1), i=st.floats(0, 1))
def test_level_is_monotone_in_hazard(h1, h2, i):
    lo, hi = sorted((h1, h2))
    assert matrix_level(lo, i, CFG['matrix']) <= matrix_level(hi, i, CFG['matrix'])
```

### 36.10 Explanation engine

```python
# src/ewf/explain/drivers.py
GROUP_LABEL = {'extreme_rainfall': 'extreme rainfall', 'rapid_water_rise': 'rapid water-level rise',
               'drainage_stress': 'drainage stress', 'terrain': 'terrain and susceptibility',
               'history_land_use': 'history and land use', 'tide': 'tide'}


def driver_shares(terms: dict, meta: dict, static_ref: dict) -> tuple[list[dict], list[dict]]:
    # terms[name] = (scaled value, contribution). Contributions are taken relative to a reference:
    # dynamic features at 0, static features at the city median in static_ref (already scaled)
    rows = []
    for name, (x, contrib) in terms.items():
        ref = static_ref.get(name)
        rel = contrib if ref is None else meta[name]['weight'] * (x - ref)
        rows.append({'name': name, 'group': meta[name]['group'], 'value': x, 'rel': rel})
    pos = [r for r in rows if r['rel'] > 0]
    total = sum(r['rel'] for r in pos) or 1.0
    groups: dict[str, float] = {}
    for r in pos:
        groups[r['group']] = groups.get(r['group'], 0.0) + r['rel']
    drivers = []
    for g, val in sorted(groups.items(), key=lambda kv: -kv[1]):
        share = 100.0 * val / total
        drivers.append({'group': g, 'label': GROUP_LABEL.get(g, g), 'share_pct': round(share, 1),
                        'impact_band': 'HIGH' if share >= 25 else 'MEDIUM' if share >= 10 else 'LOW',
                        'members': [r['name'] for r in pos if r['group'] == g]})
    return drivers, [r for r in rows if r['rel'] < 0]          # drivers, mitigating factors
```

```python
# src/ewf/explain/verifier.py  (entity allow-list check omitted in this skeleton)
import re

NUM = re.compile(r'\d+(?:\.\d+)?')
BANNED = ('will definitely', 'guaranteed', 'certain to', 'no doubt')


def verify_text(text: str, allowed_numbers: set[float], evidence_ids: set[str], claims: list[dict],
                max_words: int = 120) -> dict:
    problems = []
    for tok in NUM.findall(text):
        v = float(tok)
        if not any(abs(v - a) <= max(0.5, 0.01 * abs(a)) for a in allowed_numbers):
            problems.append(f'number not in evidence: {tok}')
    for c in claims:
        ids = set(c.get('evidence_ids', []))
        if not ids or not ids <= evidence_ids:
            snippet = str(c.get('text', ''))[:40]
            problems.append(f'claim without valid evidence: {snippet}')
    low = text.lower()
    problems += [f'certainty phrase: {p}' for p in BANNED if p in low]
    if len(text.split()) > max_words:
        problems.append('too long')
    return {'ok': not problems, 'problems': problems}


def _fmt(d: dict) -> str:
    return d['label'] + ' (' + format(d['share_pct'], '.0f') + '% of the risk)'


def render_template(level: str, ward: dict, prob: float, tti: int | None, conf: str,
                    drivers: list[dict], history: str, limitation: str) -> str:
    head = {'LOW': 'Monitor', 'MEDIUM': 'Prepare', 'HIGH': 'High flood risk', 'VERY_HIGH': 'Very high flood risk'}[level]
    when = f'within about {tti} minutes' if tti else 'in the coming hours'
    name, ward_no = ward['name'], ward['ward_no']
    top = '; '.join(_fmt(d) for d in drivers[:3])
    return (f'{head}: {name} (Ward {ward_no}). Estimated {prob * 100:.0f}% chance of flooding {when} '
            f'(confidence {conf}). Main reasons: {top}. {history} {limitation}').strip()
```

### 36.11 Alert engine

```python
# src/ewf/alerts/state_machine.py
from sqlalchemy import text
from ewf.core.errors import AppError
from ewf.db.repositories import audit

TRANSITIONS: dict[str, set[str]] = {
    'DRAFT': {'AI_GENERATED', 'CANCELLED'},
    'AI_GENERATED': {'PENDING_REVIEW', 'CANCELLED'},
    'PENDING_REVIEW': {'APPROVED', 'REJECTED', 'CHANGES_REQUESTED', 'EXPIRED', 'SUPERSEDED', 'CANCELLED'},
    'CHANGES_REQUESTED': {'SUPERSEDED', 'CANCELLED'},
    'APPROVED': {'DISPATCHED', 'EXPIRED', 'SUPERSEDED', 'CANCELLED'},
    'DISPATCHED': {'ACTIVE', 'CANCELLED'},
    'ACTIVE': {'RESOLVED', 'SUPERSEDED', 'CANCELLED'},
    'REJECTED': set(), 'RESOLVED': set(), 'EXPIRED': set(), 'SUPERSEDED': set(), 'CANCELLED': set(),
}
APPROVERS = {'MEDIUM': {'municipal_operator', 'emergency_coordinator'},
             'HIGH': {'municipal_operator', 'emergency_coordinator'},
             'VERY_HIGH': {'emergency_coordinator'}}


def transition(conn, alert_id, expected: str, new: str, actor: dict, meta: dict | None = None) -> None:
    if new not in TRANSITIONS[expected]:
        raise AppError('INVALID_TRANSITION', f'{expected} to {new} is not allowed', 409)
    res = conn.execute(text('''UPDATE alerts SET status = :new,
                               approved_at = CASE WHEN :new = 'APPROVED' THEN now() ELSE approved_at END,
                               dispatched_at = CASE WHEN :new = 'DISPATCHED' THEN now() ELSE dispatched_at END
                               WHERE alert_id = :id AND status = :old'''),
                       {'new': new, 'old': expected, 'id': alert_id})
    if res.rowcount != 1:                                      # optimistic concurrency: someone else changed it
        raise AppError('INVALID_TRANSITION', 'alert changed concurrently', 409)
    audit.write(conn, actor, 'alert.transition', 'alert', alert_id,
                before={'status': expected}, after={'status': new, **(meta or {})})
```

```python
# src/ewf/db/repositories/audit.py  (hash chain)
import hashlib
import json
from sqlalchemy import text


def write(conn, actor: dict, action: str, entity_type: str, entity_id, before=None, after=None, request_id=None) -> None:
    prev = conn.execute(text('SELECT hash FROM audit_logs ORDER BY audit_id DESC LIMIT 1 FOR UPDATE')).scalar_one_or_none() or ''
    entry = {'actor': actor, 'action': action, 'entity_type': entity_type, 'entity_id': str(entity_id),
             'before': before, 'after': after, 'request_id': request_id}
    digest = hashlib.sha256((prev + json.dumps(entry, sort_keys=True, default=str)).encode()).hexdigest()
    conn.execute(text('''INSERT INTO audit_logs (actor_type, actor_id, action, entity_type, entity_id,
                                                 before, after, request_id, prev_hash, hash)
                         VALUES (:at, :ai, :ac, :et, :ei, CAST(:b AS jsonb), CAST(:a AS jsonb), :rid, :ph, :h)'''),
                 {'at': 'USER', 'ai': str(actor.get('user_id', 'system')), 'ac': action, 'et': entity_type,
                  'ei': str(entity_id), 'b': json.dumps(before, default=str), 'a': json.dumps(after, default=str),
                  'rid': request_id, 'ph': prev, 'h': digest})
```

```python
# src/ewf/alerts/dispatcher.py
import random
import time
from typing import Protocol
from sqlalchemy import text
from ewf.core.errors import AppError


class ChannelAdapter(Protocol):
    name: str

    def send(self, alert: dict, recipient: dict) -> tuple[bool, str | None]: ...


class SimulatedSMS:
    name = 'SMS'

    def __init__(self, failure_rate: float = 0.0, seed: int = 42):
        self.failure_rate, self.rng = failure_rate, random.Random(seed)

    def send(self, alert: dict, recipient: dict) -> tuple[bool, str | None]:
        if self.rng.random() < self.failure_rate:
            return False, 'simulated gateway error'
        return True, None                                      # nothing leaves the machine


def dispatch(conn, alert: dict, recipients: list[dict], adapters: dict[str, ChannelAdapter],
             allow_live: bool, retry_delays=(0, 2, 4)) -> dict:
    if alert['mode'] == 'live' and not allow_live:
        raise AppError('LIVE_DISPATCH_DISABLED', 'live dispatch is disabled', 403)
    summary = {'sent': 0, 'failed': 0}
    for rec in recipients:
        ok, err = False, None
        for delay in retry_delays:
            time.sleep(delay)
            ok, err = adapters[rec['channel']].send(alert, rec)
            if ok:
                break
        conn.execute(text('''INSERT INTO alert_recipients (alert_id, subscriber_id, channel, status, attempts, sent_at, error)
                             VALUES (:a, :s, :c, :st, :n, now(), :e) ON CONFLICT DO NOTHING'''),
                     {'a': alert['alert_id'], 's': rec['subscriber_id'], 'c': rec['channel'],
                      'st': 'SIMULATED_SENT' if ok else 'FAILED', 'n': len(retry_delays), 'e': err})
        summary['sent' if ok else 'failed'] += 1               # fallback to the next channel is applied by the caller
    return summary
```

```python
# src/ewf/alerts/service.py  (approval, abbreviated)
from datetime import timedelta
from sqlalchemy import text
from ewf.alerts.state_machine import APPROVERS, transition
from ewf.core.errors import AppError
from ewf.db.engine import get_engine


def approve(alert_id, reviewer: dict, evidence_opened: bool, acknowledged_low_confidence: bool,
            comment=None, modifications=None, severity_override=None, clock=None, ttl_min: int = 30) -> dict:
    with get_engine().begin() as conn:
        a = conn.execute(text('SELECT * FROM alerts WHERE alert_id = :id FOR UPDATE'), {'id': alert_id}).mappings().one_or_none()
        if a is None:
            raise AppError('NOT_FOUND', 'alert not found', 404)
        severity = severity_override or a['severity']
        if reviewer['role'] not in APPROVERS[severity]:
            raise AppError('FORBIDDEN', 'this role may not approve this severity', 403)
        status = a['status']
        if status != 'PENDING_REVIEW':
            raise AppError('INVALID_TRANSITION', f'alert is {status}', 409)
        if str(a['created_by']) == str(reviewer['user_id']):
            raise AppError('FORBIDDEN', 'an author cannot approve their own draft', 403)
        if not evidence_opened:
            raise AppError('VALIDATION_ERROR', 'open the evidence panel before approving', 422)
        if a['low_confidence'] and not acknowledged_low_confidence:
            raise AppError('VALIDATION_ERROR', 'low-confidence acknowledgement required', 422)
        now = clock.now()
        if a['valid_until'] <= now:
            raise AppError('CONFLICT', 'alert has expired', 409)
        issued = conn.execute(text('SELECT issued_at FROM risk_predictions WHERE prediction_id = :p'),
                              {'p': a['prediction_id']}).scalar_one()
        if now - issued > timedelta(minutes=ttl_min):
            raise AppError('STALE_PREDICTION', 'prediction is stale; refresh the analysis', 409)
        # record human_reviews, apply and re-verify modifications, then:
        transition(conn, alert_id, 'PENDING_REVIEW', 'APPROVED', reviewer, {'comment': comment, 'override': severity_override})
        # dispatch(...) with simulated adapters, then DISPATCHED and ACTIVE transitions; return the final alert
    return {'alert_id': str(alert_id), 'status': 'APPROVED'}
```

## 37. Chennai End-to-End Demo

### 37.1 Scenario DEMO-STORM-01

A scripted, synthetic storm in the style of a north-east monsoon burst. It is not a reconstruction of a real event. T0 is the moment rainfall crosses 50 mm/hr (the PROTOTYPE threshold the proposal visuals use).

- Hyetograph knots, minutes from T0 and mm/hr, linear between knots: (-12, 4), (-6, 20), (0, 55), (4, 92), (14, 90), (30, 75), (45, 50), (60, 20), (80, 5), (120, 2). Antecedent 24 h rainfall: 30 mm (assumption). Forecast: the true shape times a bias of 0.8, no time shift, so the forecast under-predicts. Tide: none for the inland hero ward.
- Area: hero ward 112 (verify its GCC zone in the loaded boundary file; the Gemini guidebook places it in Zone 9, Teynampet), the AOI of at most 15 wards, 50 simulated sensors with at least 4 in the hero ward. Static inputs assumed for the reference run: S\_p90 0.72, HAND p10 0.9 m, history frequency 0.6, imperviousness 0.8, E 0.75, V 0.70.
- Tuned simulator values (from running the reference code of §36.6 for a nominal sensor: depth 120 cm, h0 5 cm, blockage 0.2): alpha0 0.055, beta 0.015, tau 20 min. Result: level 7.8 cm at T0; 33.6 cm at T+15, after a rise of 20.8 cm in the preceding 10 min; warn (72 cm) at T+29; critical (102 cm) at T+40; overtopping (120 cm) at T+48; peak rise about 2.9 cm/min. Per-sensor variation (blockage, imperviousness, catchment) moves these by several minutes. These supersede the starting values of §9.5.

Reference hazard trajectory (default priors; M2 exceedance replaced by a stand-in, so the real M2 will be noisier early on). Read the numbers on screen during the demo, not from this table.

| Minutes from T0 | rain\_hr\_eq (mm/hr) | H | Level |
| --- | --- | --- | --- |
| 0 | 18.9 | 0.08 | LOW |
| 5 | 41.9 | 0.20 | LOW |
| 10 | 67.5 | 0.48 | MEDIUM |
| 15 | 85.1 | 0.65 | HIGH |
| 20 | 89.7 | 0.73 | HIGH |
| 25 | 86.7 | 0.78 | HIGH |
| 30 | 82.5 | 0.81 | HIGH |
| 35 | 77.3 | 0.82 | HIGH |
| 40 | 70.9 | 0.81 | HIGH |
| 45 | 63.3 | 0.75 | HIGH |

With these inputs the level reaches HIGH at T+15, matching the proposal storyline, and time to impact is 30 min (the smallest horizon whose exceedance reaches 0.5). Dispatch at T+19 against critical level at about T+40 and overtopping at about T+48 gives a lead of roughly 21 and 29 minutes. VERY\_HIGH (H of 0.85 or more) is not reached; an optional DEMO-STORM-02 (peak 130 mm/hr, forecast bias 1.0) demonstrates that branch. If the real pipeline does not reach HIGH at about T+15, raise the storm intensity in the scenario file; do not tune the priors to flatter the demo.

### 37.2 The 16 steps

Simulation clock default: one simulated minute per real second (slow to one per 5 s for narration; pause at T+15 and T+18).

| Step | Sim time | What happens | Data and endpoints | On screen |
| --- | --- | --- | --- | --- |
| 1 Select Chennai | before start | City overview, clock paused | GET /zones, /risk, /health | 200 wards all LOW, SIM badge, mode replay |
| 2 Select the zone | before start | Open Ward 112 | GET /risk/W112, GET /sensors?zone\_id=W112 | Ward card, 4 or more SIM sensors, static features |
| 3 Load rainfall | start | Reset and start the scenario; worker ingests replay rainfall and the forecast | POST /demo/control, POST /data/rainfall, rainfall\_forecasts | Hyetograph with observed bars and forecast |
| 4 Rainfall intensifies | T-12 to T0 | Intensity crosses 50 mm/hr at T0 | GET /data/rainfall | Threshold marker on the hyetograph |
| 5 Sensor levels rise | T0 to T+10 | Simulator posts one batch per simulated minute; faults injected: a spike on one sensor at T+6 (flagged SUSPECT and excluded), an outage on another from T+8 to T+13 | POST /data/water-level | Water-level chart rising, grey sensor, flag icon |
| 6 Forecast continues the rise | T+10 | M2 bands cross the critical line at +30 and +60 | POST /forecast | Forecast chart with P10 to P90 band, time to impact |
| 7 Risk engine computes zone risk | T+10, T+15 | MEDIUM at T+10, HIGH at T+15 | POST /risk/analyze (tick) | Risk card: H, E, V, I, R, confidence components |
| 8 Map turns high risk | T+15 | Ward turns orange; indicative footprint with inner and outer envelope | GET /risk, GET /risk/W112 | Map, KPI strip updates |
| 9 RCA explains why | T+16 | Drivers with shares, evidence links, similar event | GET /explanations/{id} | Explainability panel with verified badge |
| 10 Decision agent proposes | T+17 | ISSUE\_ALERT, EVACUATION\_ROUTE, OPEN\_SHELTER x3, DEPLOY\_TEAM, NOTIFY\_AUTHORITY; alert in PENDING\_REVIEW | GET /alerts?status=PENDING\_REVIEW, GET /routes | Review queue entry |
| 11 Human approval | T+18 | Presenter opens the evidence panel, then approves (or an autopilot user does) | POST /alerts/{id}/approve | Review screen, approval confirmation |
| 12 Alert dispatched | T+19 | Simulated SMS, app and IVRS; alert ACTIVE; CAP export with status Exercise | approve response, GET /alerts/{id}/cap | Phone mockup, SIMULATED DELIVERY summary |
| 13 Routes calculated | T+19 | Three routes to safe shelters, one underpass blocked | GET /routes?alert\_id | Routes with safety scores |
| 14 Outcome loaded | T+45 to T+50 | Hero-ward sensors overtop; SIM\_TRUTH extent injected from the historical analog; outcome rows written | POST /outcomes | Predicted against observed on the map |
| 15 Prediction versus outcome | T+1 day (clock jump) | TP or FN, lead time, IoU, Brier score | GET /outcomes | Continuous Learning view |
| 16 Learning updates | T+1 day | Recalibration candidate evaluated against production; administrator promotes only if the gate passes | POST /models/{id}/promote | Model registry, accuracy-over-time chart (labelled) |

Supporting endpoints used here and not in the §23.2 table: GET /outcomes and GET /audit, with the same role rules as their POST or read counterparts.

### 37.3 Running the demo

- Day before: run make data (or unpack the data bundle), make db, make train, make seed; run the demo three times offline; record a fallback video.
- Manual mode is the recommended mode for judges: the presenter performs step 11, so human oversight is visible. The autopilot (scripts/run\_demo.py with the autopilot option) calls the same approve endpoint as demo\_operator and is labelled in the audit view.
- Narration rules: say simulated whenever sensors, delivery or truth appear; say decision support, not automatic warning; read values from the screen; never quote the proposal slides' numbers as results.
- Prepared honest answers: the sensors are simulated and a real gateway would use the same endpoint; flood footprints are indicative, not hydraulic; thresholds are prototype values pending the authorities; the model metrics are labelled synthetic-validation or backtest.

## 38. Deployment

### 38.1 Docker Compose (docker-compose.yml)

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: ewf
      POSTGRES_USER: ewf
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change-me}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: [CMD-SHELL, pg_isready -U ewf -d ewf]
      interval: 5s
      timeout: 3s
      retries: 20
    ports: ['5432:5432']
  api:
    build: {context: ., dockerfile: docker/api.Dockerfile}
    env_file: .env
    depends_on: {db: {condition: service_healthy}}
    volumes: ['./data:/app/data', './config:/app/config:ro']
    ports: ['8000:8000']
    command: uvicorn ewf.api.main:app --host 0.0.0.0 --port 8000
  worker:
    build: {context: ., dockerfile: docker/api.Dockerfile}
    env_file: .env
    depends_on: {db: {condition: service_healthy}, api: {condition: service_started}}
    volumes: ['./data:/app/data', './config:/app/config:ro']
    command: python -m ewf.worker.main
  simulator:
    build: {context: ., dockerfile: docker/api.Dockerfile}
    env_file: .env
    depends_on: [api]
    profiles: [demo]
    command: python scripts/run_demo.py --mode replay --api http://api:8000
  web:
    build: {context: ., dockerfile: docker/web.Dockerfile}
    depends_on: [api]
    ports: ['8080:80']
volumes:
  pgdata:
```

```dockerfile
# docker/api.Dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY src ./src
COPY scripts ./scripts
ENV PATH=/app/.venv/bin:$PATH PYTHONPATH=/app/src
```

web.Dockerfile is a two-stage build: node builds the Vite app, nginx serves the output and proxies /api to the api service. libgomp1 is required by LightGBM on Debian slim images.

### 38.2 Procedure

```text
cp .env.example .env            # set secrets
make setup                      # uv sync, pre-commit install, npm ci
make data                       # fetch and build layers (internet needed once) or unpack data-bundle.zip
docker compose up -d db api worker web
make db                         # alembic upgrade head, seeds
make train                      # M1, M2, hazard calibration; registers model versions
make seed                       # users, subscribers, scenarios, sensors
make demo                       # resets the scenario and starts the simulator and demo driver
```

### 38.3 Environments and sizing

- development: laptop, hot reload, APP\_ENV development. demo: Compose on the demo machine, APP\_ENV demo, no external calls required. production: not part of the MVP (§34).
- Demo machine: 4 vCPU, 8 GB RAM, 20 GB disk; 16 GB if the full-city routing graph is loaded.
- Fast restore: db/demo.dump (pg\_restore) plus the data bundle containing processed rasters, model artifacts and graph files, so the demo never depends on downloads.

## 39. Troubleshooting

### 39.1 Common problems

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Operation on mixed SRID geometries | A 4326 geometry meets a 32644 geometry | Use geom\_utm or ST\_Transform; never silence it with ST\_SetSRID |
| GeoPandas reports crs None or warns about CRS mismatch | Source file has no CRS | Confirm the CRS from the source documentation, set it explicitly, then to\_crs(32644) |
| Ward count is not 200 or cells have no ward | Invalid ward geometry or wrong CRS | make\_valid, check the boundary file and CRS, rebuild the grid |
| LightGBM fails to import (libgomp or libomp) | Missing OpenMP runtime | Install libgomp1 on Debian images; brew install libomp on macOS |
| KML reads as empty | The file has several layers | List layers (pyogrio.list\_layers), read each, explode multi-geometries |
| ArcGIS REST returns at most 1,000 features | Server maxRecordCount | Page with resultOffset and resultRecordCount, or by object ids |
| Earthdata 401 or 403 | Not logged in, or the GES DISC application is not authorised | earthaccess.login(); approve the application in the Earthdata profile |
| IMERG variable not found | Group or variable name differs by product version | Inspect the file with xarray or h5py and verify the precipitation variable in the Grid group |
| OSMnx slow or memory-hungry | Polygon too large | Restrict to AOI plus 5 km, enable the cache, simplify, save GraphML and load that |
| Timestamps off by 5 hours 30 min | Naive IST treated as UTC | Declare source\_tz and use to\_utc; the timezone tests catch it |
| Simulator timeline does not match the storyline | Wall-clock scheduling or wrong speed | Schedule on simulated minutes; check SimClock speed; retune alpha0, beta, tau in sensors.yaml |
| Duplicate alerts after a clock jump | Idempotency or supersede rule bypassed | Check the inputs\_hash key and the duplicate-suppression rule; test T18 |
| 409 STALE\_PREDICTION on approve | Prediction older than 30 min | Refresh the analysis; in replay keep the clock paused during review or raise the demo TTL |
| Browser CORS error | Origin not in the allow-list | Add the web origin to the CORS configuration |
| Graph or LangGraph API error after an upgrade | Version drift | Pin versions; run the parity test between the graph and SequentialRunner |
| The LLM guard rejects every text | Numbers formatted differently (0.8 against 80 percent) | Include both forms in allowed\_numbers; check the tolerance |
| Database not ready when the API starts | Start order | Use the healthcheck and depends\_on condition service\_healthy |
| Metrics look too good | Leakage or synthetic data | Check scenario-level splits, LeakageError tests and the metric label |

### 39.2 Chaos checklist before the demo

| Drill | Expected behaviour (§28) |
| --- | --- |
| Remove the LLM key or set LLM\_MODE off | Template explanations; nothing else changes |
| Disconnect the network | Replay mode continues; live feeds show unavailable |
| Kill the worker | Dashboard shows data ageing and a stale badge; restart resumes without duplicates |
| Silence half of the sensors | Degraded banner; confidence falls; risk still computed |
| Restart the database | API returns 503 for writes and stale reads; recovers on its own |
| Skew the system clock by 3 min | Sensor timestamps flagged; no future-dated rows accepted |
| Corrupt a model artifact | Checksum failure; fallback model; degraded banner |
| Delete the routing graph | Unverified straight-line shelters; no fabricated routes |
| Approve twice from two browsers | Second call returns 409 INVALID\_TRANSITION |
| Approve a stale draft | 409 STALE\_PREDICTION and a forced refresh |

## 40. Final Architecture Decision

These are decisions, not options.

- FINAL ARCHITECTURE: a twelve-layer modular monolith. One FastAPI application, one worker (ingestion, simulation driver, assessment tick), one React SPA. Six typed agents on one LangGraph assessment graph; deterministic tools produce every number; approval is a database state machine; dispatch is separate from the agents.
- FINAL STACK: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2 Core with psycopg2 and GeoAlchemy2, Alembic, APScheduler 3.x; PostgreSQL 16 with PostGIS 3.4; GeoPandas, Shapely 2, rasterio, rioxarray, pysheds, scipy, OSMnx 2.x, NetworkX; LightGBM, scikit-learn, SHAP; LangGraph (pinned); React 18, TypeScript, Vite, MapLibre GL JS, ECharts, TanStack Query, Zustand, Tailwind; Docker Compose; GitHub Actions; structlog and prometheus\_client.
- FINAL DATABASE: one PostgreSQL and PostGIS database with the 45 tables of §7; geom in 4326 plus geom\_utm in 32644 filled by trigger; plain tables for time series; JSONB for snapshots; full-text search for the knowledge base; append-only, hash-chained audit.
- FINAL DATA PIPELINE: adapters, validators with a dead-letter table, idempotent upserts, leak-free as\_of feature builders, models and engines, predictions stored with evidence. Rainfall chain: gauge, IMERG, Open-Meteo. Replay is the default demo mode. Static layers are built offline by scripts and loaded once.
- FINAL MODEL STRATEGY: M1 LightGBM susceptibility on real labels (spatial cross-validation, positive-unlabeled aware); M2 LightGBM quantile forecaster on simulated and replayed storms (labelled synthetic-validation) with persistence and linear baselines; M3 calibrated expert-prior logistic hazard function; a deterministic risk engine (hazard-gated impact, matrix, safety floors, confidence). No deep learning in serving and no numbers from an LLM.
- FINAL AGENT STRATEGY: the six agents and contracts of §13 and §14, the graph of §15; the LLM is optional (template by default), verified when used; abstention is a first-class outcome.
- FINAL GEOSPATIAL STRATEGY: wards as alert units, a 250 m grid for modelling, UTM 44N for all metric work, HAND-approx and sink depth as the primary terrain indices, indicative footprints constrained by history, routing on an OSMnx graph with risk-penalised costs.
- FINAL FRONTEND: React SPA with 13 operator views and a citizen view, polling, MapLibre, ECharts, a SIM badge and degraded banner, English and Tamil.
- FINAL DEPLOYMENT: Docker Compose on one machine with an offline data bundle and a simulation clock; CI on GitHub Actions.
- FINAL DEMO: Ward 112 with DEMO-STORM-01, the 16 steps of §37, manual approval by the presenter, honest labelling. The Velachery to Pallikaranai backtest is the secondary story.

Items to verify before relying on them (they are not decisions): the ward-to-GCC-zone mapping for Ward 112; OpenCity dataset formats and the GCC ArcGIS layer ids; the Copernicus DEM access route; IMD data access terms; Open-Meteo terms and rate limits; current LLM model names and prices; helpline numbers for alert text; reviewed Tamil wording; whether an MQTT bridge is worth including as a stretch.

## 41. What NOT to Build

| Do not build | Why | It becomes right when |
| --- | --- | --- |
| Kubernetes, Helm, service mesh | One machine and one team; adds failure modes | Production with several services and availability targets |
| Microservices | Module boundaries give separation without network failures | Independent teams or scaling needs |
| A Kafka cluster or stream processor | About 72,000 rows a day; HTTP and PostgreSQL are enough | Thousands of sensors and a need for durable replay |
| An MQTT broker in the critical path | A broker failing is a demo risk | Real sensor gateways exist (an optional bridge is a stretch) |
| Autonomous emergency actions | Safety, legal and ethical risk | Not without a statutory framework |
| Fake real-time integrations (NDMA, alerting platforms, GCC systems, IMD APIs) | Cannot be tested; claims would be dishonest | After formal onboarding or agreements |
| Extra LLM agents or LLM-steered control flow | Nondeterminism, cost, hallucination risk | Bounded text tasks with verifiers only |
| Numbers or forecasts produced by an LLM | An LLM is not a hydrological model | Never |
| Deep learning (LSTM, GRU, ConvLSTM, Transformer) in serving | No real sequential labels; synthetic data would be learned back | After one or two monsoons of real telemetry |
| Full hydraulic simulation in the runtime path | Cannot be calibrated or validated; drain capacities unpublished | Priority basins with surveyed data |
| Claims of real IoT hardware | Dishonest | Sensors are actually deployed |
| Real SMS, IVRS or CAP transmission | Would reach real people and needs regulatory registration | After approval and testing with the authority |
| A vector database | About 50 knowledge chunks; full-text search is enough | Knowledge base grows to thousands of chunks |
| A feature store, MLflow, DVC, Kubeflow | Three models and one team | Several maintainers and models |
| Native mobile apps or an embeddable widget | A responsive web view is enough | After a pilot |
| ML radar nowcasting | No radar QPE access | IMD radar data becomes available |
| GraphQL, websockets, SSE | Polling is adequate | Latency requirements demand it |
| Multi-city generalisation | Scope creep; validate one city first | After Chennai validation |
| Online or automatic learning | Unsafe in a warning workflow | Not without model governance |

## 42. Build Checklist

- [ ] Repository (§24, phase 0)
- [ ] Environment (.env, secrets, pre-commit, CI)
- [ ] Database (§7 applied, seeds loaded)
- [ ] Chennai GIS (200 wards, 250 m grid, coverage report)
- [ ] Rainfall ingestion (adapters, validators, endpoint, replay)
- [ ] Weather forecast (Open-Meteo, cache, fallback chain)
- [ ] DEM (access route chosen, terrain features built)
- [ ] Drainage (GCC drains loaded, per-ward coverage)
- [ ] Historical floods (labels, events, Sentinel-1 masks)
- [ ] Population (WorldPop with age structure)
- [ ] Buildings (Open Buildings)
- [ ] Roads (OSM graph and roads table)
- [ ] Shelters (loaded, capacity flags)
- [ ] Sensor simulator (50 SIM sensors, faults, tuned to the storyline)
- [ ] Forecast model (M2, baselines, labelled report)
- [ ] Risk model (M1, M3, engine, floors, config\_versions)
- [ ] Explainability (drivers, evidence, verifier)
- [ ] Agents (six agents and contracts)
- [ ] Orchestrator (graph, idempotency, SequentialRunner parity)
- [ ] Human approval (state machine, RBAC, audit chain verified)
- [ ] Alerts (drafting, simulated dispatch, CAP export)
- [ ] Routing (graph, costs, fallbacks)
- [ ] Dashboard (13 views and citizen view)
- [ ] Evaluation (labelled metrics, sensitivity run, backtests)
- [ ] Continuous learning (outcomes, candidate, promotion gate)
- [ ] Testing (T01 to T20, CI green)
- [ ] Docker (images, compose, data bundle, demo dump)
- [ ] Deployment (demo machine, offline run)
- [ ] Demo script (§37, three clean rehearsals, fallback video)
- [ ] LIMITATIONS.md, model cards and the data manifest complete
- [ ] Tamil templates reviewed by a native speaker
- [ ] Proposal deck corrected: risk arithmetic (§1.4) and the Team ID and Team Name placeholders on the title slide

## 43. Appendix — Schemas

### 43.1 Where the schemas live

- Database: the DDL in §7.2 to §7.4 is the single source of truth (45 tables). Pydantic contracts: §14. Configuration schemas: §25 and §45. Request and response models for the API are generated into OpenAPI from ewf.api.schemas.

### 43.2 Enumerations

| Enumeration | Values |
| --- | --- |
| Level | LOW, MEDIUM, HIGH, VERY\_HIGH |
| ConfidenceLevel | LOW, MEDIUM, HIGH |
| Prediction status | OK, DEGRADED, INSUFFICIENT\_EVIDENCE |
| Alert status | DRAFT, AI\_GENERATED, PENDING\_REVIEW, CHANGES\_REQUESTED, REJECTED, APPROVED, DISPATCHED, ACTIVE, RESOLVED, EXPIRED, SUPERSEDED, CANCELLED |
| Review decision | APPROVE, MODIFY\_APPROVE, REJECT, REQUEST\_CHANGES |
| Action type | MONITOR, PREPARE, ISSUE\_ALERT, OPEN\_SHELTER, EVACUATION\_ROUTE, DEPLOY\_TEAM, NOTIFY\_AUTHORITY, PRIORITISE\_FACILITY, ALLOCATE\_RESOURCE |
| Evidence kind | RAIN\_OBS, SENSOR\_OBS, FORECAST, TERRAIN\_STAT, DRAINAGE\_STAT, HISTORICAL\_EVENT, MODEL\_OUTPUT, RULE, KB\_CHUNK |
| Quality flag | OK, SUSPECT, BAD (rainfall also FILLED) |
| Roles | citizen, municipal\_operator, emergency\_coordinator, administrator, researcher, system\_service |
| Run mode | replay, backtest, live |
| Outcome label source | SENSOR, SAR, REPORT, SIM\_TRUTH, MANUAL |
| Model status | CANDIDATE, STAGING, PRODUCTION, RETIRED |
| Channel | DASHBOARD, SMS, APP, EMAIL, IVRS |
| Delivery status | QUEUED, SIMULATED\_SENT, RETRY, FAILED |

### 43.3 Ingestion payload schemas (JSON Schema)

```json
{
  "title": "RainfallBatch",
  "type": "object",
  "required": ["source", "records"],
  "properties": {
    "source": {"type": "string"},
    "records": {
      "type": "array", "maxItems": 5000,
      "items": {
        "type": "object",
        "required": ["station_id", "observed_at", "interval_minutes", "rain_mm"],
        "properties": {
          "station_id": {"type": "string"},
          "observed_at": {"type": "string", "format": "date-time"},
          "interval_minutes": {"enum": [5, 10, 15, 30, 60, 1440]},
          "rain_mm": {"type": "number", "minimum": 0, "maximum": 400}
        }
      }
    }
  }
}
```

```json
{
  "title": "SensorBatch",
  "type": "object",
  "required": ["readings"],
  "properties": {
    "readings": {
      "type": "array", "maxItems": 2000,
      "items": {
        "type": "object",
        "required": ["sensor_id", "timestamp", "water_level_cm"],
        "properties": {
          "sensor_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]+$"},
          "timestamp": {"type": "string", "format": "date-time"},
          "water_level_cm": {"type": "number", "minimum": 0, "maximum": 1000},
          "battery_percent": {"type": "number", "minimum": 0, "maximum": 100},
          "signal_dbm": {"type": "number"},
          "status": {"enum": ["ONLINE", "DEGRADED", "OFFLINE", "MAINTENANCE"]},
          "is_simulated": {"type": "boolean"}
        }
      }
    }
  }
}
```

## 44. Appendix — API Examples

All values are illustrative. Times use the DEMO-STORM-01 date with T0 at 08:30 UTC (14:00 IST); identifiers are shortened. Error responses use the envelope of §23.1.

**POST /auth/login**

```json
{"username": "operator1", "password": "<demo password>"}
```

```json
{"access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600, "role": "municipal_operator"}
```

**GET /health**

```json
{"status": "ok", "db": "ok", "postgis": "3.4",
 "models": {"susceptibility": "1.0.0", "wl_forecast": "1.0.0", "hazard": "1.0.0"},
 "clock": {"mode": "replay", "sim_now": "2026-11-20T08:45:00+00:00", "speed": 60, "running": true},
 "degraded": [], "version": "1.0.0"}
```

**POST /data/rainfall** (202)

```json
{"source": "replay", "records": [{"station_id": "GRID-W112", "observed_at": "2026-11-20T08:45:00+00:00", "interval_minutes": 5, "rain_mm": 7.5}]}
```

```json
{"run_id": "3a9f", "accepted": 1, "duplicates": 0, "rejected": 0}
```

**POST /data/water-level** (202)

```json
{"readings": [{"sensor_id": "SIM-SWD-W112-004", "timestamp": "2026-11-20T08:45:00+00:00", "water_level_cm": 33.6,
               "battery_percent": 88, "signal_dbm": -92, "status": "ONLINE", "is_simulated": true}]}
```

```json
{"run_id": "3aa0", "accepted": 1, "duplicates": 0, "rejected": 0, "quality": {"OK": 1, "SUSPECT": 0, "BAD": 0}}
```

**GET /zones?include=risk** (geometry elided)

```json
{"type": "FeatureCollection", "features": [{"type": "Feature",
  "properties": {"zone_id": "W112", "ward_no": 112, "risk_level": "HIGH", "probability": 0.65,
                 "confidence_level": "HIGH", "issued_at": "2026-11-20T08:45:00+00:00"},
  "geometry": {"type": "MultiPolygon", "coordinates": []}}]}
```

**GET /risk?level\_at\_least=MEDIUM**

```json
{"items": [{"prediction_id": "6f0e", "zone_id": "W112", "risk_level": "HIGH", "probability": 0.65,
            "time_to_impact_min": 30, "confidence_level": "HIGH", "issued_at": "2026-11-20T08:45:00+00:00"}],
 "next_cursor": null}
```

**GET /risk/W112**

```json
{"prediction_id": "6f0e", "zone_id": "W112", "timestamp": "2026-11-20T08:45:00+00:00", "horizon_minutes": 60,
 "status": "OK", "probability": 0.65, "hazard_score": 0.65, "exposure_score": 0.75, "vulnerability_score": 0.70,
 "impact_index": 0.725, "risk_index": 0.54, "risk_level": "HIGH", "time_to_impact_min": 30,
 "confidence": 0.83, "confidence_level": "HIGH",
 "confidence_components": {"data": 0.90, "sensor": 0.85, "forecast": 0.70, "model": 0.85, "pred": 0.80},
 "key_factors": [{"factor_key": "rain_hr_eq", "driver_group": "extreme_rainfall", "value": 85.1, "unit": "mm/hr",
                  "contribution_pct": 44.0, "direction": "INCREASES", "impact_band": "HIGH", "evidence_ids": ["e1"]}],
 "evidence_ids": ["e1", "e2"], "footprint_extent_id": "x1", "model_version_ids": ["m1", "m2", "m3"],
 "config_version": "risk-2026-10-v1", "inputs_hash": "sha256:ab12", "abstain_reasons": []}
```

**GET /explanations/{risk\_id}**

```json
{"prediction_id": "6f0e", "mode": "template",
 "text_en": "High flood risk: Ward 112. Estimated 65% chance of flooding within about 30 minutes (confidence High). Main reasons: extreme rainfall (44% of the risk); rapid water-level rise (27%); drainage stress (17%). Water-level sensors are simulated.",
 "text_ta": "<reviewed Tamil text>", "similar_event_ids": ["EVT-2015-12"],
 "limitations": ["Water-level sensors are simulated."], "verified": true,
 "evidence": [{"evidence_id": "e1", "kind": "SENSOR_OBS", "payload": {"sensor_id": "SIM-SWD-W112-004", "level_cm": 33.6}}]}
```

**POST /forecast**

```json
{"zone_id": "W112", "as_of": "2026-11-20T08:45:00+00:00"}
```

```json
{"zone_id": "W112", "available": true, "degraded": false, "time_to_impact_min": 30, "confidence": 0.70,
 "horizons": [{"horizon_minutes": 15, "p10_cm": 66.0, "p50_cm": 74.0, "p90_cm": 81.0, "exceed_prob": 0.0},
              {"horizon_minutes": 30, "p10_cm": 98.0, "p50_cm": 112.0, "p90_cm": 124.0, "exceed_prob": 0.79},
              {"horizon_minutes": 60, "p10_cm": 104.0, "p50_cm": 126.0, "p90_cm": 138.0, "exceed_prob": 0.91}],
 "rain_outlook_mm": {"next_60min": 39.3, "next_120min": 55.0}}
```

**POST /risk/analyze**

```json
{"zone_id": "W112"}
```

```json
{"outcome": "DRAFTED", "run_id": "r77", "risk": {"prediction_id": "6f0e", "risk_level": "HIGH", "probability": 0.65},
 "alert_id": "a10", "alert_status": "PENDING_REVIEW", "warnings": []}
```

**GET /alerts?status=PENDING\_REVIEW**

```json
{"items": [{"alert_id": "a10", "zone_id": "W112", "severity": "HIGH", "status": "PENDING_REVIEW",
            "headline": "High flood risk: Ward 112", "low_confidence": false, "is_simulated": true,
            "valid_until": "2026-11-20T09:45:00+00:00"}]}
```

**POST /alerts** (manual draft, 201)

```json
{"zone_id": "W112", "severity": "HIGH", "headline": "Manual advisory", "body_en": "Avoid low-lying roads near the river.", "channels": ["DASHBOARD", "SMS"]}
```

```json
{"alert_id": "a11", "status": "PENDING_REVIEW", "created_by": "u-operator1"}
```

**POST /alerts/{id}/approve**

```json
{"evidence_opened": true, "acknowledged_low_confidence": false, "comment": "Reviewed sensors and routes."}
```

```json
{"alert_id": "a10", "status": "ACTIVE", "approved_by_role": "municipal_operator",
 "dispatch": {"sent": 38, "failed": 2, "simulated": true}, "valid_until": "2026-11-20T09:45:00+00:00"}
```

```json
{"error": {"code": "STALE_PREDICTION", "message": "prediction is stale; refresh the analysis", "details": {"age_min": 41}, "request_id": "9c1d"}}
```

**POST /alerts/{id}/reject** and **/request-changes**

```json
{"comment": "Sensors in the ward are in maintenance; hold."}
```

```json
{"alert_id": "a10", "status": "REJECTED"}
```

```json
{"alert_id": "a10", "status": "CHANGES_REQUESTED", "analysis_run_id": "r78"}
```

**GET /alerts/{id}/cap** (status Exercise)

```xml
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>a10</identifier><sender>prototype@example.invalid</sender><sent>2026-11-20T14:19:00+05:30</sent>
  <status>Exercise</status><msgType>Alert</msgType><scope>Public</scope>
  <info><category>Met</category><event>Urban flood warning</event><responseType>Prepare</responseType>
    <urgency>Expected</urgency><severity>Severe</severity><certainty>Likely</certainty>
    <headline>High flood risk: Ward 112</headline>
    <area><areaDesc>Ward 112</areaDesc><polygon>13.040,80.230 13.045,80.236 13.038,80.240 13.040,80.230</polygon></area>
  </info>
</alert>
```

**GET /routes?alert\_id=a10**

```json
{"unverified": false, "items": [{"route_id": "rt1", "shelter_id": "SH-0001", "profile": "walk", "distance_m": 1800,
  "duration_s": 1350, "safety_score": 78.4, "max_segment_risk": 0.21, "blocked_edges": 0,
  "geometry": {"type": "LineString", "coordinates": [[80.234, 13.040], [80.236, 13.043]]}}]}
```

**GET /shelters?zone\_id=W112&limit=3**

```json
{"items": [{"shelter_id": "SH-0001", "name": "<from GCC data>", "capacity": null, "capacity_known": false,
            "flood_safety": 0.91, "distance_m": 650}]}
```

**GET /events**

```json
{"items": [{"event_id": "EVT-2015-12", "name": "December 2015 floods", "confidence": "HIGH", "validation_status": "UNVERIFIED"}]}
```

**POST /feedback** (201)

```json
{"alert_id": "a10", "kind": "ROUTE_BLOCKED", "text": "The subway near the market is flooded.", "location": {"lon": 80.236, "lat": 13.041}}
```

```json
{"feedback_id": "f1", "applied": false}
```

**POST /outcomes** (201)

```json
{"prediction_id": "6f0e", "zone_id": "W112", "observed_flooded": true, "label_source": "SIM_TRUTH",
 "observed_onset_at": "2026-11-20T09:18:00+00:00", "observed_peak_level_cm": 138.0, "outcome_confidence": 1.0}
```

```json
{"outcome_id": "o1", "classification": "TP", "lead_time_min": 29, "iou": null}
```

**GET /models** and **POST /models/{id}/promote**

```json
{"items": [{"model_version_id": "m2", "name": "wl_forecast", "version": "1.0.0", "kind": "WL_FORECAST", "status": "PRODUCTION",
            "trained_on_synthetic": true, "metrics": {"h30": {"label": "synthetic-validation", "skill": null}}}]}
```

```json
{"comment": "Gate passed; see the evaluation report."}
```

```json
{"model_version_id": "m9", "status": "PRODUCTION", "retired": "m2"}
```

**POST /demo/control**

```json
{"action": "start", "scenario_id": "DEMO-STORM-01", "speed": 60}
```

```json
{"mode": "replay", "scenario_id": "DEMO-STORM-01", "sim_now": "2026-11-20T08:18:00+00:00", "speed": 60, "running": true}
```

## 45. Appendix — Configuration

risk.yaml and app.yaml are in §25.3 and §25.4, the policy rules in §19.2, and .env.example in §25.2. The remaining files follow.

**config/aoi.yaml**

```yaml
hero_ward_no: 112                    # verify its GCC zone in the loaded boundary file
neighbour_rings: 1
corridor: adyar_to_coast             # wards touching the Adyar corridor, selected by adjacency
max_wards: 15
backtest_showcase:
  name: velachery_pallikaranai
  events: [EVT-2015-12, EVT-2023-12]
```

**config/sensors.yaml**

```yaml
count: 50
minimum: 30
min_in_hero_ward: 4
min_in_other_aoi_ward: 2
min_separation_m: 400
drain_depth_cm: {default: 120, variation: 0.30}
thresholds: {warn_ratio: 0.60, critical_ratio: 0.85}
model: {alpha0: 0.055, beta: 0.015, tau_min: 20, h0_cm: 5, blockage_beta: [2, 8], noise_cm: 0.4, quantisation_cm: 0.1}
faults:
  packet_loss_p: 0.02
  battery_decay_pct_per_hour: 0.03
  duplicate_p: 0.005
  clock_skew_s: {share_of_sensors: 0.05, max: 120}
```

**config/scenarios/demo\_storm\_01.yaml**

```yaml
scenario_id: DEMO-STORM-01
name: Synthetic north-east monsoon burst
t0_utc: 2026-11-20T08:30:00+00:00      # rainfall crosses 50 mm/hr; 14:00 IST
seed: 42
rain_knots: [[-12, 4], [-6, 20], [0, 55], [4, 92], [14, 90], [30, 75], [45, 50], [60, 20], [80, 5], [120, 2]]
antecedent_24h_mm: 30
forecast: {bias: 0.8, shift_min: 0}
tide_knots: [[-12, 0], [120, 0]]
faults:
  - {sensor_id: SIM-SWD-W112-003, kind: spike, start_min: 6, end_min: 7}
  - {sensor_id: SIM-SWD-W112-004, kind: outage, start_min: 8, end_min: 13}
truth:
  flooded_when: {share_of_sensors: 0.30, min_sensors: 2, consecutive_min: 3}
  extent_source: historical_analog     # observed extent of EVT-2015-12 inside the AOI, never the model's own surface
reference_timeline_min: {level_high_at: 15, dispatch_at: 19, overtopping_at: 48}   # reference only
```

**config/alerts.yaml**

```yaml
channels: {order: [SMS, APP, IVRS], retry_delays_s: [0, 2, 4], failure_rate_demo: 0.03}
sender_id: prototype-exercise            # placeholder; real sender IDs need registration
helplines: {emergency: 112, local_control_room: TO_BE_VERIFIED}
disclaimer_en: PROTOTYPE - SIMULATED DATA. Not an official warning.
disclaimer_ta: TO_BE_PROVIDED_AND_REVIEWED
language: {default: en, required_for_dispatch: [en, ta]}
sms: {max_chars_gsm7: 160, max_chars_ucs2: 70}
```

**config/datasets.yaml (two entries; the rest follow the register of §6.2)**

```yaml
datasets:
  - id: D01
    name: GCC wards and zones
    kind: vector
    access: arcgis_rest
    url: https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/GCC_COLLABORATION_LAYER/MapServer
    layer_name_contains: [ward, zone]      # enumerate the layers first; do not hard-code layer ids
    expected_rows: 200
    crs_expected: EPSG:4326
  - id: D04
    name: GPM IMERG half-hourly (Early)
    kind: raster_time_series
    access: earthaccess
    short_name: GPM_3IMERGHHE              # verify the short name and version in the Earthdata catalogue
    version: '07'
    bbox: [80.05, 12.80, 80.40, 13.30]     # approximate Chennai extent; derive from aoi.yaml
    credentials_env: [EARTHDATA_USERNAME, EARTHDATA_PASSWORD]
```

## 46. Appendix — Dataset References

URLs are taken from the Dataset Research Report and the two research guidebooks and were not independently re-verified here. Access conditions change (the report notes new authorisation requirements for some Copernicus DEM GLO-30 routes in 2026). Record the retrieval date, version and licence of everything you download in data/manifest.yaml.

| ID | Dataset | Reference | Note |
| --- | --- | --- | --- |
| D01, D09, D10, D16 | GCC GIS service (wards, zones, drains, rivers, roads, buildings) | https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCDepts/GCC\_COLLABORATION\_LAYER/MapServer | Enumerate layers; page with maxRecordCount |
| D01, D09, D10, D16, D17, D18 | OpenCity Chennai datasets (SWD maps, waterbodies, shelters, flood events, rainfall) | https://data.opencity.in/dataset/?groups=chennai&q=data | Shelters: https://data.opencity.in/dataset/chennai-shelters; check each file's format and licence |
| D02, D03 | IMD data services | https://mausam.imd.gov.in/ | Gridded data through the IMD Pune portal or the imdlib package; the IMD API portal needs registration (Grok guidebook) |
| D03 | IMD radar products | https://mausam.imd.gov.in/responsive/radar.php | Display only; raw access not assumed |
| D04 | NASA GPM IMERG | https://gpm.nasa.gov/data/imerg | Earthdata login; verify short names |
| D05 | Open-Meteo forecast API | https://open-meteo.com/ | Added in this manual, not in the research report; check terms, attribution and rate limits |
| D05 | ECMWF open data (IFS, AIFS) | https://www.ecmwf.int/en/forecasts/datasets/open-data-0 | Optional; resolution to verify (0.25 or 0.4 degrees) |
| D06 | ERA5 hourly reanalysis | https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels | Backtests and climatology |
| D02 | CHIRPS v3 | https://www.chc.ucsb.edu/data/chirps3 | Optional climatology |
| D07 | CWC hydro-meteorological observations | https://cwc.gov.in/hydro-meteorological-observation | Access-dependent |
| D07 | Copernicus GloFAS historical | https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical | Optional upstream context |
| D08 | Copernicus DEM | https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM.html | GLO-30 access route to verify; fallback SRTM and GLO-90 |
| D08 | USGS SRTM | https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm | Fallback DEM |
| D10 | HydroSHEDS | https://www.hydrosheds.org/products | Hydrographic context |
| D10 | JRC Global Surface Water | https://global-surface-water.appspot.com/download | Permanent-water mask |
| D11 | ESA WorldCover | https://esa-worldcover.org/en/data-access | Land cover 10 m |
| D11 | GHSL built-up surface | https://developers.google.com/earth-engine/datasets/catalog/JRC\_GHSL\_P2023A\_GHS\_BUILT\_S\_10m | Imperviousness proxy |
| D12 | Google Open Buildings | https://sites.research.google/gr/open-buildings/ | Fallbacks below |
| D12 | Microsoft building footprints | https://github.com/microsoft/GlobalMLBuildingFootprints | Alternative |
| D13 | WorldPop India 100 m | https://hub.worldpop.org/project/categories?id=3 | Age and sex structure |
| D14, D15 | OpenStreetMap, Geofabrik India | https://download.geofabrik.de/asia/india.html | Or OSMnx download by polygon; ODbL attribution |
| D17 | Bhuvan flood early warning and hazard layers | https://bhuvan-app1.nrsc.gov.in/fews/index.php and https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood\_hz/flood\_hz.php | Labels and hazard priors |
| D17 | Global Flood Database | https://developers.google.com/earth-engine/datasets/catalog/GLOBAL\_FLOOD\_DB\_MODIS\_EVENTS\_V1 | 2000 to 2018 events |
| D17 | Copernicus Sentinel-1 | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1 | Change-detection masks; urban caveat |
| D17 | Sen1Floods11 | https://github.com/EOEPCA/Sen1Floods11-Dataset | Optional SAR model training |
| D07 | PSMSL tide records, INCOIS | per the Grok guidebook | Optional; verify station and terms |
| D21 | NDMA urban flooding guidelines | NDMA website (public document) | Cite chunk ids in explanations |

Other references to consult, by name: the OASIS Common Alerting Protocol 1.2 specification; the TRAI DLT framework for commercial SMS in India; India's Digital Personal Data Protection Act, 2023; IMD's impact-based colour-coded warning documentation (to understand how official warnings differ from this prototype's levels).

Revision history: 1.0, 9 October 2026, initial build specification for the DREAMOVATION 2.0 DREAM-SSB-09 Chennai prototype.
