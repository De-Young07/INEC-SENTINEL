# SENTINEL: Electoral Transmission Readiness Pilot

Date: 20 October 2026
Status: Streamlit pilot retained; dedicated web workspace implemented following user approval on 21 October 2026. Formal design review remains incomplete.

## Accepted direction

Build a focused Streamlit prototype to validate electoral transmission readiness and contingency planning before scaling. A custom web application may be considered on 21 October if the team chooses it; this is an option, not a scheduled migration.

Subsequent decision: user requested a dedicated interactive web app. Implemented the frontend in `web/`, served by `src/web_api.py`, retaining the shared analytical core and the earlier Streamlit app. See `WEB_HANDOFF.md` for the current architecture, demo workflow and verification limits.

Primary workflow: inspect evidence → prioritize verification → compare interventions → export an actionable brief.

Primary pilot user: an electoral operations planner. The exact operational reviewer and pilot geography remain to be identified. NCC/operator investigation and USPF community connectivity planning are secondary uses.

## Existing foundation

Reuse src/spatial_engine.py, src/app.py, existing boundary files, Ookla observations, and facility datasets. Source already contains school and health joins, but inspected generated CSV lacks those columns. Reconcile generated outputs before presenting facility counts.

## Implementation sequence

1. Correct data semantics: missing observations remain unknown; aggregate by stable administrative identifiers; retain observation periods and source metadata; distinguish straight-line distance from routed travel distance. Document sampling limitations and verify mobile versus fixed dataset provenance.
2. Separate observed performance, evidence confidence, and intervention priority. Any composite score is an explicitly documented screening heuristic until calibrated. Schools remain community anchors unless matched to an authoritative polling-unit register.
3. Build the pilot workflow in Streamlit: evidence map, ranked verification queue, selected-location evidence inspector, budget scenario comparison, and executive briefing export. Do not represent school counts as polling-unit counts or population as voters.
4. Compare interventions using explicit assumptions, cost, capacity, deployment lead time, power and access constraints. Count each beneficiary site once. Do not hard-code improvement percentages as measured outcomes. Record remaining unmet needs.
5. Demonstrate one traceable rehearsal observation using a synthetic upload payload. Label all demonstration observations as simulated. Recompute the recommendation and explain the changed evidence.
6. Validate missing-data handling, aggregation identities, allocation constraints, site deduplication and reproducibility. Exercise the complete inspect-to-export workflow and confirm the briefing preserves sources and assumptions.

## Preserve a web application migration path

Keep Streamlit calls in the UI layer. Put data loading, scoring, allocation and export preparation in plain Python modules accepting explicit inputs and returning serializable tables or records. Use stable IDs and versioned data contracts. Store scenario assumptions as structured records rather than only session state. Cache by input version and scenario parameters. Avoid introducing a separate API server or frontend before needed.

A later web UI can consume the same analytical functions through a thin API adapter. This reduces rework but does not eliminate frontend, authentication, deployment or integration effort.

## Proposed design direction — pending review

Desktop: a readable 2D map beside a ranked action list, with a selected-location inspector. Optional 3D overview is secondary. Distinguish unknown evidence from measured poor performance through labels and patterns as well as colour. Keep source dates and assumption status visible. Use a restrained dark interface and a light print layout. Detailed layout, responsive behaviour and state handling are not yet approved.

## Stakeholder pilot proposition

Offer a bounded pilot with an authoritative site list and an operational reviewer. Deliver a verification shortlist, transparent intervention comparison and exportable decision brief. Evaluate field usefulness and ranking changes rather than claiming nationwide election-day reliability.

## Open decisions

- Pilot geography, site register availability and operational reviewer.
- Hackathon deadline, available implementation time and team responsibilities.
- Detailed screen layout, evidence states, responsive behaviour and scenario interaction.
- Availability of field observations, realistic intervention costs and deployment constraints.

## Implemented pilot and scope limits

The current app includes filtered LGA evidence, a 2D boundary map, an LGA inspector, equal-cost verification-visit allocation, saved-plan comparison, printable HTML briefs, CSV evidence and JSON scenario export, and session-only synthetic rehearsal notes. Unknown measurements remain unscored. The pipeline uses stable boundary IDs, great-circle proximity and facility match auditing. Analytical functions are separate from Streamlit.

Infrastructure allocation is intentionally deferred: this version allocates verification visits rather than satellite/tower coverage. Synthetic rehearsals update a suggested next action but do not change historical evidence or LGA rankings. No authoritative site-level readiness claim, road route or direct PDF generation is implemented. Print the HTML brief to PDF in the browser. A custom frontend remains optional.

## GSTACK REVIEW REPORT

| Review | Runs | Status | Findings |
|---|---:|---|---|
| Office hours | 1, in progress | Direction and approach accepted | Streamlit pilot approved; custom web application remains optional |
| Plan design review | 0 completed | Pending | Preliminary observations only; no completed seven-pass review |
| Engineering review | 0 | Not performed | Architecture and implementation require verification |

VERDICT: Approach approved; detailed design and implementation are not cleared by a completed review.

**UNRESOLVED DECISIONS:**
- Confirm pilot geography, evidence availability, layout and interaction details before treating the detailed design as approved.
