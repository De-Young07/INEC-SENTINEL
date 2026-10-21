# SENTINEL handoff — 21 October 2026

The primary interface runs on localhost:8600. The original Streamlit planner remains available through its launcher. See [team documentation](docs/TEAM_GUIDE.md) and [operations](docs/OPERATIONS.md).

## Implemented this iteration

- Reproducible 49,839-record facility register using GRID3 health, HOT health and HOT education.
- Source identifiers preserved separately from unique extract record IDs; 914 possible health-source duplicates flagged, never automatically merged.
- Nearest historical Ookla tile distance/performance context, explicitly not a facility measurement.
- Facility search, pagination, source filters and LGA-scoped links from the web map.
- SQLite observation history, separated demo/field streams, idempotent reports, late-event handling, incident ownership, audit and recovery.
- Email/SMS outbox, safe preview default, SMTP STARTTLS/Twilio adapters, explicit worker and one unacknowledged-field-incident escalation.
- Token-protected field ingestion and bounded synthetic-upload endpoint; optional probe with local retry queue.
- Shared Streamlit operations tab and combined printable team handbook.

## Verification evidence

- `python -m unittest discover -s tests`: 20 passing tests, including field auth, upload size limits, duplicates, late events, mode isolation, incident lifecycle, escalation and mocked delivery acceptance/failure.
- `python tests/check_app.py`: initial render, zero budget, original rehearsal and empty filters passed.
- JavaScript syntax checks passed for app.js and monitor.js.
- Browser: facility selection, three synthetic failures, incident acknowledgment and action note, two successes, resolved state and notification previews verified. No console errors in that workflow.
- Real providers were not contacted. SMTP/Twilio credentials and approved recipients remain unconfigured.

## Operational limits

No public deployment, Docker build, national load test, per-device identity, provider delivery receipts, automated missing-heartbeat alerts or remote source refresh has been verified/implemented. The UI freshness check marks old field observations stale. Future source releases require identifier reconciliation before replacing records referenced by monitoring history.

## Maintainer learnings

GRID3 unique_id and HOT source IDs can repeat. Pyogrio can expose GeoPackage feature IDs through fid_as_index=True, rather than treating OBJECTID as an ordinary column. Source record IDs are extract-scoped, not guaranteed stable across future releases. On Windows, sandboxed API TestClient can stall on event-loop sockets; the tests pass in an unrestricted local terminal.
