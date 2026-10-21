# Demonstrate SENTINEL in ten minutes

This walkthrough is for any teammate, including someone with no GIS or programming background. Ask the maintainer to start both applications first. You need a browser; no geospatial software is required.

## First result in three steps

1. Open `http://localhost:8600/`. The national map and evidence totals appear.
2. Type an LGA name in the search box or select one on the map. Its evidence appears in the inspector.
3. Change the visit budget. The proposed visits and estimated spending update. You have turned data into a resource-constrained action plan.

Say: “The colours summarize historical observations. Grey means insufficient evidence. Our next action is to verify conditions at real sites.”

## Explore and explain

Reset filters to restore the full country. Compare the observed-performance layer with the evidence-sample layer. A larger sample is more observations, not proof that the data is current. Bookmark two areas, enable bookmarked-only planning, and change team capacity. The shortlist must respect the budget and capacity; it does not estimate voters protected or new network coverage.

Save a comparison, alter the budget, and explain the difference. Download the shortlist CSV. Export the HTML briefing, open it, and use the browser's Print command to save a PDF. The report includes assumptions and limitations.

## Rehearse an incident

Open “Facilities & alerts.” Search a familiar clinic or school name, or select a record from the first page. Read its source, location, type and duplicate warning. These are source records, not verified polling units or confirmed operational facilities.

Click “Record failed demo test” three times, allowing each request to finish. An incident opens and two notification previews appear: one SMS and one email. Both say DEMO. No messages leave the system.

Enter an officer name and a concrete action such as “Check power and repeat on another carrier,” then acknowledge. The incident now has an owner and action note. This does not mean connectivity has recovered.

Click “Record successful demo test” twice. The incident resolves and recovery previews appear. Explain that the rule is illustrative. We demonstrate an evidence-to-action workflow, not actual failures at that facility.

Refresh the page. Records persist in the local database. The page also refreshes automatically every 15 seconds when visible, except while you are typing an incident response.

## Show the Streamlit version

Open the address printed by `Start SENTINEL.cmd` (normally `http://localhost:8502/` on this machine; check the launcher). The sidebar filters the map and visit plan. Use the numbered tabs: evidence, budget/briefing, and the original demo observation.

The original “Demo observation” tab saves session notes and gives a suggested next step. Those notes are separate from persistent monitoring. Open “Facilities & alerts” to search facilities in the selected LGA, record persistent demo tests, acknowledge incidents and inspect previews. The web and Streamlit operations screens share the database.

Say: “Streamlit helped us validate the analysis quickly. The dedicated web app gives us a more interactive workflow. Both use the same scoring functions, so we do not maintain competing formulas.”

## Three-minute judge demonstration

- 0:00–0:30: Introduce the provided Ookla data and the decision problem: where should teams verify connectivity first?
- 0:30–1:00: Show the map, a grey LGA and a measured LGA. Explain unknown versus poor evidence.
- 1:00–1:30: Set a visit budget, bookmark locations and export a shortlist.
- 1:30–2:30: Open a facility, record three DEMO failures, acknowledge the incident, then record two successes.
- 2:30–3:00: Explain that SMTP/SMS adapters are ready for configuration, actual sends remain disabled, and a partner pilot would validate the rules and data freshness.

Do not claim that the demo proves a real network outage, election readiness or lives/voters protected. Do not say every health record is a primary health centre or every education record is a school polling unit.

## Troubleshooting during a demo

- No facilities: ask the maintainer to run `python -m src.facilities`.
- No incident after three clicks: use the same facility; all three failures must be recent and consecutive. A success interrupts the streak.
- Incident remains acknowledged: two recent consecutive successful tests are required for recovery.
- Blank/failed requests: check that the server is running and reload. Do not substitute an old screenshot for current evidence without labelling it.
- No external message: expected in preview mode; show the outbox and explain the configuration boundary.

What you built: a reproducible demonstration that links historical evidence, resource planning, facility inspection and a traceable response workflow. For the full explanation see [TEAM_GUIDE.md](TEAM_GUIDE.md); for setup see [OPERATIONS.md](OPERATIONS.md).
