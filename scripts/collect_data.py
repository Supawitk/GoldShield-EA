#!/usr/bin/env python3
"""
Fetch XAUUSD H1 candles from Twelve Data and store them in PostgreSQL.

Usage:
    python collect_data.py                  # fetch latest 500 bars
    python collect_data.py --days 30        # fetch last 30 days
"""

import argparse
import os
from datetime import datetime, timedelta, timezone

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

DB_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'goldshield')} "
    f"user={os.getenv('DB_USER', 'goldshield')} "
    f"password={os.getenv('DB_PASSWORD', 'goldshield_dev')}"
)

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
SYMBOL = "XAU/USD"
INTERVAL = "1h"


def fetch_candles(output_size: int = 500) -> list[dict]:
    """Fetch candles from Twelve Data API."""
    if not API_KEY:
        raise SystemExit(
            "TWELVE_DATA_API_KEY not set. "
            "Get a free key at https://twelvedata.com and add it to .env"
        )

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": output_size,
        "apikey": API_KEY,
        "format": "JSON",
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "values" not in data:
        raise SystemExit(f"API error: {data.get('message', data)}")

    return data["values"]


def store_candles(candles: list[dict]) -> int:
    """Insert candles into the database (skip duplicates)."""
    sql = """
        INSERT INTO candles (time, open, high, low, close, volume, symbol, timeframe)
        VALUES (%s, %s, %s, %s, %s, %s, 'XAUUSD', 'H1')
        ON CONFLICT DO NOTHING
    """

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    rows = 0
    for c in candles:
        cur.execute(sql, (
            c["datetime"],
            float(c["open"]),
            float(c["high"]),
            float(c["low"]),
            float(c["close"]),
            float(c.get("volume", 0)),
        ))
        rows += cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description="Collect XAUUSD candles")
    parser.add_argument("--days", type=int, default=0,
                        help="Fetch this many days of history (max ~5000 bars)")
    args = parser.parse_args()

    output_size = min(max(args.days * 24, 500), 5000) if args.days else 500

    print(f"Fetching {output_size} candles from Twelve Data ...")
    candles = fetch_candles(output_size)
    print(f"Got {len(candles)} candles. Storing ...")

    inserted = store_candles(candles)
    print(f"Done — {inserted} new rows inserted.")


if __name__ == "__main__":
    main()
