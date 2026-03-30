#!/usr/bin/env python3
"""
GoldShield MCP Server
─────────────────────
Exposes the PostgreSQL trade database to any MCP-compatible AI client
(Claude Desktop, Claude Code, etc.) so the AI can query performance,
analyse market data, and suggest EA parameter adjustments.

Run:
    python server.py
"""

import json
import os
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'goldshield')} "
    f"user={os.getenv('DB_USER', 'goldshield')} "
    f"password={os.getenv('DB_PASSWORD', 'goldshield_dev')}"
)

mcp = FastMCP("GoldShield")


def _query(sql: str, params: tuple = ()) -> list[dict]:
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()

    # Serialise datetime objects for JSON output
    for row in rows:
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
    return rows


# ── Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def get_recent_trades(limit: int = 20) -> str:
    """Return the most recent trades from the journal."""
    rows = _query(
        "SELECT * FROM trades ORDER BY time DESC LIMIT %s", (limit,)
    )
    return json.dumps(rows, indent=2)


@mcp.tool()
def get_trade_stats(days: int = 30) -> str:
    """Aggregate win-rate, profit factor, and P&L over the last N days."""
    rows = _query("""
        SELECT
            COUNT(*)                                        AS total_trades,
            ROUND(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0 END)::numeric, 4)
                                                            AS win_rate,
            ROUND((SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) /
                   NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0))::numeric, 2)
                                                            AS profit_factor,
            ROUND(SUM(pnl)::numeric, 2)                    AS net_pnl,
            ROUND(AVG(duration_mins)::numeric, 0)           AS avg_duration_mins
        FROM trades
        WHERE time > NOW() - INTERVAL '1 day' * %s
    """, (days,))
    return json.dumps(rows, indent=2)


@mcp.tool()
def get_candles(hours: int = 100) -> str:
    """Return the most recent XAUUSD H1 candles."""
    rows = _query("""
        SELECT time, open, high, low, close, volume
        FROM candles
        WHERE symbol = 'XAUUSD' AND timeframe = 'H1'
        ORDER BY time DESC
        LIMIT %s
    """, (hours,))
    return json.dumps(rows, indent=2)


@mcp.tool()
def compare_parameter_sets(limit: int = 10) -> str:
    """Compare EA parameter sets ranked by profit factor."""
    rows = _query("""
        SELECT id, label, ema_fast, ema_slow, rsi_period,
               risk_percent, sl_atr_mult, tp_atr_mult,
               total_trades, win_rate, profit_factor,
               max_drawdown_pct, net_pnl, source
        FROM parameter_sets
        ORDER BY profit_factor DESC NULLS LAST
        LIMIT %s
    """, (limit,))
    return json.dumps(rows, indent=2)


@mcp.tool()
def suggest_parameters() -> str:
    """
    Return the best-performing parameter set as a suggested starting
    point for the next EA configuration.
    """
    rows = _query("""
        SELECT * FROM parameter_sets
        WHERE total_trades >= 10
        ORDER BY profit_factor DESC NULLS LAST
        LIMIT 1
    """)
    if not rows:
        return json.dumps({"message": "Not enough data yet. Run more backtests."})
    return json.dumps(rows[0], indent=2)


@mcp.tool()
def run_sql(query: str) -> str:
    """
    Run a read-only SQL query against the database.
    Only SELECT statements are allowed.
    """
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed."})
    rows = _query(q)
    return json.dumps(rows[:100], indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
