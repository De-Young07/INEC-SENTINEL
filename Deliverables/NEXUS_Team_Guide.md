# NEXUS Team guide to SENTINEL

Prepared for Quadri Adebisi, Glory Akanbi, Gboyega Pelumi Stephen and Neneh Precious Egbo-Egbo on 21 October 2026. Speaking assignments below are suggestions, not claims about individual contributions.

## What we are presenting

We built a connectivity evidence and field-verification planner. The hackathon asks where connectivity improvements should be prioritized. Our contribution is to combine supplied Ookla observations with administrative boundaries and public-service locations, show both weak observations and missing evidence, and turn them into an affordable investigation plan. Electoral logistics is a motivating use case; health and education give it wider digital-inclusion relevance. SENTINEL does not conduct voting, transmit official results or certify BVAS readiness.

## How the data becomes a map

1. Read the supplied Nigeria Ookla GeoPackage. Its 9,234 rows contain coordinates, average download and upload speeds, latency and test counts. We convert kilobits per second to megabits per second by dividing by 1,000. We have not established the supplied extract's observation period or mobile/fixed provenance. The research notebook's Q4 2024 download is a different source and cannot establish those facts for our extract.
2. Standardize coordinates to EPSG:4326. Match each tile coordinate to the LGA polygon it intersects. This assigns 9,209 records and leaves 25 unmatched. Multiple candidates would use a stable sorted shapeID tie-break; this build found none. A tile coordinate match is not an area-weighted tile intersection.
3. Group matched records by LGA ID. Calculate unweighted tile means for download, upload and latency; sum test counts. A tile with many tests has the same weight in these means as a tile with few tests. We retain all 774 LGAs, including those without observations.
4. Match each LGA polygon to the state with the largest overlap. Calculate intersection areas in equal-area EPSG:6933, record the overlap percentage, and flag results below 95%. This build has no flagged state matches. This is a geometric assignment, not an official administrative certification.
5. Add GRID3 health facilities and HOT OSM education facilities. Remove missing/empty geometry and use a representative point for polygon records before assigning them to an LGA. GRID3 has 41,778 source rows: 6,004 lack usable geometry; 35,772 of 35,774 usable records match an LGA. Education has 6,329 usable records, of which 6,327 match. Counts describe source records, not independently verified operational facilities or polling units.
6. Prepare an evidence CSV, analytical GeoJSON, simplified display boundaries and source audit. Display simplification never alters the analytical geometry used for matching. Both apps share the same screening and planning code.

## How to explain the screening score

Upload deficit = clamp((2.5 minus mean upload Mbps) / 2.5, 0, 1).
Latency deficit = clamp((mean latency ms minus 50) / 200, 0, 1).
Score = 100 multiplied by (0.7 times upload deficit plus 0.3 times latency deficit).

Scores below 35 are lower observed concern, 35 to below 65 need review, and 65 or more are poor observed performance. Missing usable data stays unknown. These thresholds are transparent pilot assumptions, not validated telecom or election requirements. A score of 80 does not mean an 80% failure probability. Download speed is displayed for context but does not enter this score.

For visit planning, unknown areas receive verification priority 75, not a risk score. We rank candidates, then choose as many equal-cost initial LGA visits as budget and team capacity allow. This is not a travel-route optimizer or a capital investment optimization model.

## Three findings the whole team can explain

1. There are 234 LGAs with no matched tile observations, 30.2% of 774. Prioritize measurement in these gaps; do not call them disconnected. Of the other 540 LGAs, 520 are lower observed concern, 15 need review and 5 fall in the poor-observed-performance category.
2. The evidence-gap LGAs contain 10,308 matched GRID3 health records and 411 matched education records. These show why missing connectivity evidence matters for public services. Verify a sample of these locations with site managers and conduct repeated tests. These figures do not establish facility outages, unique beneficiaries or population coverage.
3. The five poor-performance LGAs are Madobi (Kano), Ezza South (Ebonyi), Doguwa (Kano), Rafi (Niger) and Edu (Kwara). Each has only one observed tile. Across observed LGAs, 355 of 540 have fewer than ten tiles. Repeat tests across locations, times and carriers before recommending infrastructure. Edu illustrates why download alone is inadequate: 15.129 Mbps download but only 0.084 Mbps upload in its single observed tile.

