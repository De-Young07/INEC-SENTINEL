# SENTINEL: the team's end-to-end explanation

Edition: 21 October 2026. Audience: every hackathon teammate, presenter and reviewer. This guide describes the implemented pilot, explains its reasoning in plain language, and separates measured evidence from demonstrations and future plans.

Read [the tutorial](TUTORIAL.md) for a live demonstration, [operations](OPERATIONS.md) for setup and alerts, and [reference](REFERENCE.md) for exact API details.

## 1. The project in one minute

SENTINEL helps teams decide where to investigate connectivity, plan affordable verification visits, and track problems at individual facilities. The hackathon supplied an Ookla dataset. We added administrative boundaries and health/education facility records, built spatial processing, designed interpretable screening rules, and created two interfaces: an initial Streamlit planner and a dedicated web application.

The latest implementation adds a facility register, persistent observation history, incident ownership and recovery, notification previews, email/SMS adapters and an optional synthetic-upload probe. Demonstration tests are always labelled DEMO and never sent externally. Field observations require a configured token. No real provider delivery has been performed during development.

Our creativity is the complete decision workflow: evidence → uncertainty → prioritized visits → facility inspection → measurement → incident → action → recovery. Merely combining more datasets would not establish that workflow.

## 2. The problem we can actually answer

Historical speed measurements can help identify places needing investigation. They cannot establish that a particular polling unit can transmit a result today. Facilities identify socially useful locations to assess, but their existence does not prove network demand, operating status or current service.

Our first question is: “Where should a team spend its limited verification budget?” Our second is: “Once a site is monitored, can we detect repeated upload problems and record a response?” The answers support planning and accountability. They do not certify electoral readiness, prove misconduct, predict election outcomes or replace an authorized election system.

## 3. The vocabulary everyone needs

- Geospatial data: information tied to locations on Earth.
- Coordinate: latitude and longitude describing a location. Longitude is east/west; latitude is north/south.
- Point: one location, such as a clinic. Polygon: an outline enclosing an area, such as an LGA. Raster: a grid of pixels, such as a satellite image.
- Tile: a geographic cell summarizing measurements. It is not a mobile tower or a verified place to upload.
- LGA: local government area. A stable identifier distinguishes areas that may share a name.
- Spatial join: assigning a point to the area that contains or intersects it. Imagine putting every clinic pin into its correct LGA folder.
- CRS: coordinate reference system. EPSG:4326 describes longitude/latitude in degrees; degrees are not kilometres.
- GeoPackage: a file that stores spatial tables. GeoJSON: a geographic JSON format. CSV: a spreadsheet-like text table.
- API: a structured way for software to request data or submit a record.
- Provenance: where a record came from and how it was processed.
- Idempotency: repeating the same report with the same identifier does not count it twice.
- Outbox: a persistent queue of messages waiting for delivery.

## 4. What data we used

Ookla was the provided dataset. The following counts describe the local extracts, not the total number of facilities or network observations in Nigeria.

- Ookla: 9,234 rows; 9,209 matched to an LGA, 25 unmatched. Upload, latency and test count feed the screening. Observation dates and fixed/mobile provenance have not been verified in the local extract.
- LGA boundaries: 774 areas used to organize the evidence. Shared-boundary cases are assigned deterministically by stable ID so one observation is not counted twice.
- GRID3 health: 41,778 source records, with 35,774 non-empty geometries. Of those, 35,772 matched the baseline LGA count. The 6,004 excluded records remain in the source file; we did not invent locations for them. Not every record is a primary health centre.
- HOT OSM education: 6,329 source records; 6,327 matched the baseline LGA count. This is not the separate GRID3 education dataset mentioned in the original guide, nor a complete national school census.
- HOT OSM health: 7,736 records, now included in the facility register. It supplements inspection and reconciliation; it is not added to GRID3 totals as if every record were a distinct clinic.

The register has 49,839 source records with non-empty geometry. It flags 914 potential GRID3/HOT health duplicates using exact normalized names within approximately 200 metres. It does not automatically merge them. A missing duplicate flag does not establish uniqueness.

The supplied OpenCellID resource is useful for future cellular context but is not connected in this build. Cell observations are not a complete tower inventory or live tower-status feed. The supplied nighttime-light version covers 1992–2020 at approximately 1 km resolution; it is not current power monitoring and has not been integrated. Meta relative wealth and population assets elsewhere in the folder are not used by the current scoring pipeline. Do not list them as implemented analytical inputs in the presentation.

## 5. How raw data becomes the evidence map

The evidence builder reads LGA polygons and standardizes their CRS. It reads Ookla upload, latency, tile coordinates and test counts. Upload values are converted from kilobits per second to megabits per second by dividing by 1,000.

Each tile coordinate becomes a point. A spatial join assigns it to an LGA. Where a point intersects two boundary polygons, stable-ID ordering chooses one assignment. We then group by LGA identifier and calculate observed tile count, mean upload, mean latency and total tests.

