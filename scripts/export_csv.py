#!/usr/bin/env python3
"""
Export database tables to CSV files.

Usage:
    python scripts/export_csv.py                    # export all tables
    python scripts/export_csv.py --table trades     # export trades only
    python scripts/export_csv.py --table candles --limit 1000
"""

import argparse
import csv
import os
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'goldshield')} "
    f"user={os.getenv('DB_USER', 'goldshield')} "
    f"password={os.getenv('DB_PASSWORD', 'goldshield_dev')}"
)

TABLES = {
    "trades":         "SELECT * FROM trades ORDER BY time DESC LIMIT %s",
    "candles":        "SELECT * FROM candles ORDER BY time DESC LIMIT %s",
    "parameter_sets": "SELECT * FROM parameter_sets ORDER BY created_at DESC LIMIT %s",
}


def export_table(table: str, limit: int, out_dir: str) -> str:
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(TABLES[table], (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    if not rows:
        print(f"  [{table}] No data.")
        return ""

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"{table}_{ts}.csv")

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v.isoformat() if isinstance(v, datetime) else v
                             for k, v in row.items()})

    print(f"  [{table}] {len(rows)} rows -> {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Export DB tables to CSV")
    parser.add_argument("--table", "-t", choices=list(TABLES.keys()),
                        help="Table to export (default: all)")
    parser.add_argument("--limit", "-l", type=int, default=5000,
                        help="Max rows per table (default: 5000)")
    args = parser.parse_args()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
    os.makedirs(out_dir, exist_ok=True)

    tables = [args.table] if args.table else list(TABLES.keys())
    print(f"Exporting to {out_dir}/ ...\n")
    for t in tables:
        export_table(t, args.limit, out_dir)
    print("\nDone.")


if __name__ == "__main__":
    main()
