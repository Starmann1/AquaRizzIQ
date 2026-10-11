# Chennai P0 Source Audit

**Retrieved:** 2026-10-11 (Asia/Kolkata)  
**Purpose:** Verify source files before application ingestion. Original downloads are retained under ignored `data/raw/chennai/`; this report and `data/manifest.yaml` record provenance and quality findings.

## Summary

| Dataset | Source file | Coverage | Inspection result | Application status |
|---|---|---|---|---|
| GCC divisions, 2022 | `gcc-wards-2022.kml` | 200 numbered divisions; bbox 80.1340948–80.3314935 E, 12.8520929–13.2350491 N | KML coordinates are longitude, latitude[, altitude] in WGS 84 per the KML specification. 9 of 209 polygon components were self-intersecting. Audited `make_valid` repairs change projected area by at most 0.000179%; division 69 becomes 3 polygon parts. | Normalized to EPSG:4326 GeoJSON after opt-in audited repair. Raw source remains unchanged. |
| GCC zones, 2022 | `gcc-zones-2022.kml` | 15 named zones plus one unnamed polygon; same city extent | 3 of 16 polygon components were self-intersecting. Zone IX is Teynampet; Zone X is Kodambakkam. The unnamed polygon is excluded. Six division-to-zone intersections are ambiguous under the 99% overlap rule. | Normalized to EPSG:4326; 194 divisions receive a zone, 6 retain a null zone plus candidate/fraction audit. |
| Chennai daily rainfall | `chennai-rainfall-1991-2023.csv` | 21,416 rows; date range 1993-03-03 through 2023-12-26; 62 station-name labels; district field is Chennai | Fields are `District`, `Station`, `Rainfall`, `Date`; none are blank. `Rainfall` unit is not declared and station coordinates are absent. 1,447 extra station/date rows occur, including 86 station/date keys with conflicting values. Values span 0.01–348.3; no negative or unparsable values. Catalog metadata identifies TNDMA as resource source, while the dataset page organization is IMD. | Historical tabular source only. Do not map to wards or use as a quantitative risk input until unit, station identity/location, and duplicate semantics are verified. |
| Official Chennai RTFF dashboard historical ARG report | `rtff-arg-area9-teynampet-2026-10-04-2026-10-11.pdf` | One ARG station (Area 9 - Teynampet), requested 2026-10-04 through 2026-10-11 | Official dashboard exposes a historical download. The downloaded one-page report contains the station/date header and hourly table headings, but no observation rows or values. It contains no station coordinates. Dashboard units are labelled mm, but this empty report provides no observations to validate. | Official source investigated; this report is empty and cannot support a rainfall layer or risk input. Other station/date combinations were not audited. |
| Official Chennai RTFF dashboard Nungambakkam cross-check | Official dashboard selected station `Nungambakkam` (ARG); historical table requested 2026-10-04 through 2026-10-11 | The table displayed seven dates (2026-10-04–10) with 0.0 values for reported hourly periods; 2026-10-10 later periods included `NA`. The dashboard chart displayed `Updated at undefined`; no station coordinates or independent freshness signal were visible. The dashboard labels chart units, but the table did not establish station location or reporting freshness. | Confirms the dashboard can expose station/date observations for another selection, but zeros and missing periods without coordinates/freshness are not adequate to establish a spatialized, current rainfall input. Retained as a read-only verification; no raw export was obtained. |
| TN-SMART daily rainfall page, 2026-10-11 | `tnsmart-daily-rainfall-page-2026-10-11.html` | Reports mm for 2026-10-10 08:30–2026-10-11 08:30 IST. Embedded `rainfall_data` contains 63 Chennai station records with unique codes, coordinate pairs, and numeric rainfall; six report positive values (4.4, 3.0, 2.2, 1.0, 0.8, 0.4 mm), and the rest report 0 mm. Its page script builds GeoJSON Point features `[longitude, latitude]` and renders them with Leaflet. The geodetic datum is not separately declared. | Processor outputs 62 points covered by the 2022 GCC division union and records one source point outside the union as excluded. The map uses the same API features and shows source-provided daily rainfall categories/popups. Coordinates are not transformed; display follows the source page's own GeoJSON/Leaflet mapping convention. Snapshot only; not a live feed and not used for ward risk. |
| Tamil Nadu SWGW manual daily rainfall, 1991–2020 | `tnswgw-daily-rainfall-1991-2020.csv` | 24,306 rows; nine districts; 66 station/coordinate pairs; dates 1991-01-03–2019-09-30 | Units are explicitly mm and coordinates are present, but the downloaded source contains zero Chennai rows. Acquisition-time values vary; four repeated station/location/time keys remain unexplained. | Unsuitable for Chennai rainfall visualization or risk inputs. |
| IMD daily gridded rainfall, 0.25 degree, 2015 | `imd-rainfall-grid-025-2015.nc` | 365 dates, 129 × 135 grid; 2015-01-01–2015-12-31; 0.25 degree spacing | Units are mm; one coordinate node was selected by overlap with the GCC union. That node is missing on all 365 dates. The NetCDF declares longitude/latitude units but not a geodetic datum; no CRS transformation or datum alignment is claimed. | Raw source validated, but it provides no valid Chennai/GCC rainfall observation for 2015 and is not used for risk. The API returns an empty map layer with the missing coverage stated. |
| Chennai 2015 NRSC inundation zone | `flood-2015-nrsc.kml` | 4,001 polygon components; bbox 79.3466338–80.3191437 E, 12.5189872–13.3297221 N | All inspected polygon components are valid. Extent includes areas outside GCC. Attributes include `id`, `area`, `perimeter`, and `pixelvalue`; acquisition timestamps are absent. Catalog describes the layer as NRSC inundation for the 2015 floods; license is listed as Public Domain. Processing retained 1,212 features intersecting the 2022 GCC division union, excluded 2,789 fully outside features, and clipped 215 partial intersections. No geometry repair was needed. | Available from the historical-flood API and optional map layer. Not event chronology or validated model labels. |
| Chennai inundation points with depth | `inundation-points-depth.kml` | 192 points; bbox 80.1674375–80.2610580 E, 12.9113740–13.1646096 N | All points parsed; KML coordinates are WGS 84. Catalog describes depth in inches; the records contain a `DEPTH` field but no per-feature date. | Supplementary historical evidence only; event date remains unknown. |

