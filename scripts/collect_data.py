#!/usr/bin/env python3
"""
Fetch XAUUSD candles from Twelve Data and store them in PostgreSQL.
Supports multiple timeframes.

Usage:
    python collect_data.py                          # H1, latest 500 bars
    python collect_data.py --days 30                # H1, last 30 days
    python collect_data.py --timeframe 15min        # 15-minute bars
    python collect_data.py --timeframe 4h --days 90 # 4-hour, last 90 days
    python collect_data.py --all-timeframes         # fetch all timeframes
"""

import argparse
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import db_cursor

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
SYMBOL = "XAU/USD"

TIMEFRAMES = {
    "1min":  {"interval": "1min",  "label": "M1",  "bars_per_day": 1440},
    "5min":  {"interval": "5min",  "label": "M5",  "bars_per_day": 288},
    "15min": {"interval": "15min", "label": "M15", "bars_per_day": 96},
    "30min": {"interval": "30min", "label": "M30", "bars_per_day": 48},
    "1h":    {"interval": "1h",    "label": "H1",  "bars_per_day": 24},
    "4h":    {"interval": "4h",    "label": "H4",  "bars_per_day": 6},
    "1day":  {"interval": "1day",  "label": "D1",  "bars_per_day": 1},
    "1week": {"interval": "1week", "label": "W1",  "bars_per_day": 0.143},
}


def fetch_candles(interval: str, output_size: int = 500) -> list[dict]:
    if not API_KEY:
        raise SystemExit(
            "TWELVE_DATA_API_KEY not set. "
            "Get a free key at https://twelvedata.com and add it to .env"
        )

    resp = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": SYMBOL, "interval": interval,
        "outputsize": min(output_size, 5000),
        "apikey": API_KEY, "format": "JSON",
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "values" not in data:
        raise SystemExit(f"API error: {data.get('message', data)}")
    return data["values"]


def store_candles(candles: list[dict], timeframe_label: str) -> int:
    sql = """
        INSERT INTO candles (time, open, high, low, close, volume, symbol, timeframe)
        VALUES (%s, %s, %s, %s, %s, %s, 'XAUUSD', %s)
        ON CONFLICT (time, symbol, timeframe) DO NOTHING
    """
    rows = 0
    with db_cursor() as cur:
        for c in candles:
            cur.execute(sql, (
                c["datetime"], float(c["open"]), float(c["high"]),
                float(c["low"]), float(c["close"]),
                float(c.get("volume", 0)), timeframe_label,
            ))
            rows += cur.rowcount
    return rows


def collect_timeframe(tf_key: str, days: int):
    tf = TIMEFRAMES[tf_key]
    output_size = max(int(days * tf["bars_per_day"]), 500) if days else 500
    output_size = min(output_size, 5000)

    print(f"  [{tf['label']}] Fetching {output_size} bars ...")
    candles = fetch_candles(tf["interval"], output_size)
    inserted = store_candles(candles, tf["label"])
    print(f"  [{tf['label']}] {len(candles)} fetched, {inserted} new rows inserted.")
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Collect XAUUSD candles")
    parser.add_argument("--days", type=int, default=0)
    parser.add_argument("--timeframe", "-tf", default="1h",
                        choices=list(TIMEFRAMES.keys()))
    parser.add_argument("--all-timeframes", action="store_true")
    args = parser.parse_args()

    if args.all_timeframes:
        print("Fetching all timeframes ...\n")
        total = sum(collect_timeframe(k, args.days) for k in TIMEFRAMES)
        print(f"\nDone — {total} total new rows.")
    else:
        print(f"Fetching {args.timeframe} candles ...\n")
        collect_timeframe(args.timeframe, args.days)
        print("\nDone.")


if __name__ == "__main__":
    main()
