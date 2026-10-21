# Master Implementation Plan: Mapping Nigeria's Digital Divide Through Geospatial Data

> **DSN Bootcamp Geospatial Hackathon**  
> **Key Objective**: Uncover internet connectivity disparities across Nigeria, integrate external demographic and socioeconomic datasets, identify underserved communities, and produce an award-winning interactive dashboard, rigorous spatial analysis, and a 2-page executive policy brief.

---

## 1. Executive Summary & Problem Framing

### The Core Challenge
The official hackathon brief asks:  
> *"Which communities have poor internet connectivity relative to their population, settlement characteristics, and socioeconomic needs, and where should connectivity improvements be prioritized?"*

### For Beginners in Geospatial Data (ELI10 Primer)
If you or your teammates have never worked with geospatial data before, here is the mental model in 3 simple rules:
1. **Geometries are Shapes on Earth**: Data points can be **Points** (like a cell tower at latitude 6.5, longitude 3.3), **Polygons** (like the boundary of an LGA or state, or a square tile), or **Rasters** (gridded pixel heatmaps like satellite imagery).
2. **Spatial Joins are "VLOOKUP by Location"**: Instead of matching on an ID like `LGA_CODE == 101`, a spatial join matches records because a point or tile falls *inside* a polygon boundary (`geom.within(lga_boundary)`).
3. **CRS (Coordinate Reference System)**: Think of CRS as the language of the map. GPS coordinates are usually in **EPSG:4326 (WGS84)** in degrees (latitude/longitude). For distance/area measurements, we reproject to a metric CRS like **EPSG:3857** or UTM Zone 31N/32N. We handle all of this automatically in Python!

---

## 2. Integrated Architecture & Data Pipeline

```
+---------------------------------------------------------------------------------------+
|                                    DATA SOURCES                                       |
+---------------------------------------------------------------------------------------+
|  1. Ookla GPKG (Provided)    2. LGA Boundaries (HDX/geoBoundaries)   3. NBS Poverty/Pop |
|  - 9,234 zoom-16 tiles       - 774 Local Government Areas            - State/LGA pop    |
|  - Download / Upload / Lat   - 36 States + FCT                       - NBS 2022 MPI     |
|  - Tests & unique devices    - GeoJSON / Shapefile format            - Urban/Rural tag  |
+------------------------------------------+--------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                          ETL & GEOSPATIAL JOIN PIPELINE                               |
|                                                                                       |
|  [Step 1] Geometry Validation (EPSG:4326 WGS84 standardization)                       |
|  [Step 2] Spatial Point-in-Polygon & Tile Overlay onto 774 LGAs                      |
|  [Step 3] Aggregation & Normalization (Weighted Speeds, Device Coverage, Latency)     |
|  [Step 4] Feature Engineering:                                                        |
|           * Speed Deficit = max(0, Benchmark_25Mbps - avg_d_mbps)                    |
|           * Population Exposure = LGA Population * (1 - Coverage_Rate)                |
|           * Digital Inclusion Priority Index (DIPI) Calculation                       |
+------------------------------------------+--------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                          ANALYTICAL & STATISTICAL ENGINE                              |
|                                                                                       |
|  * Spatial Autocorrelation: Global & Local Moran's I (Hotspot / Coldspot clusters)    |
|  * Geopolitical Zone Disparity Matrix (SW, SE, SS, NC, NE, NW)                        |
|  * Urban vs Rural Connectivity Gap Quantification                                     |
|  * 3-Tier Investment Priority Classification (Critical, Vulnerable, Emerging)         |
+------------------------------------------+--------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
+---------------------------------------+     +-----------------------------------------+
|     INTERACTIVE DASHBOARD APP         |     |        SUBMISSION 2-PAGE PDF            |
|  - Streamlit + Pydeck + Folium UI     |     |  - High-res choropleth maps             |
|  - Dark Glassmorphism Design System   |     |  - Key findings & statistical callouts  |
|  - Dynamic LGA/State drilldown        |     |  - Policy & USPF investment roadmap     |
|  - Dual-layer slider & filter metrics |     |  - Formatted cleanly to 2 pages max     |
+---------------------------------------+     +-----------------------------------------+
```