## Provenance and source metadata

The exact URLs, retrieval date, file sizes, SHA-256 checksums, catalog source, format, CRS, coverage, units, preprocessing, limitations, and current status are recorded in [`data/manifest.yaml`](../../data/manifest.yaml). The raw files are byte-for-byte source downloads and have not been transformed.

For KML, the source files do not contain a separate CRS declaration. The KML specification defines coordinate tuples as longitude, latitude, and optional altitude using WGS 84; the observed coordinate ranges are consistent with Chennai. Coordinates must still be range-checked at ingestion.

## Local fixture audit

| Current local data | Classification | Demo/use restriction |
|---|---|---|
| `data/fixtures/wards.geojson` | Fixture; geometry and properties unverified | Keep for development only. Do not present its population, elevation, imperviousness, susceptibility, or zone values as observed/official. Ward 112 is in Teynampet (Zone IX) by overlay against the downloaded 2022 boundaries, unlike the fixture's Zone X label. |
| `data/fixtures/sensors.json` | Simulated fixture | Keep the `SIM-` prefix and simulated badge; not live telemetry. |
| `data/fixtures/shelters.json` | Unverified fixture | Do not claim official location, capacity, occupancy, elevation, or safety score. |
| `aquarizz.db` rainfall/sensor observations | Simulated; all inspected rows have `is_simulated=1` | Simulation/demo only. |
| Database grid cells/features | Derived from fixture geography | Not authoritative analysis units. |
| API `/risk` | Explicit `INSUFFICIENT_EVIDENCE` for available divisions | Numeric metrics remain null until verified current inputs are connected. |
| API `/data/quality` | Computed from registered sensors and stored observations | No live source is verified; an empty store reports `NO_DATA`. Simulated observations remain labelled. |

## Data availability decision

