# Chennai Flood Prototype — Dataset Download Links

This file contains the Chennai-focused dataset and data-source links for the Dreamovation 2.0 prototype:
**DREAM-SSB-09 — Climate-Resilient Urban Flood Monitoring and Early Warning System**.

The priority is to use real Chennai observations, government/open geospatial datasets, and historical flood observations wherever possible.

---

## 1. Core Chennai Rainfall Data

- **Chennai Rainfall Data — IMD / OpenCity**
  - https://data.opencity.in/dataset/chennai-rainfall-data
  - Historical monthly and daily Chennai rainfall data.

---

## 2. Historical Chennai Flood Data

- **Chennai Flooding Data — OpenCity**
  - https://data.opencity.in/dataset/chennai-flooding-data
  - Flood inundation points, inundation depth and flood-hazard-related layers.

- **Chennai Floods 2015 Data — OpenCity**
  - https://data.opencity.in/dataset/chennai-floods-2015-data
  - GCC stagnation locations, flood hotspots, crowdsourced locations and NRSC inundation information.

- **Chennai Floods 2005 Data — OpenCity**
  - https://data.opencity.in/dataset/chennai-floods-2005-data
  - Historical 2005 flood hotspots and flood extent.

- **Chennai Floods 2020 Data / Cyclone Nivar — OpenCity**
  - https://data.opencity.in/dataset/chennai-floods-2020-data
  - Chennai flood hotspots associated with Cyclone Nivar.

---

## 3. Chennai Storm-Water Drainage

- **Chennai Stormwater Drain (SWD) Maps — OpenCity / GCC**
  - https://data.opencity.in/dataset/chennai-stormwater-drain-swd-maps
  - Storm-water drainage maps, including machine-readable KML resources.

- **Chennai Basin Drainage Maps — OpenCity**
  - https://data.opencity.in/dataset/chennai-basin-drainage-maps
  - Rivers, streams, Buckingham Canal, Krishna Water Canal, macro drains and micro drains.

- **Chennai Microwatersheds Map — OpenCity**
  - https://data.opencity.in/dataset/chennai-microwatersheds-map
  - Catchments, watersheds and microwatersheds.

---

## 4. Chennai Rivers and Waterbodies

- **Chennai Waterbodies — OpenCity**
  - https://data.opencity.in/dataset/chennai-waterbodies
  - Chennai waterbodies, basin waterbodies and rivers.

- **Chennai Lake Levels Since 2003 — OpenCity**
  - https://data.opencity.in/dataset/chennai-lake-leves-since-2003
  - Historical storage levels for major Chennai-area reservoirs/lakes.

- **Chennai Lakes Inflow and Outflow — OpenCity**
  - https://data.opencity.in/dataset/chennai-lakes-inflow-and-outflow
  - Lake inflow/outflow information for major Chennai lakes.

---

## 5. Chennai Administrative Boundaries

- **GCC Ward and Zone Information — OpenCity**
  - https://data.opencity.in/dataset/gcc-ward-information
  - Chennai ward boundaries, zone boundaries and related GCC administrative information.

---

## 6. Chennai Roads and Transport

- **Chennai Road Centerline Map — OpenCity / GCC**
  - https://data.opencity.in/dataset/chennai-road-centerline-map
  - Chennai road-centerline GIS data.

- **Geofabrik Southern India OpenStreetMap Extract**
  - https://download.geofabrik.de/asia/india/southern-zone.html
  - OSM road and infrastructure data; useful as a backup/supplement to GCC road data.

---

## 7. Shelters and Relief Centres

- **Chennai Shelters — OpenCity**
  - https://data.opencity.in/dataset/chennai-shelters
  - Chennai shelter locations in GIS format.

- **GCC Relief Centres — OpenCity**
  - https://data.opencity.in/dataset/gcc-relief-centres
  - GCC relief-centre information. Check the resource format before integrating because the available resource may require extraction from PDF.

---

## 8. Official Chennai Real-Time Flood Forecasting System