The averages are unweighted means of tile averages. A tile with many tests does not receive extra weight in the current mean. This is a transparent pilot choice, but it does not represent population-weighted experience or remove measurement selection bias.

Health and education geometries are converted to representative points where needed and assigned to LGAs. Representative points lie within the geometry; they are not validated entrances or GPS measurements. Missing observation metrics stay unknown. Facility counts are zero only when the available source contributes no matched records, not proof that no facilities exist.

The builder also finds proximity to a historical tile with upload at least 2.5 Mbps and latency below 80 ms. It converts coordinates to a three-dimensional unit sphere, finds the nearest point with a spatial search tree, then converts the chord to great-circle kilometres. The origin is an interior representative point of the LGA. This is neither road distance nor distance from every facility. The historical tile is not a verified accessible upload station.

Outputs are `sentinel_evidence.csv`, `sentinel_evidence.geojson` and `sentinel_sources.json`. Both interfaces read these outputs rather than repeating expensive spatial joins on every click.

## 6. The screening formula, with an example

We use two bounded deficits. “Bounded” means values are limited to the range zero to one.

Upload deficit = clamp((2.5 − mean upload Mbps) / 2.5, 0, 1).

Latency deficit = clamp((mean latency milliseconds − 50) / 200, 0, 1).

Screening score = 100 × (0.70 × upload deficit + 0.30 × latency deficit).

Example: an LGA with 1 Mbps upload and 150 ms latency has upload deficit 0.6 and latency deficit 0.5. Score = 100 × (0.70 × 0.6 + 0.30 × 0.5) = 57. This falls in “Review performance.” It does not mean a 57% probability of upload failure.

Categories: below 35 is lower observed concern; 35 to below 65 is review performance; 65 or higher is poor observed performance. An LGA without usable measurements remains unscored and grey. The current output contains 234 LGAs with no observed tiles.

“Larger sample” requires at least ten observed tiles and thirty tests. It does not establish statistical representativeness or freshness. Unknown areas receive verification priority 75 so they can receive field attention; 75 is an allocation policy, not an invented risk measurement.

The original blueprint proposed four weighted factors and a “feasibility” index where high values meant failure. We implemented a simpler, explicitly named screening score based on fields available in the actual extract. We did not implement alleged BVAS TCP-timeout thresholds, blackout fractions from absent tests, invented roaming benefits or fixed percentages of protected voters.

## 7. How the visit planner works

Users choose available budget, cost per visit and team capacity. The planner ranks LGAs by verification priority, breaks ties by stable ID and selects the highest priorities within all limits.

Visit count = minimum(eligible LGAs, team capacity, whole visits affordable from budget).

Example: a ₦500,000 budget, ₦100,000 per visit and capacity of three produces three visits, ₦300,000 estimated spend and ₦200,000 remaining. Equal visit cost makes ranking straightforward. If costs differ by area, a different optimization model is needed.

The shortlist proposes initial LGA verification visits. It does not allocate satellite terminals, select fibre routes or quantify social return on investment. Schools and clinics give context for the next investigation; they do not silently alter the current score.

## 8. Why we have two interfaces

Streamlit let us validate analytical logic quickly using Python. It includes filtering, a map, an evidence table, budget controls, downloadable scenarios and briefs, and session-based rehearsal notes. Its theme was corrected after contrast problems made the interface difficult to use.

The dedicated web app separates the browser interface from the Python service. It adds linked map/queue selection, pan and zoom, map colour layers, an inspector, browser-persistent bookmarks, plan comparisons, CSV downloads and printable briefs. It serves custom HTML, CSS and JavaScript, not a Streamlit page in a wrapper.

Both use `readiness.py`. Both now expose the facility register and persistent monitoring workflow. The original Streamlit rehearsal notes remain session-only; its new monitoring tab shares SQLite records with the web app. Web bookmarks and plan comparisons remain in that browser, not in shared team accounts.

## 9. What the new monitoring system does

The facility register provides source-based identity and context. Each facility also has a nearest historical Ookla tile, its straight-line distance, upload and latency. A nearby observation is context only: it is not a test at the facility, and its date and network type remain unverified. A report says which site was tested, when, whether the upload completed, how long it took, and the reporting mode. The server separately records receipt time.

DEMO reports are synthetic exercises. FIELD reports arrive through a token-protected API, either from the authorized reporting form or the optional probe; the label means submitted field evidence, not independent verification. A shared token cannot establish who physically stood at the site. Device enrollment, per-device credentials and identity validation are future deployment work.

Reports are saved in SQLite, a local database suitable for this pilot. Repeating an identical event ID does not add another report. Reusing an ID with different contents is rejected. Late reports remain available as history without changing the current incident state. Demo and field events never combine to satisfy a failure streak.

Three recent consecutive failures open an incident. Two recent consecutive successes record recovery. An officer can acknowledge an incident and record an action; this preserves a separate audit entry. Acknowledgment and recovery are different facts.