---

## 3. Data Ingestion & Integration Strategy

### Data Source 1: Provided Ookla Geopackage (`Nigeria Ookla.gpkg`)
* **Size**: 9,234 tile polygons covering populated/tested corridors of Nigeria.
* **Attributes**: `tile_x`, `tile_y`, `avg_d_kbps`, `avg_u_kbps`, `avg_lat_ms`, `avg_lat_down_ms`, `avg_lat_up_ms`, `tests`, `devices`.
* **Derived Metrics**: Convert kbps to Mbps (`avg_d_mbps = avg_d_kbps / 1000.0`), calculate upload/download asymmetry, and classify latency health (<50ms Excellent, 50-100ms Moderate, >100ms Poor).

### Data Source 2: External Administrative Boundaries (Nigeria 774 LGAs & 36 States)
* **Source**: geoBoundaries / HDX OCHA Nigeria ADM2 (Local Government Areas).
* **Role**: Provides the official administrative boundaries and names for Nigeria's 774 LGAs and 36 States + FCT.
* **Why it matters**: Telecommunications policy, Universal Service Provision Fund (USPF) interventions, and state government initiatives operate strictly at the LGA and State level.

### Data Source 3: Population & Socioeconomic Deprivation (NBS MPI & Census Projections)
* **Source**: Nigeria National Bureau of Statistics (NBS) 2022 Multidimensional Poverty Index (MPI) survey + LGA Population projections.
* **Variables**:
  * Population per LGA (National Population Commission / WorldPop aggregations).
  * Multidimensional Poverty Headcount ratio ($H$) and Intensity ($A$).
  * Urban vs. Semi-Urban vs. Rural settlement typology.

---

## 4. Mathematical Formulation: Digital Inclusion Priority Index (DIPI)

To move beyond simple speed test rankings and solve the prompt's key challenge, we define a composite **Digital Inclusion Priority Index (DIPI)** scaled from $0$ to $100$ for each LGA $i$:

$$DIPI_i = w_{1} \cdot S_{i} + w_{2} \cdot P_{i} + w_{3} \cdot M_{i} + w_{4} \cdot L_{i}$$

Where:
* $S_i$ **(Speed Deficit Score, 35% weight)**: Normalized gap between local download speed and the Nigerian National Broadband Plan target (25 Mbps for urban / 10 Mbps for rural):
  $$S_i = \min\left(1.0, \max\left(0.0, \frac{25 - \text{Speed}_i}{25}\right)\right)$$
* $P_i$ **(Population Exposure Score, 30% weight)**: Normalized logarithm of population living in underserved or un-tested tiles:
  $$P_i = \frac{\ln(\text{Pop}_i) - \ln(\text{Pop}_{\min})}{\ln(\text{Pop}_{\max}) - \ln(\text{Pop}_{\min})}$$
* $M_i$ **(Multidimensional Poverty Vulnerability, 20% weight)**: NBS Multidimensional Poverty Index ($0.0$ to $1.0$). High poverty + low connectivity = severe digital exclusion trap.
* $L_i$ **(Latency & Quality Deficit, 15% weight)**: High loaded latency ($>120\text{ ms}$) prevents modern video learning, telemedicine, and fintech transactions.

---

## 5. Design Consultation & Visual Aesthetics (Aesthetic System)

### Visual Philosophy: "Geospatial Intelligence Terminal"
A professional, modern GIS aesthetic inspired by Kepler.gl, Deck.gl, and Bloomberg Terminal:

1. **Color Palette**:
   * **Base Background**: Deep Obsidian/Space Cadet (`#0B0F19` and `#111827`) with glassmorphic cards (`rgba(30, 41, 59, 0.7)` with `backdrop-filter: blur(12px)`).
   * **Accent Cyan**: `#00F0FF` for primary actions, digital nodes, and highlights.
   * **Status / Choropleth Scale**:
     * High Performance / Digital Leader: `#10B981` (Emerald Teal)
     * Moderate / Transition Zone: `#F59E0B` (Vibrant Amber)
     * Severe Deficit / Digital Desert: `#EF4444` to `#991B1B` (Crimson Alert)
   * **Text Hierarchy**: Slate 100 (`#F8FAFC`) for primary headers, Slate 400 (`#94A3B8`) for metadata/labels.