- **Chennai Real-Time Flood Forecasting & Spatial Decision Support System**
  - https://chennaifloodmonitor.tn.gov.in/
  - Official Chennai flood-monitoring and forecasting platform.

- **Official Chennai RTFF & SDSS Dashboard**
  - https://chennaifloodmonitor.tn.gov.in/HomePage/Dashboard
  - Rainfall, forecast, water-level, lake and related monitoring information.

- **RTFF & SDSS About / System Information**
  - https://www.chennaifloodmonitor.tn.gov.in/Master/AboutUs
  - Background on Chennai's real-time flood forecasting and spatial decision-support system.

**Important:** Do not claim direct API/live machine-to-machine access unless the actual feed/API has been verified. Use publicly downloadable/replayable data for the Monday prototype where necessary.

---

## 9. Satellite-Derived Chennai Flood Observations

- **NRSC 2021 Flood Inundation Products**
  - https://www.nrsc.gov.in/nrscnew/2021_Floods.php
  - National Remote Sensing Centre flood products, including Chennai-area inundation observations.

- **Bhuvan Flood / Disaster Portal**
  - https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood/flood.php?uname=empty
  - Historical satellite-derived flood information and disaster products.

- **NRSC / Bhuvan Open Data Download Portal**
  - https://bhuvan-app3.nrsc.gov.in/data/download/tools/download1/tooldown1.php
  - Open-data/product download interface.

- **Bhuvan National Flood Vulnerability Application**
  - https://bhuvan-app1.nrsc.gov.in/nfvas/
  - Flood vulnerability and supporting geospatial layers.

---

## 10. Terrain / Elevation

### SRTM

- **OpenTopography SRTM Global 30 m**
  - https://portal.opentopography.org/raster?jobId=rt1743104115266
  - Use to obtain elevation data and clip it to the Chennai study area.

### Copernicus DEM

- **Copernicus DEM GLO-30 / GLO-90**
  - https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM
  - Global elevation products at approximately 30 m / 90 m resolution.

For a Monday prototype, use whichever DEM can be downloaded with the least friction and clip it to Chennai.

---

## 11. Population Exposure

- **WorldPop India Population — approximately 100 m**
  - https://hub.worldpop.org/geodata/summary?id=73807
  - Population raster that can be clipped to the Chennai study area.

---

## 12. Building Footprints

- **Google Open Buildings**
  - https://sites.research.google/gr/open-buildings/
  - Building polygons/points and building-area information.

For the Monday prototype, building footprints are optional. Prioritize rainfall, flooding, drainage, terrain, roads, population and shelters first.

---

## 13. Recommended Download Order

If time is limited, download in this order:

1. Chennai Rainfall
2. Chennai Flooding Data
3. Chennai Floods 2015
4. Chennai Stormwater Drains
5. Chennai Basin Drainage
6. Chennai Waterbodies
7. Chennai Lake Levels
8. Chennai Lake Inflow/Outflow
9. GCC Wards/Zones
10. Chennai Road Centerline
11. Chennai Shelters / Relief Centres
12. NRSC/Bhuvan flood observations
13. SRTM DEM
14. WorldPop population

---

## 14. Suggested Local Folder Structure

```text
CHENNAI_FLOOD_DATA/
├── 01_rainfall/
├── 02_historical_floods/
├── 03_drainage/
├── 04_water/
├── 05_terrain/
├── 06_transport/
├── 07_administrative/
├── 08_population/
├── 09_shelters/
└── 10_satellite_validation/
```

---

## 15. Prototype Principle

The Monday demonstration should distinguish clearly between:

- **Real Chennai data** — downloaded from the sources above.
- **Model-derived results** — predictions/risk scores calculated by the prototype from those real inputs.
- **Simulated sensor replay** — only where a public raw real-time feed cannot be accessed; label it explicitly as a prototype/replay stream.

Do not present synthetic values as live government telemetry.

The strongest demonstration is a replay/analysis of a real Chennai historical event and comparison of the prototype's risk assessment with real observed flood/inundation data.