The system creates SMS and email entries when an incident opens and recovers. A separate worker handles sending and one escalation for a field incident left unacknowledged for fifteen minutes. Preview mode is the default. Even with sending enabled, demo entries never leave the application.

## 10. How actual measurements and alerts can travel

The optional probe runs on an authorized device. It uploads 64 KiB of synthetic bytes to SENTINEL's own endpoint. The server counts and discards them. The probe measures elapsed time, then submits a small report. It stores pending reports locally and retries them after connectivity returns. Use one process per queue file.

This measures the device-to-SENTINEL path. It does not test INEC's servers or authenticate a BVAS device. Power loss, endpoint errors, credentials and device faults can also produce failures. A complete outage prevents immediate reporting over the failed connection. The UI therefore calls old field reports stale; it does not claim that a missing report proves an outage.

The web monitoring page polls every fifteen seconds. The optional probe waits five minutes after each test cycle, and the worker checks every fifteen seconds. These are schedules, not a guaranteed end-to-end service level. Delay also includes network outages, retries, provider queues and recipient availability.

SMTP sends email using an encrypted STARTTLS session. The Twilio adapter submits SMS through its Messages API. Credentials and recipient destinations live in server-side environment variables. A provider-accepted status does not prove delivery or that a human has read or acted on a message. Ambiguous failures require provider reconciliation before retrying to avoid duplicate sends.

## 11. What stakeholders can reasonably take away

For an electoral operations team, the system can organize verification work around actual authorized sites once an authoritative polling-unit register is supplied. It does not provide official results transmission.

For health administrators, the facility register provides a starting point for choosing clinics to assess and monitor. For education teams, it does the same for educational records. For infrastructure planners, clusters can motivate investigation into shared demand, but commercial viability still needs operating status, costs, bandwidth demand and partner commitments.

ODK, DHIS2 and agency-dashboard integrations remain proposed. We have implemented the API boundary that can support adapters; we have not connected to those institutions. We also have not proved backhaul congestion from tower proximity, power availability from darkness, or causation from wealth/connectivity correlations.

## 12. What is finished and what remains

Implemented locally: evidence preparation, transparent scoring, constrained visit planning, both interfaces, searchable facility register, conservative duplicate flags, persistent observation/incident/audit/outbox storage, incident rehearsal and recovery, field ingestion token, synthetic probe with retry queue, SMTP/SMS adapters, worker escalation, source audit and this guide.

Requires configuration and partner testing: provider accounts, permitted sender and recipient, secure hosting, authorized site devices, current measurements, costs and calibrated alert thresholds. No live SMS/email has been sent or delivery verified in this development session.

Future engineering: PostgreSQL/PostGIS migration for distributed use, per-user/device authentication, access-controlled read APIs, rate limiting, recipient routing, verified delivery receipts, automatic heartbeat alerts, source-download scheduling, identity reconciliation across source releases, external integrations, backups/restore rehearsal and load testing. Docker packaging exists but has not been built or deployed here.

## 13. Questions judges may ask

“Why not treat untested areas as disconnected?” Because absence of observations does not establish absence of service. We prioritize verification instead.

“How did you know where the clinics belong?” We matched their coordinates to LGA polygons with a spatial join, recording unmatched rows separately.

“Are these all polling units?” No. These are facility datasets. Official polling-unit linkage requires authoritative records.

“Why are the health counts different?” Source rows, usable locations and matched locations are different totals. We expose that distinction and retain the audit.

“Is the system real-time?” The historical baseline is static. The new monitoring pipeline can accept repeated reports and refresh the interface. Its usefulness depends on deployed probes, recent observations and a working network.

“What did the team add beyond Ookla?” Administrative organization, facility context, uncertainty handling, a reproducible pipeline, actionable budget planning, a reusable API, interactive interfaces and an incident-response workflow.

“Can it scale nationally?” The separation of components supports evolution, but the current local SQLite pilot has not been nationally load-tested or secured for public deployment.

## 14. Source references and attribution

- Ookla open data documentation: https://github.com/teamookla/ookla-open-data
- GRID3 data portal: https://grid3.org/dataexplorer/
- HOT/HDX education catalog: https://data.humdata.org/dataset/hotosm_nga_education_facilities
- HOT/HDX health catalog: https://data.humdata.org/dataset/hotosm_nga_health_facilities
- OpenCellID download and attribution guidance: https://opencellid.org/downloads.php
- Exact supplied nighttime-light metadata: https://api.figshare.com/v2/articles/9828827/versions/5
- ODK integration documentation: https://docs.getodk.org/central-api/
- DHIS2 Nigeria case study: https://dhis2.org/nigeria-user-story/
- SMS adapter documentation: https://www.twilio.com/docs/messaging/api/message-resource

The local sources and generated audits are the basis for our counts. Verify individual source licences and required attribution before public redistribution. Do not describe downloaded records as personally surveyed or independently validated by the team.
