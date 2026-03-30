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
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import db_cursor


def parse_summary(html: str) -> dict:
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


def main():
    parser = argparse.ArgumentParser(description="Log MT5 backtest report")
    parser.add_argument("report", help="Path to MT5 HTML report file")
    parser.add_argument("--label", default="default")
    args = parser.parse_args()

    with open(args.report, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    stats = parse_summary(html)
    print(f"Parsed: {stats}")

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO parameter_sets
                (label, total_trades, win_rate, profit_factor,
                 max_drawdown_pct, sharpe_ratio, net_pnl, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'backtest')
            RETURNING id
        """, (args.label, stats["total_trades"], stats["win_rate"],
              stats["profit_factor"], stats["max_drawdown_pct"],
              stats["sharpe_ratio"], stats["net_pnl"]))
        pid = cur.fetchone()[0]

    print(f"Saved as parameter_set #{pid}")


if __name__ == "__main__":
    main()
