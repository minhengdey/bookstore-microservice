"""Poll PostgreSQL until named tables exist (used by worker entrypoints)."""
import os
import sys
import time

import psycopg2


def main() -> int:
    tables = [t.strip() for t in os.environ.get("WAIT_FOR_TABLE", "").split(",") if t.strip()]
    if not tables:
        return 0

    conn_params = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "postgres"),
        "dbname": os.environ.get("DB_NAME", "postgres"),
    }
    timeout = int(os.environ.get("WAIT_FOR_TABLE_TIMEOUT", "300"))
    interval = float(os.environ.get("WAIT_FOR_TABLE_INTERVAL", "2"))

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with psycopg2.connect(**conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' AND tablename = ANY(%s)",
                        (tables,),
                    )
                    found = {row[0] for row in cur.fetchall()}
            missing = [t for t in tables if t not in found]
            if not missing:
                print(f"All tables ready: {', '.join(tables)}")
                return 0
            print(f"Waiting for tables: {', '.join(missing)}")
        except Exception as exc:
            print(f"DB check failed: {exc}")
        time.sleep(interval)

    print(f"Timeout waiting for tables: {', '.join(tables)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
