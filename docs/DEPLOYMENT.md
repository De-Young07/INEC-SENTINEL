# Deployment status — 21 October 2026

Repository: https://github.com/De-Young07/INEC-SENTINEL
Web app: https://inec-sentinel-omega.vercel.app
Supabase project: INEC SENTINEL (swtndffgcebilfhxditq), INEC's org.

The web app runs on Vercel with server-side PostgreSQL access through the
Supabase transaction pooler. Four monitoring tables live in the private sentinel
schema with RLS enabled. Public Supabase client roles have no schema access.
The restricted runtime login can select, insert and update records, but cannot
delete them. Its credentials are configured as sensitive Vercel environment values.
SENTINEL_SEND remains 0: no external SMS or email delivery is enabled.

A synthetic commissioning rehearsal through the local FastAPI test client against
the managed database persisted five demo observations, opened an incident,
acknowledged it and resolved it. Reopening the database confirmed persistence.
Duplicate suppression and rejection of unauthenticated hosted writes passed.
These records are labelled synthetic; they are not field measurements.

The operator token remains in the Git-ignored .env.deploy file. Enter the value of
SENTINEL_INGEST_TOKEN into the monitoring page and select Refresh now. Do not share
that file, commit it, or place its contents in presentation slides. The temporary
database administrator password has been cleared after setup. The runtime login
and operator token remain available locally for the team operating this pilot.

Vercel deployments currently use the authenticated CLI. Automatic GitHub deployment
is not connected: Vercel reported insufficient repository access. Grant the Vercel
GitHub integration access to De-Young07/INEC-SENTINEL before expecting push-to-deploy.
Streamlit is available from the repository and runs locally with requirements-local.txt;
it is not hosted on Vercel.

Live browser verification is still blocked by a saved browser permission setting,
even after the user approved a retry. Build readiness and database/API test results
must not be described as a verified live browser workflow. Update the browser's
permission for the Vercel site before performing that check.

An external scheduled delivery worker, provider credentials and approved recipients
are still required before enabling real SMS/email alerts. Historical datasets remain
historical; fresh observations require field submissions or authorized probes.