2. **Typography**:
   * Font stack: Clean geometric sans-serif (`Inter`, `Plus Jakarta Sans`, system fallback).
   * Tabular figures (`font-variant-numeric: tabular-nums`) for coordinates, speeds, and indices so tables and numbers don't jitter.

3. **Dashboard Structure**:
   * **Hero KPI Ribbon**: National Average Download Speed, Coverage Disparity Ratio (Top 10% vs Bottom 10%), Total Population in Critical Priority LGAs, Top Priority LGA.
   * **Interactive Dual-Mode Map View**:
     * *Layer 1 (LGA Choropleth)*: Macro view of Nigeria shaded by DIPI priority or average speed.
     * *Layer 2 (Hexagonal/Tile Grid)*: Micro view of individual Ookla 610m tiles showing tests, download/upload, and latency.
   * **Filter & Drilldown Drawer**: Filter by Geopolitical Zone (SW, SE, SS, NC, NE, NW), State, and Priority Tier.
   * **LGA Inspector Card**: Hover or click an LGA to inspect demographic breakdown, speed stats, and customized USPF recommendation.
   * **Comparison & Policy Sandbox**: Compare any two LGAs side-by-side to understand why one thrives while another lags.

---

## 6. Engineering Review & Technical Architecture

### Priority Engineering Safeguards
1. **CRS Preservation**: Ensure all spatial operations explicitly operate on standard WGS84 (`EPSG:4326`) before projection or rendering.
2. **Deterministic Fallbacks**: If external API endpoints are offline, cache boundary data locally so the dashboard and pipeline run 100% offline.
3. **Optimized Spatial Joins**: Standard iterative loop over 9,234 tiles and 774 polygons takes minutes if unindexed. Using `geopandas.sjoin` with spatial index (R-tree) reduces spatial join execution to <2 seconds!
4. **Export Reproducibility**: The 2-page PDF deliverable must be completely generated via an automated script (`generate_submission_pdf.py`) with high-resolution map figures embedded, eliminating manual copy-pasting.

---

## 7. Actionable Hackathon Deliverables

### Deliverable A: Core Geospatial Pipeline (`etl_pipeline.py`)
- Downloads and normalizes Nigeria LGA boundaries and NBS poverty/population data.
- Executes spatial joins with `Nigeria Ookla.gpkg`.
- Computes DIPI score, spatial autocorrelation, and outputs `nigeria_digital_divide_master.geojson` and `.csv`.

### Deliverable B: Interactive Web Dashboard (`app.py`)
- Built with **Streamlit + Pydeck + Folium**.
- Interactive map layers (Speeds, Latency, DIPI Priority, Population at Risk).
- Rich KPI cards, Zone comparison charts, and dynamic filtering.

### Deliverable C: Automated 2-Page Submission PDF (`generate_submission_pdf.py`)
- Page 1: Executive Summary, Final Master Choropleth Map, Methodology, and Integrated Datasets.
- Page 2: Three Core Insights, Priority Target LGAs (Top 15), and Strategic Recommendations for NCC/USPF.

---

## 8. Verification & QA Plan

### Automated Pipeline Verification
```powershell
# 1. Run ETL and Spatial Processing
python src/etl_pipeline.py

# 2. Run Quality Checks on Spatial Data
python src/test_pipeline.py
# - Asserts 774 LGAs accounted for
# - Asserts 0 null or NaN in DIPI score
# - Validates speed ranges (0 to 200 Mbps)

# 3. Generate 2-Page PDF
python src/generate_submission_pdf.py
# - Verifies PDF page count == 2 exactly
```

### Manual Dashboard Verification
```powershell
# Launch Streamlit local dev server
streamlit run src/app.py
```
- Verify interactive map renders smoothly with basemap tiles.
- Verify filtering by State updates LGA drilldowns instantly.
- Test hover tooltips on Ookla tiles and LGA polygons.