## What the notebook contributed

We adapted the ideas of administrative reconciliation, explicit matching audits, richer connectivity hover information and detailed location inspection. We did not copy its different download-based priority formula into our upload-oriented model. We did not import unverified population values or attach LGA averages to ward shapes as if they were ward measurements. Population-normalized deprivation and socioeconomic analysis remain future work; facility counts are a limited proxy for service need.

## Four minute demonstration

Suggested opening for Quadri: State the digital-inclusion problem, distinguish poor observations from missing evidence, and show the national map. Grey means unknown.

Suggested data explanation for Glory: Expand the matching audit. Explain 9,209 matched and 25 unmatched records. Search for Kano and hover over Madobi. Show state, download, upload, latency, tiles and tests. Click it to reveal the overlap-based state assignment and stable LGA ID.

Suggested analysis explanation for Gboyega: Search for Edu and explain the difference between download and upload. Change the map to evidence sample. Present the three quantified findings, including the single-tile limitation. Set a budget and visit capacity; explain that the plan pays for investigations, not promised connectivity improvements.

Suggested operations explanation for Neneh: Open Facilities and alerts, select a site and explain its historical nearest-tile context. Show the synthetic incident rehearsal separately from historical data. Close with a request for a small validation pilot and verified operational sites. These speaking roles can be reassigned by the team.

On mobile, tap an LGA and use its inspector; hover is a desktop enhancement. The Streamlit app has the same richer tooltip and LGA/state search, plus tables and downloads.

## Monitoring and deployment in plain language

Vercel hosts the custom web app and API. Supabase stores shared observations, incidents, acknowledgment history and notification outbox entries in a private schema. Three recent failed reports open an incident; two consecutive successful reports resolve it. Reports more than 15 minutes old are retained as history rather than changing current incident state. The browser refreshes every 15 seconds, but new data still needs a field submission or authorized probe. Demo and field incident state remain separate.

Hosted writes and field-history access require an operator token. Demo history is public. Do not put passwords, operator tokens, personal contact details or sensitive field notes into the submission. Streamlit remains a local interface. SMS/email adapters exist, but actual sending is disabled and requires approved recipients, provider credentials and a separate scheduled worker. A provider accepting a message does not prove a human received or acknowledged it.

## Questions judges may ask

Why not call grey areas blackouts? No speed test is evidence of an observation gap, not proof that service is absent.

Are the schools polling units? No. They are public-service location records. An official polling-unit register would need separate matching and validation.

How many people benefit? We cannot quantify that yet. Population and socioeconomic data were explored in the notebook but are not validated in this implementation.

What causes poor performance? The current data cannot establish congestion, backhaul failure, device faults or administrative causes. Site tests and operator cooperation are needed.

Is it real-time? Monitoring can accept fresh reports; historical maps are static evidence snapshots. No live nationwide operator feed is connected.

What makes it creative? It links historical observations, service-location needs, matching transparency, affordable verification planning and a shared incident workflow.

What remains before production? Individual operator identities, role-based permissions, operational agreements, tested alert delivery, load testing, updated source provenance and repeated field validation. The shared pilot token and serialized database writes are deliberate pilot limitations.

## Reproducing the submission

Install requirements-local.txt. Run python -m src.spatial_engine to rebuild evidence, then python -m unittest discover -s tests and python tests/check_app.py. Run the web app with python -m uvicorn src.web_api:app --port 8600 or Streamlit with python -m streamlit run src/app.py. The PDF and supporting CSV use the same screening categories and input evidence. Keep raw datasets in their existing locations. The challenge specifies a maximum two-page PDF; the longer guide is a team preparation resource, not extra submission pages.
