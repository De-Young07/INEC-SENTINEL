# How to run, refresh and operate SENTINEL

Read [the tutorial](TUTORIAL.md) first for the user workflow. [Reference](REFERENCE.md) lists all fields and environment settings. [The team guide](TEAM_GUIDE.md) explains the data and claims.

## How to start both interfaces

Use Python 3.11 and a terminal opened in the project folder. The downloaded source GeoPackages and boundary GeoJSON must be present for rebuilding. Existing prepared files are sufficient to run the apps.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn src.web_api:app --host 127.0.0.1 --port 8600
```

Open `http://localhost:8600/` for the web app. `Start SENTINEL Web.cmd` is a double-click alternative. In a second terminal:

```powershell
python -m streamlit run src/app.py --server.port 8502
```

Open `http://localhost:8502/`. The existing `Start SENTINEL.cmd` does not explicitly set a port, so its console may show 8501 or another available port. Use the printed address. The new operations tab links to the web server on 8600.

If the port is occupied, stop the existing instance in its terminal before starting a replacement. Do not terminate unrelated Python or notebook processes. Both apps must use the same database path to share monitoring history.

## How to rebuild evidence and facilities

Preserve the original files and source attribution. Inspect a new release before replacing an extract. Especially check identifiers: feature IDs may change between releases, so a register refresh must not silently attach old observations to a different facility.

```powershell
python src/spatial_engine.py
python -m src.facilities
```

The first command rebuilds LGA evidence and its audit. The second rebuilds the register and duplicate-candidate audit. Check `data/sentinel_sources.json` and `data/facilities_audit.json`. Restart FastAPI to refresh its historical evidence cache. The register itself is reloaded when its file timestamp changes.

These commands process local extracts. They do not download new remote source releases automatically. Review changed counts, unmatched locations, source licence and observation date before accepting an update. A download date is not the measurement date.

If a source file is missing, restore it at the path named in the error. If a source schema changes, update the builder deliberately and rerun the tests. Do not replace unknown measurements with zero speed.

## How to rehearse without sending messages

Keep `SENTINEL_SEND` unset or `0`. Open `/monitor.html`, choose a facility and record three failed demo tests. Acknowledge the incident and record two successful demo tests. All rows remain visibly DEMO. Review the SMS/email previews. The worker also refuses demo entries even if sending is enabled.

```powershell
python -m src.delivery
```

Without send configuration, this returns a preview-only status and sends nothing. It can still queue an escalation for eligible field incidents. Tests use temporary databases and mocked providers, not real recipients.

## How to configure authorized field reporting

Set a strong `SENTINEL_INGEST_TOKEN` in the API server environment and on each authorized probe. Do not put it in frontend JavaScript or a committed file. This version uses one shared token; individual-device enrollment is future work. The `.env.example` file documents names but is not automatically loaded.

For a manual report, open Facilities & alerts, select a facility, switch Reporting mode to Authorized field report, and enter the configured operator token, measured seconds, carrier and context. Submit the actual success/failure outcome. The form does not perform a network test and timestamps the report now; use the API for earlier observations. The same token enables field-incident acknowledgment. It is kept only in the current page, cleared when returning to demo mode, and never saved in browser storage.

For an automated probe, choose an actual registered site ID from the interface. Verify that the device is physically at the intended site and that the facility has agreed to the test. With the token already set securely in the process environment:

```powershell
python -m src.probe --site GRID3:65 --carrier "Pilot carrier"
```

`GRID3:65` is an example register ID, not a recommendation to deploy at that facility. Replace it with the agreed site. The command performs one 64 KiB synthetic upload to the default localhost server and queues/submits a field report. Localhost tests validate software only, not external connectivity.

For an authorized hosted pilot, supply `--url https://your-approved-server` and `--watch`. HTTPS is required except for localhost. The loop waits 300 seconds between cycles. Use `--queue` to give each probe its own writable queue file. Do not run two probes against one queue.

The queue survives temporary network failure. Reports retain original test times; old reports do not rewrite current incidents. If queued_reports grows, check connectivity, server availability, token and site ID. Do not discard reports to hide a failure. The queue stops collecting at 10,000 pending reports until the issue is resolved.

## How to enable email or SMS delivery

First obtain an authorized destination and a configured provider account. For email, configure SMTP_HOST, SMTP_PORT, SMTP_FROM, SMTP_USER, SMTP_PASSWORD and SENTINEL_EMAIL_TO in the worker environment. The adapter uses STARTTLS and authentication; it does not support a plaintext relay or implicit-TLS port 465 in this version.

For SMS, configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM and SENTINEL_SMS_TO. Verify sender availability, country permissions, destination format and account/trial restrictions with the provider. Actual delivery costs are provider-specific and are not part of the visit budget.

Only when the team has approved the destination and sending purpose, set `SENTINEL_SEND=1` in the worker environment and run:

```powershell
python -m src.delivery --watch
```

The worker processes up to 25 pending field messages per channel per cycle. It will also process old pending field notifications: inspect the outbox before enabling sends. The initial adapter uses one destination per channel; it does not automatically know which commissioner or LGA officer should receive a message.

Verification requires a controlled field-mode test, checking provider acceptance, actual recipient receipt, and operator acknowledgment separately. None of those external delivery checks has been performed here because provider credentials and approved recipients have not been configured.

## How to handle delivery failures

If messages stay pending, confirm the worker is running, sending is enabled and every required variable for that channel is present. The worker and API may have different environment variables; the dashboard's delivery label reflects the API process, not proof that a worker is running.

If status is review_required, inspect the provider console without copying credentials into logs. A timeout can happen after acceptance; do not blindly retry. A crashed worker may leave sending. Reconcile that entry with provider history before a maintainer changes its status. The pilot intentionally has no one-click retry for ambiguous submissions.

Provider_accepted means the provider accepted a request. SMS delivery receipts and email bounce handling are not implemented. Operator acknowledgment is recorded in SENTINEL separately. A missed fifteen-minute acknowledgment queues one escalation to the same configured destinations.

## How to protect and back up the pilot

Keep the server bound to localhost for demonstrations. Before shared/public hosting, add user authentication, read authorization, per-device credentials, rate limits, TLS termination, audit access policies and a retention policy. The current public read endpoints and unauthenticated demo controls are intended for a local pilot.

Stop the apps and worker before making a simple file copy of `data/monitoring.sqlite3`; retain source snapshots and prepared data alongside it. Restore-test a backup before relying on it. Do not store the database on an unreliable network share. A container needs a persistent data volume; otherwise recreating it can lose monitoring history. The supplied Dockerfile is packaging preparation, not a verified deployment.

## How to verify changes

```powershell
python -m unittest discover -s tests
python tests/check_app.py
node --check web/app.js
node --check web/monitor.js
```

Unit/API tests cover scoring, budgets, unknown semantics, endpoint validation, persistence rules and mocked delivery. Streamlit checks cover initial render, zero budget, session rehearsal and empty filters. Browser verification should cover facility selection, three failures, acknowledgment, two successes, retained history, empty search and readable layouts.

On this Windows environment, API tests may need an unrestricted local terminal because sandbox socket restrictions can block the test event loop. A hanging sandbox test does not itself prove an application defect.

## How to regenerate the printable team guide

```powershell
python -m src.build_guide
```

This combines the four Markdown documents into `web/guide.html`. Open `/guide.html` and print to PDF. The Markdown documents remain the editable source. Update both the guide and implemented-status notes whenever features change.
