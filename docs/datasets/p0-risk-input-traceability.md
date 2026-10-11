# P0 Risk Input Traceability

## Current decision

The current ward-risk API abstains for every ward with `INSUFFICIENT_EVIDENCE`. It returns null numeric scores and confidence. It does not consume historical flood polygons as current hazard input. The 2015 layer is contextual historical evidence only.

## Source-to-UI trace

| Input / layer | Source and validation | Processing and storage | API / map use | Risk use and current status |
|---|---|---|---|---|
| GCC divisions, 2022 | GCC-attributed KML mirror; checksum and 200-division inventory verified; KML WGS 84 coordinates range-checked | Raw KML preserved. `scripts/import_chennai_boundaries.py` records explicit geometry repairs, projected area deltas and division-zone overlay results; normalized RFC 7946 GeoJSON | `/api/v1/zones`, `/api/v1/risk`; division outlines and selection on Flood Risk Map | Defines administrative geometry only; not a hazard/exposure score |
| GCC zones, 2022 | 15 named zone polygons; one unnamed polygon excluded | Same boundary processor; 194 division joins meet the explicit overlap threshold; 6 remain unresolved | Zone attributes accompany division response; map can identify source zone where joined | Administrative context only |
| OpenCity Chennai daily rainfall | 21,416 rows, but units and coordinates absent; duplicates include 86 conflicting station/date keys | Raw CSV retained and audited; not imported into live tables or spatialized | Provenance and quality documentation only | Excluded from all spatial and current risk calculations |
| Tamil Nadu SWGW manual daily rainfall | Officially described in mm with coordinates; local download has zero Chennai rows | Raw CSV and checksum retained; source QA marks it unsuitable | Source audit only | Excluded; no Chennai readings |
| Official RTFF dashboard ARG report | Historical download verified for Area 9 - Teynampet, 2026-10-04 through 2026-10-11; report has no observations or coordinates | One-page PDF retained and checksummed; text and rendered page reviewed | Provenance only; no rainfall map features are generated | Excluded; this single report does not establish availability for other stations or dates |
| Official RTFF dashboard Nungambakkam cross-check | Dashboard selection was Nungambakkam (ARG); historical table showed 2026-10-04 through 2026-10-10, reported hourly periods at 0.0 and some later `NA` intervals. Chart freshness appeared as `undefined`; coordinates were not exposed. | Read-only table inspection on the official dashboard; no raw export retained | No map feature is generated | Excluded; without verified station coordinates and freshness, the table is not a risk-grade spatial observation feed |
| TN-SMART daily station snapshot, 2026-10-11 | Page states units are mm and interval is 2026-10-10 08:30–2026-10-11 08:30 IST. Its embedded data includes 63 Chennai rows with unique station codes and source coordinates; the page builds GeoJSON points and displays them through Leaflet. The datum is not separately declared. | Raw page retained and checksummed; processor validates rows, filters 62 points covered by the processed GCC union, and records one out-of-union station in the audit. No datum transformation is performed. | `/api/v1/layers/rainfall/tnsmart/2026-10-11` returns the same 62 point records consumed by the map; each point popup uses its API properties. | Dated observed snapshot only; not a live feed, not used for ward risk, and no datum accuracy claim beyond reproducing the source page's own mapping convention |
| IMD 0.25-degree daily rainfall, 2015 | NetCDF structure, axes, units, and dates validated; datum is not declared | `scripts/process_imd_rainfall.py` point-selects grid coordinates against GCC division union, retains 365 explicit missing rows and emits an audit. Selected coordinate is missing for all 365 dates | `/api/v1/layers/rainfall/2015` returns an empty FeatureCollection and metadata; UI layer control reports no marks | No valid rainfall input. Not used for risk |
| NRSC 2015 inundation KML | 4,001 source polygons valid; source hash checked; per-feature acquisition time absent | `scripts/process_chennai_floods.py` intersects source geometries with processed GCC union, using EPSG:32644 for area summaries; raw file preserved; no geometry repair | `/api/v1/layers/historical-floods/2015`; optional historical map layer with provenance metadata | Contextual historical evidence only; never treated as current conditions or validated labels |
| Sensor observations | Database and fixture observations have simulation flags; no external live source is connected | `/api/v1/data/quality` computes state/freshness from stored values and reports simulation status | Quality/status panel | Not eligible as verified live water-level inputs |
| Record-level evidence and explanation | No verified observation registry or source lineage is connected | The legacy graph now abstains at retrieval, discards caller-supplied numeric features, and creates no evidence records; `/api/v1/explanations/{assessment_id}` returns an explicit abstention | Evidence page reports that no traceable evidence is registered; explanation page reports unavailable drivers | No hashes, Shapley values, narratives, or confidence values are claimed |
| Exposure and vulnerability attributes | Local fixture geography contains unverified population, elevation, imperviousness and susceptibility fields; source audit marks these as fixtures | Not used to construct source-verified risk inputs | Fixture-only and demo surfaces must remain labeled | Excluded from current P0 risk scores |

## Risk endpoint invariants

- `GET /api/v1/risk` and `GET /api/v1/risk/{ward_id}` return `INSUFFICIENT_EVIDENCE` until valid, sufficiently current hazard inputs and traceable exposure inputs are connected.
- `risk_score`, hazard, exposure, vulnerability, impact and confidence remain null during abstention.
- Historical flood polygons, daily missing rainfall records, fixture attributes, and unmarked database observations do not satisfy current-input requirements.
- No risk color band, population estimate, or probability is inferred from missing values.

## Remaining P0 input gaps

- Historical 2015 Chennai rainfall remains unavailable from the selected IMD node (365/365 missing); the retained TN-SMART page supports only a single dated daily snapshot, with no independent geodetic-datum declaration.
- Verified current rainfall and water-level feeds for current warnings.
- Source-verified exposure and vulnerability layers before numerical risk/explainability can be shown.
- A defensible datum/positional-alignment basis for using the IMD grid spatially, plus a repeatable multi-day rainfall history suitable for event replay.
- RTFF station metadata and observation timestamps/freshness, plus a repeatable raw-data export, before any selected station values can enter the rainfall layer.

Until those inputs pass QA, a measured risk map, operational explanation, or model-driven alert is unsupported. The source-backed boundary and historical layer remain demonstrable independently.
