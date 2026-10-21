# SENTINEL technical reference

Read [the team explanation](TEAM_GUIDE.md), [the demo tutorial](TUTORIAL.md), and [the operating guide](OPERATIONS.md) for context and instructions.

## Components and persistence

- `src/spatial_engine.py`: offline evidence builder. Uses the local Ookla GeoPackage, LGA boundaries, GRID3 health and HOT education. Writes CSV, GeoJSON and a source audit.
- `src/readiness.py`: shared scoring, equal-cost visit allocation and escaped HTML brief generation.
- `src/facilities.py`: offline facility register builder. Adds HOT health, source attributes, representative locations, LGA assignments, nearest historical Ookla context and possible cross-source duplicates.
- `src/web_api.py`: FastAPI routes and static web hosting. Historical evidence and boundary geometries are cached until restart; facility CSV cache refreshes when the file modification timestamp changes.
- `src/app.py`: Streamlit interface. Uses the same analytical logic and monitoring database. Evidence caches use file modification timestamps.
- `src/monitoring.py`: SQLite observation history, incident state, acknowledgment audit and notification outbox.
- `src/delivery.py`: explicit SMTP/Twilio worker. Default preview only. `--watch` repeats every 15 seconds. Sends only field-mode entries.
- `src/probe.py`: synthetic 64 KiB upload test, timestamped field report and local retry queue. `--watch` waits 300 seconds after each cycle. One process per queue file.
- `web/index.html`, `app.js`, `style.css`: evidence map and visit planner.
- `web/monitor.html`, `monitor.js`, `monitor.css`: facility search, demo controls, incidents, and notification previews. Polls every 15 seconds while visible and not editing an incident form.
- `data/monitoring.sqlite3`: persistent local pilot database. Override with `SENTINEL_DB`. SQLite serializes writes; this is not a distributed database deployment.

## API routes

FastAPI's interactive schema at `/docs` is the complete machine-readable request reference.

- `GET /api/health`: status and LGA count; this is not a complete dependency health check.
- `GET /api/evidence`: all scored LGA rows. Unknown scores are JSON null.
- `GET /api/boundaries`: simplified LGA display geometry, tolerance 0.008 degrees. Analytical joins use original geometry.
- `POST /api/plan`: JSON budget (0–100 billion naira, default 5 million), cost_per_visit (1–1 billion, default 100,000), max_visits (0–774, default 20), optional ids (up to 774). Unknown IDs are rejected. Empty ids means empty scope.
- `POST /api/brief`: same input as plan; returns printable HTML with scenario assumptions.
- `GET /api/facilities`: q (literal name or site-ID substring, max 100 characters), source (exact source name), lga (shapeID), offset (nonnegative), limit (1–100, default 30). Returns total and items.
- `GET /api/sources`: generated source and facility audits.
- `GET /api/monitoring`: optional site_id filters observations and incidents. Returns latest 100 observations, incidents, notifications, and audit entries. Outbox and audit remain global. Includes server update time and delivery setting. This pilot read endpoint has no user authentication; keep it local until access controls are added.
- `POST /api/observations`: event_id (1–100 characters), site_id (1–150; must exist), mode (`demo` default or `field`), timezone-aware observed_at, success (boolean), seconds (finite, >0 and <=3600), carrier (up to 80, default Unspecified), note (up to 1000). Field writes require `X-Sentinel-Token`. An event ID is idempotent only when its contents match; conflicting reuse is rejected.
- `POST /api/incidents/{id}/acknowledge`: actor (2–100 characters), note (3–1000); whitespace-only values rejected. Field incidents require the token. Resolved incidents cannot be acknowledged. Saves actor label and action, but the shared-token pilot does not authenticate individual officer identities.
- `POST /api/probe-upload`: token required; accepts 1–262,144 bytes, discards the body, returns byte count and server time. No election records are expected or stored.

## Observation and incident rules

Times are normalized to UTC. Observation time is when the test occurred; received time is when the server accepted the report. Future timestamps more than 60 seconds ahead are rejected. Reports older than 15 minutes or no newer than the latest report for the same site/mode are stored as history only. They do not alter current incidents.

Three consecutive failed observations spanning no more than 15 minutes open one incident per site/mode. Repeated failures do not create repeated open incidents. Two consecutive successes within 15 minutes resolve an active incident. Acknowledgment records ownership and action; it does not imply recovery. These thresholds are demonstration rules, not an INEC standard or statistically validated reliability model.

The delivery worker adds one escalation for a field incident remaining open and unacknowledged after 15 minutes. It uses the same configured recipients; regional recipient routing is not implemented. Missing check-ins are displayed as stale when viewing a site, but do not currently generate automatic outage incidents.

## Outbox states

- `pending`: recorded, not submitted to a provider.
- `sending`: claimed by a worker before network submission.
- `provider_accepted`: SMTP or SMS provider accepted the request. Does not establish handset delivery, reading or acknowledgment.
- `review_required`: submission raised an error. A timeout may have happened after provider acceptance. Check the provider before retrying.

Demo entries remain previews regardless of the send setting. Workers claim field entries transactionally so concurrent workers cannot submit the same pending row. A crash after claim leaves `sending`; operators must reconcile it against provider records. There is no automatic retry of ambiguous sends and no delivery-receipt webhook yet. Provider credentials and recipients never appear in the public API.

## Environment variables

`.env.example` is a reference, not automatically loaded. Configure the server, probe and delivery-worker environments separately.

- `SENTINEL_DB`: database path; default project `data/monitoring.sqlite3`.
- `SENTINEL_INGEST_TOKEN`: operator/probe shared secret. Unset rejects field writes and upload tests.
- `SENTINEL_SEND`: only literal `1` enables external sends; default disabled.
- `SMTP_HOST`, `SMTP_PORT` (587 default), `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD`, `SENTINEL_EMAIL_TO`: SMTP with STARTTLS and login. One configured email destination.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `SENTINEL_SMS_TO`: Twilio Messages API adapter. One configured SMS destination; sender and destination must be permitted by the provider account and destination-country rules.

## Data identity and interpretation

Facility `site_id` is source name plus the GeoPackage feature identifier. `source_identifier` preserves the original registry/OSM identifier, which may repeat. IDs are reliable within these extracts; a new source release can renumber records, so reconcile identity before replacing a register that has monitoring history.

Potential duplicates use exact normalized names within approximately 200 metres between HOT health and GRID3. All records remain; the matcher does not prove distinctness when it finds no candidate. There are 914 candidates in the current build. No cross-source unique-facility total is claimed.

Source attribute values, including functionality and quality flags, are retained as supplied. Non-empty geometry is a technical acceptance criterion, not verification of positional accuracy. The 6,004 excluded GRID3 records require a separate coordinate-quality audit before any recovery.

## External integrations

SMTP and Twilio adapters are implemented. Real delivery has not been tested with provider credentials. OpenCellID, VIIRS, RIPE Atlas, ODK, DHIS2, operator telemetry and INEC interfaces are not connected. The supplied OpenCellID token is not embedded. No automatic remote baseline download or national live coverage is claimed.

Provider reference: https://www.twilio.com/docs/messaging/api/message-resource
