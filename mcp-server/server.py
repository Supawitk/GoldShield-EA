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

import csv as csv_mod
import json
import os
import sys
from datetime import datetime

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import query_rows

mcp = FastMCP("GoldShield")


def _serialize(rows: list[dict]) -> str:
    for row in rows:
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
    return json.dumps(rows, indent=2)


# ── Tools ────────────────────────────────────────────────────────────


@mcp.tool()
def get_recent_trades(limit: int = 20) -> str:
    """Return the most recent trades from the journal."""
    return _serialize(query_rows(
        "SELECT * FROM trades ORDER BY time DESC LIMIT %s", (limit,)
    ))


@mcp.tool()
def get_trade_stats(days: int = 30) -> str:
    """Aggregate win-rate, profit factor, and P&L over the last N days."""
    return _serialize(query_rows("""
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
    """, (days,)))


@mcp.tool()
def get_candles(hours: int = 100) -> str:
    """Return the most recent XAUUSD H1 candles."""
    return _serialize(query_rows("""
        SELECT time, open, high, low, close, volume
        FROM candles
        WHERE symbol = 'XAUUSD' AND timeframe = 'H1'
        ORDER BY time DESC LIMIT %s
    """, (hours,)))


@mcp.tool()
def compare_parameter_sets(limit: int = 10) -> str:
    """Compare EA parameter sets ranked by profit factor."""
    return _serialize(query_rows("""
        SELECT id, label, ema_fast, ema_slow, rsi_period,
               risk_percent, sl_atr_mult, tp_atr_mult,
               total_trades, win_rate, profit_factor,
               max_drawdown_pct, net_pnl, source
        FROM parameter_sets
        ORDER BY profit_factor DESC NULLS LAST
        LIMIT %s
    """, (limit,)))


@mcp.tool()
def suggest_parameters() -> str:
    """Return the best-performing parameter set as a starting point."""
    rows = query_rows("""
        SELECT * FROM parameter_sets
        WHERE total_trades >= 10
        ORDER BY profit_factor DESC NULLS LAST
        LIMIT 1
    """)
    if not rows:
        return json.dumps({"message": "Not enough data yet. Run more backtests."})
    return _serialize(rows[:1])


@mcp.tool()
def find_similar_conditions(hours_ago: int = 0, top_k: int = 5) -> str:
    """
    Find historical moments where market conditions were most similar,
    using pgvector cosine similarity on market_embeddings.
    If hours_ago=0, compares against the most recent embedding.
    """
    if hours_ago == 0:
        anchor = query_rows("""
            SELECT embedding FROM market_embeddings
            WHERE symbol = 'XAUUSD'
            ORDER BY time DESC LIMIT 1
        """)
    else:
        anchor = query_rows("""
            SELECT embedding FROM market_embeddings
            WHERE symbol = 'XAUUSD'
              AND time <= NOW() - INTERVAL '1 hour' * %s
            ORDER BY time DESC LIMIT 1
        """, (hours_ago,))

    if not anchor:
        return json.dumps({"message": "No embeddings found. Run: python scripts/generate_embeddings.py"})

    rows = query_rows("""
        SELECT time, symbol, timeframe, label,
               1 - (embedding <=> %s::vector) AS similarity
        FROM market_embeddings
        WHERE symbol = 'XAUUSD'
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (anchor[0]["embedding"], anchor[0]["embedding"], top_k + 1))

    results = [r for r in rows if r.get("similarity", 1) < 0.9999][:top_k]
    return _serialize(results)


@mcp.tool()
def export_csv(table: str = "trades", limit: int = 500) -> str:
    """
    Export a table as CSV to the exports/ directory.
    Supported tables: trades, candles, parameter_sets.
    """
    allowed = {
        "trades": "SELECT * FROM trades ORDER BY time DESC LIMIT %s",
        "candles": "SELECT * FROM candles WHERE symbol='XAUUSD' AND timeframe='H1' ORDER BY time DESC LIMIT %s",
        "parameter_sets": "SELECT * FROM parameter_sets ORDER BY created_at DESC LIMIT %s",
    }

    if table not in allowed:
        return json.dumps({"error": f"Table must be one of: {', '.join(allowed)}"})

    rows = query_rows(allowed[table], (limit,))
    if not rows:
        return json.dumps({"message": f"No data in {table}."})

    export_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
    os.makedirs(export_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(export_dir, f"{table}_{ts}.csv")

    with open(filepath, "w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v.isoformat() if isinstance(v, datetime) else v
                             for k, v in row.items()})

    return json.dumps({
        "file": os.path.abspath(filepath),
        "rows": len(rows),
        "table": table,
    }, indent=2)


@mcp.tool()
def run_sql(query: str) -> str:
    """Run a read-only SELECT query against the database."""
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        return json.dumps({"error": "Only SELECT queries are allowed."})
    return _serialize(query_rows(q)[:100])


if __name__ == "__main__":
    mcp.run(transport="stdio")
