#!/usr/bin/env python3
"""
Generate market condition embeddings from XAUUSD candle data
and store them in the market_embeddings table (pgvector).

Each embedding is a 128-dim vector capturing the "shape" of a
window of bars: normalized OHLCV ratios, technical indicators,
and candle structure — enabling cosine similarity search for
historically similar market conditions.

Usage:
    python scripts/generate_embeddings.py               # default: H1, 50-bar windows
    python scripts/generate_embeddings.py --window 100   # 100-bar windows
    python scripts/generate_embeddings.py --step 5       # every 5 bars (less overlap)
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import db_cursor, query_rows

EMBEDDING_DIM = 128


def load_candles(timeframe: str = "H1", limit: int = 5000) -> list[dict]:
    return query_rows("""
        SELECT time, open, high, low, close, volume
        FROM candles
        WHERE symbol = 'XAUUSD' AND timeframe = %s
        ORDER BY time ASC
        LIMIT %s
    """, (timeframe, limit))


def build_embedding(window: list[dict]) -> list[float]:
    """
    Build a 128-dim embedding from a window of candle bars.

    Features per bar (5): normalized close change, body ratio,
    upper wick ratio, lower wick ratio, volume z-score.
    Aggregates (remaining dims): rolling stats, momentum, volatility.
    """
    closes = np.array([c["close"] for c in window], dtype=np.float64)
    opens = np.array([c["open"] for c in window], dtype=np.float64)
    highs = np.array([c["high"] for c in window], dtype=np.float64)
    lows = np.array([c["low"] for c in window], dtype=np.float64)
    volumes = np.array([c["volume"] for c in window], dtype=np.float64)

    n = len(window)
    features = []

    # 1. Normalized returns (n-1 values, pad to fill)
    returns = np.diff(closes) / (closes[:-1] + 1e-10)
    features.extend(returns.tolist())

    # 2. Body ratios (body / range)
    ranges = highs - lows + 1e-10
    bodies = (closes - opens) / ranges
    features.extend(bodies.tolist())

    # 3. Upper wick ratios
    upper_wicks = (highs - np.maximum(opens, closes)) / ranges
    features.extend(upper_wicks.tolist())

    # 4. Aggregate stats
    features.append(float(np.mean(returns)))        # avg return
    features.append(float(np.std(returns)))          # volatility
    features.append(float(np.mean(bodies)))          # avg body direction
    features.append(float(np.std(bodies)))           # body variation

    # 5. Momentum at different scales
    for period in [5, 10, 20]:
        if n > period:
            features.append(float((closes[-1] - closes[-period-1]) / (closes[-period-1] + 1e-10)))
        else:
            features.append(0.0)

    # 6. Simple RSI approximation
    if len(returns) > 0:
        gains = np.mean(returns[returns > 0]) if np.any(returns > 0) else 0
        losses = -np.mean(returns[returns < 0]) if np.any(returns < 0) else 1e-10
        features.append(float(gains / (gains + losses + 1e-10)))

    # 7. Volume trend
    if len(volumes) > 1 and np.std(volumes) > 0:
        features.append(float((volumes[-1] - np.mean(volumes)) / (np.std(volumes) + 1e-10)))
    else:
        features.append(0.0)

    # Pad or truncate to exactly EMBEDDING_DIM
    features = features[:EMBEDDING_DIM]
    while len(features) < EMBEDDING_DIM:
        features.append(0.0)

    # Normalize to unit vector (cosine similarity works best this way)
    arr = np.array(features, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm

    return arr.tolist()


def label_regime(window: list[dict]) -> str:
    """Simple regime label based on overall direction and volatility."""
    closes = [c["close"] for c in window]
    ret = (closes[-1] - closes[0]) / (closes[0] + 1e-10)
    returns = np.diff(closes) / (np.array(closes[:-1]) + 1e-10)
    vol = float(np.std(returns))

    if abs(ret) < 0.005:
        direction = "sideways"
    elif ret > 0:
        direction = "bullish"
    else:
        direction = "bearish"

    volatility = "high_vol" if vol > 0.005 else "low_vol"
    return f"{direction}_{volatility}"


def main():
    parser = argparse.ArgumentParser(description="Generate market embeddings")
    parser.add_argument("--window", "-w", type=int, default=50,
                        help="Window size in bars (default: 50)")
    parser.add_argument("--step", "-s", type=int, default=10,
                        help="Step between windows (default: 10)")
    parser.add_argument("--timeframe", "-tf", default="H1")
    parser.add_argument("--limit", type=int, default=5000,
                        help="Max candles to load")
    args = parser.parse_args()

    print(f"Loading {args.timeframe} candles ...")
    candles = load_candles(args.timeframe, args.limit)

    if len(candles) < args.window:
        raise SystemExit(
            f"Need at least {args.window} candles, got {len(candles)}. "
            "Run: python scripts/collect_data.py --days 90"
        )

    print(f"  {len(candles)} candles loaded")
    print(f"  Generating embeddings (window={args.window}, step={args.step}) ...")

    inserted = 0
    with db_cursor() as cur:
        for i in range(0, len(candles) - args.window + 1, args.step):
            window = candles[i:i + args.window]
            embedding = build_embedding(window)
            label = label_regime(window)
            end_time = window[-1]["time"]

            cur.execute("""
                INSERT INTO market_embeddings
                    (time, symbol, timeframe, window_bars, embedding, label)
                VALUES (%s, 'XAUUSD', %s, %s, %s::vector, %s)
                ON CONFLICT DO NOTHING
            """, (end_time, args.timeframe, args.window,
                  str(embedding), label))
            inserted += cur.rowcount

    print(f"  {inserted} embeddings inserted.")
    print("Done. Use MCP tool 'find_similar_conditions' to search.")


if __name__ == "__main__":
    main()
