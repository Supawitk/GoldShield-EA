#!/usr/bin/env python3
"""
Parse an MT5 Strategy Tester HTML report and insert trades + stats
into the GoldShield database.

Usage:
    python backtest_logger.py report.html            # log with default params
    python backtest_logger.py report.html --label v2  # tag the parameter set
"""

import argparse
import os
import re
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'goldshield')} "
    f"user={os.getenv('DB_USER', 'goldshield')} "
    f"password={os.getenv('DB_PASSWORD', 'goldshield_dev')}"
)


def parse_summary(html: str) -> dict:
    """Extract key metrics from MT5 report HTML."""
    def find(pattern: str, default="0"):
        m = re.search(pattern, html)
        return m.group(1) if m else default

    return {
        "total_trades":     int(find(r"Total Trades.*?(\d+)")),
        "profit_factor":    float(find(r"Profit Factor.*?([\d.]+)")),
        "max_drawdown_pct": float(find(r"Maximal Drawdown.*?([\d.]+)\s*%")),
        "net_pnl":          float(find(r"Total Net Profit.*?([-\d.\s]+)").replace(" ", "")),
        "win_rate":         float(find(r"Win Rate.*?([\d.]+)")) / 100,
        "sharpe_ratio":     float(find(r"Sharpe Ratio.*?([-\d.]+)")),
    }


def insert_param_set(cur, label: str, stats: dict) -> int:
    """Insert a parameter_set row and return its ID."""
    cur.execute("""
        INSERT INTO parameter_sets (label, total_trades, win_rate,
            profit_factor, max_drawdown_pct, sharpe_ratio, net_pnl, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'backtest')
        RETURNING id
    """, (
        label,
        stats["total_trades"],
        stats["win_rate"],
        stats["profit_factor"],
        stats["max_drawdown_pct"],
        stats["sharpe_ratio"],
        stats["net_pnl"],
    ))
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Log MT5 backtest report")
    parser.add_argument("report", help="Path to MT5 HTML report file")
    parser.add_argument("--label", default="default", help="Label for this run")
    args = parser.parse_args()

    with open(args.report, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    stats = parse_summary(html)
    print(f"Parsed: {stats}")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    pid = insert_param_set(cur, args.label, stats)
    conn.commit()
    cur.close()
    conn.close()

    print(f"Saved as parameter_set #{pid}")


if __name__ == "__main__":
    main()