| Feature | Classification | Reason |
|---|---|---|
| GCC administrative geography | Available and normalized locally | 200 division features and 15 named zones; repairs are opt-in and recorded in `data/processed/chennai/boundary-import-audit.json`. Six division-zone joins remain ambiguous and are not forced. |
| Historical rainfall series | Available locally after download; restricted | Dates/station strings exist, but units and station coordinates are absent and duplicates conflict. |
| Official rainfall observations | A TN-SMART daily snapshot is processed as 62 source-rendered point features within the GCC boundary; 63 Chennai rows were inspected and one out-of-union point excluded. RTFF historical control was also inspected. | Units and a 24-hour interval are explicit; the daily page embeds coordinates in GeoJSON and renders them with Leaflet, but does not separately declare a datum. The source is one dated snapshot, not a live feed; it is not used for ward risk. The Area 9 - Teynampet RTFF PDF contains no observations; the RTFF Nungambakkam table lacks reliable freshness. |
| 2015 IMD grid rainfall | Source file verified, but unsuitable for a Chennai rainfall layer | Only the coordinate node selected inside GCC is missing on all dates; datum is undeclared. |
| 2015 satellite-derived inundation extent | Available as historical map layer | 1,212 clipped features; broad extent and no per-feature acquisition-time attribute. |
| Inundation-depth points | Available locally after download; limited | 192 points, catalog unit is inches, date is not recorded per point. |
| Ward-level rainfall | Not justified yet | The TN-SMART source has station coordinates and one-day observations, but there is no sustained, quality-controlled station history, no independent datum declaration, and no verified ward-level aggregation methodology. |
| Real-time rainfall or water-level telemetry | Unavailable in this checkout | No verified live feed or API access; existing sensor readings are simulated. |
| Calibrated/validated flood risk | Not justified | No verified rainfall units/spatial linkage, no real exposure layers, and no held-out validation evidence. |
| Elevation, drainage, population, roads, official shelters | Unavailable locally | Only links or unverified fixtures are present; no source files have passed inspection. |
| Ward polygons and metric area / zone joins | Processed | Area and overlays use EPSG:32644; web GeoJSON is EPSG:4326. A 99% intersection criterion leaves six divisions unresolved. |

## Next implementation gates

1. Keep source files immutable under `data/raw/chennai/` and verify their checksums with the source manifest.
2. Re-run `python scripts/validate_chennai_sources.py` to verify source checksums and data quality.
3. Rebuild boundaries with `python scripts/import_chennai_boundaries.py --repair-invalid`; inspect the recorded geometry repairs and zone-join audit before changing the explicit 99% assignment rule.
4. Keep OpenCity, Tamil Nadu SWGW, and RTFF observations excluded from risk until a Chennai-suited dataset has verified duplicate semantics and coverage, and the live/forecast sources provide reliable freshness. The TN-SMART snapshot establishes a daily map layer only; the retained blank PDF and Nungambakkam table are specific to the selected station/date range inspected.
5. Rebuild IMD rainfall extraction with `python scripts/process_imd_rainfall.py`; it retains explicit missing records and reports the absence of usable GCC values.
6. Rebuild the historical layer with `python scripts/process_chennai_floods.py`; review its audit before presenting it as a historical visual reference.
7. The API serves the historical flood layer, the explicitly empty 2015 IMD rainfall layer, and 62 TN-SMART station points for the 2026-10-11 daily snapshot. The source page itself maps the embedded GeoJSON points, but does not explicitly name the datum. Risk remains abstained because this one-day rainfall snapshot is not paired with verified water-level and exposure inputs and cannot support calibrated ward-level risk.

## Reproduce the processed P0 data

Run from the repository root, in this order:

```powershell
python scripts/validate_chennai_sources.py
python scripts/import_chennai_boundaries.py --repair-invalid --force
python scripts/process_imd_rainfall.py --force
python scripts/process_chennai_floods.py --force
python scripts/process_tnsmart_rainfall.py --force
python scripts/validate_chennai_sources.py
pytest --basetemp .pytest-tmp apps/api/tests -q
Push-Location apps/web
npm run build
Pop-Location
```

The boundary import must run first because the IMD and flood processors consume its normalized GCC divisions. Source validation checks manifest sizes and SHA-256 values; the PDF report check verifies its PDF header and checksum, while its empty observation table is recorded from manual text and visual inspection. Processed outputs remain in `data/processed/chennai/`; raw sources are not modified. Backend tests require a Windows environment that permits asyncio socket-pair creation.
