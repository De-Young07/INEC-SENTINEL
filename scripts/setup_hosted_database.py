"""Provision the named pilot project from a local, ignored setup credential.
Run explicitly after saving SUPABASE_DB_PASSWORD in .env.deploy.
Never prints connection URIs or passwords. Re-running retains runtime credentials.
"""
import os
import secrets
from pathlib import Path
from urllib.parse import quote
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
REF = "swtndffgcebilfhxditq"
HOST = "aws-0-eu-west-1.pooler.supabase.com"

def values():
    return dict(line.split("=", 1) for line in (ROOT / ".env.deploy").read_text().splitlines() if "=" in line and not line.startswith("#"))

def main():
    config = values()
    password = config.get("SUPABASE_DB_PASSWORD", "").strip()
    if not password:
        raise SystemExit("Save the new project's database password in .env.deploy first.")
    runtime = config.get("SENTINEL_RUNTIME_PASSWORD") or secrets.token_urlsafe(36)
    token = config.get("SENTINEL_INGEST_TOKEN") or secrets.token_urlsafe(36)
    with psycopg.connect(host=HOST, port=6543, dbname="postgres", user="postgres."+REF,
                          password=password, sslmode="require", connect_timeout=15,
                          prepare_threshold=None) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='sentinel_runtime'").fetchone():
            conn.execute(sql.SQL("CREATE ROLE sentinel_runtime LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION").format(sql.Literal(runtime)))
        elif not config.get("SENTINEL_RUNTIME_PASSWORD"):
            raise RuntimeError("Existing runtime role found; supply its existing credential rather than resetting it.")
        if not conn.execute("SELECT to_regclass('sentinel.observations')").fetchone()[0]:
            conn.execute((ROOT / "sql/schema.sql").read_text())
            conn.execute((ROOT / "sql/runtime_grants.sql").read_text())
    uri = f"postgresql://sentinel_runtime.{REF}:{quote(runtime, safe='')}@{HOST}:6543/postgres?sslmode=require"
    # Preserve setup credential locally until successful end-to-end verification.
    config.update(SENTINEL_RUNTIME_PASSWORD=runtime, SENTINEL_INGEST_TOKEN=token, DATABASE_URL=uri, SENTINEL_SEND="0")
    (ROOT / ".env.deploy").write_text("# LOCAL SECRET FILE - excluded from Git and Vercel uploads\n" + "\n".join(k+"="+v for k,v in config.items())+"\n")
    with psycopg.connect(uri, prepare_threshold=None, connect_timeout=15) as conn:
        count = conn.execute("SELECT count(*) FROM sentinel.observations").fetchone()[0]
        assert not conn.execute("SELECT has_table_privilege(current_user, 'sentinel.observations', 'DELETE')").fetchone()[0]
    print(f"Private monitoring schema configured; runtime login verified; {count} observations.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Provider errors can contain connection details. Keep console output redacted.
        raise SystemExit("Database setup failed: " + type(exc).__name__ + ". Check credential and connectivity; no secret values printed.")
