"""Applies db/migrations/*.sql to the Supabase database, in order, each exactly once.

Usage (from the repo root):
    uv run --with "psycopg[binary]" python db/migrate.py

Reads POSTGRES_URL_NON_POOLING from the environment or engine/.env.local
(fill it with: cd engine && npx vercel env pull .env.local --environment production).
"""

import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT.parent / "engine" / ".env.local"


def database_url() -> str:
    if url := os.environ.get("POSTGRES_URL_NON_POOLING"):
        return url
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("POSTGRES_URL_NON_POOLING="):
                return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit(f"POSTGRES_URL_NON_POOLING is not set and not found in {ENV_FILE}.")


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        conn.execute("create table if not exists schema_migrations (name text primary key, applied_at timestamptz not null default now())")
        conn.execute("alter table schema_migrations enable row level security")  # hide it from Supabase's public API
        applied = {row[0] for row in conn.execute("select name from schema_migrations")}
        pending = [p for p in sorted((ROOT / "migrations").glob("*.sql")) if p.name not in applied]
        if not pending:
            print("Database is up to date.")
        for path in pending:
            # Each file runs in its own transaction, so a failing file leaves nothing half applied.
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("insert into schema_migrations (name) values (%s)", (path.name,))
            print(f"Applied {path.name}")
        if pending:
            # Supabase's API caches the schema; without this, new functions return 404 for a while.
            conn.execute("notify pgrst, 'reload schema'")


if __name__ == "__main__":
    main()
