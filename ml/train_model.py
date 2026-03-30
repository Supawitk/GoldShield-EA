#!/usr/bin/env python3
"""
Train ML models on XAUUSD candle data from the GoldShield database.
Supports multiple sklearn models and exports results back to DB.

Usage:
    python ml/train_model.py                              # Random Forest, default
    python ml/train_model.py --model gradient_boosting    # Gradient Boosting
    python ml/train_model.py --model logistic             # Logistic Regression
    python ml/train_model.py --lookback 200 --split 75    # custom params
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_DSN = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'goldshield')} "
    f"user={os.getenv('DB_USER', 'goldshield')} "
    f"password={os.getenv('DB_PASSWORD', 'goldshield_dev')}"
)

MODELS = {
    "random_forest":      "RandomForestClassifier",
    "gradient_boosting":  "GradientBoostingClassifier",
    "logistic":           "LogisticRegression",
    "svm":                "SVC",
    "knn":                "KNeighborsClassifier",
}


def load_candles(lookback: int) -> pd.DataFrame:
    conn = psycopg2.connect(DB_DSN)
    df = pd.read_sql("""
        SELECT time, open, high, low, close, volume
        FROM candles
        WHERE symbol = 'XAUUSD' AND timeframe = 'H1'
        ORDER BY time ASC
    """, conn)
    conn.close()

    if len(df) < lookback:
        raise SystemExit(
            f"Need at least {lookback} candles, got {len(df)}. "
            "Run: python scripts/collect_data.py --days 90"
        )
    return df.tail(lookback * 2).reset_index(drop=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create technical indicator features from OHLCV data."""
    df = df.copy()
    df["return"] = df["close"].pct_change()
    df["target"] = (df["return"].shift(-1) > 0).astype(int)

    # EMAs
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["ema_ratio"] = df["ema_50"] / df["ema_200"]

    # RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR
    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift(1)),
            abs(df["low"] - df["close"].shift(1))
        )
    )
    df["atr"] = df["tr"].rolling(14).mean()

    # Candle features
    df["body"] = abs(df["close"] - df["open"])
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    # Time features
    df["hour"] = pd.to_datetime(df["time"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["time"]).dt.dayofweek

    # Momentum
    df["momentum_5"] = df["close"].pct_change(5)
    df["momentum_10"] = df["close"].pct_change(10)

    return df.dropna()


def train(model_name: str, df: pd.DataFrame, split_pct: int):
    """Train and evaluate the selected model."""
    feature_cols = [
        "ema_ratio", "rsi", "atr", "body", "upper_wick", "lower_wick",
        "hour", "day_of_week", "momentum_5", "momentum_10", "volume",
    ]

    X = df[feature_cols].values
    y = df["target"].values

    split = int(len(X) * split_pct / 100)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Import the right model
    if model_name == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_name == "gradient_boosting":
        from sklearn.ensemble import GradientBoostingClassifier
        clf = GradientBoostingClassifier(n_estimators=100, random_state=42)
    elif model_name == "logistic":
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        clf = LogisticRegression(max_iter=1000, random_state=42)
    elif model_name == "svm":
        from sklearn.svm import SVC
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        clf = SVC(kernel="rbf", random_state=42)
    elif model_name == "knn":
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        clf = KNeighborsClassifier(n_neighbors=5)
    else:
        raise SystemExit(f"Unknown model: {model_name}")

    clf.fit(X_train, y_train)

    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    preds = clf.predict(X_test)
    results = {
        "model": model_name,
        "accuracy": round(accuracy_score(y_test, preds), 4),
        "precision": round(precision_score(y_test, preds, zero_division=0), 4),
        "recall": round(recall_score(y_test, preds, zero_division=0), 4),
        "f1": round(f1_score(y_test, preds, zero_division=0), 4),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "features": feature_cols,
    }

    # Feature importance (if available)
    if hasattr(clf, "feature_importances_"):
        imp = dict(zip(feature_cols, [round(float(v), 4) for v in clf.feature_importances_]))
        results["feature_importance"] = dict(sorted(imp.items(), key=lambda x: -x[1]))

    return results


def export_for_r(df: pd.DataFrame):
    """Export candle data as CSV for R scripts."""
    out = os.path.join(os.path.dirname(__file__), "candles_export.csv")
    df.to_csv(out, index=False)
    print(f"Exported {len(df)} rows to {out} (for R scripts)")


def main():
    parser = argparse.ArgumentParser(description="Train ML model on XAUUSD data")
    parser.add_argument("--model", "-m", default="random_forest",
                        choices=list(MODELS.keys()),
                        help="Model to train")
    parser.add_argument("--lookback", type=int, default=200,
                        help="Number of bars to use")
    parser.add_argument("--split", type=int, default=80,
                        help="Train/test split percentage")
    parser.add_argument("--export-r", action="store_true",
                        help="Also export CSV for R scripts")
    args = parser.parse_args()

    print(f"Loading candles (lookback={args.lookback}) ...")
    df = load_candles(args.lookback)

    print("Engineering features ...")
    df = engineer_features(df)
    print(f"  {len(df)} samples after feature engineering")

    if args.export_r:
        export_for_r(df)

    print(f"Training {MODELS[args.model]} ...")
    results = train(args.model, df, args.split)

    print(f"\n{'='*50}")
    print(f"  Model:     {results['model']}")
    print(f"  Accuracy:  {results['accuracy']*100:.1f}%")
    print(f"  Precision: {results['precision']*100:.1f}%")
    print(f"  Recall:    {results['recall']*100:.1f}%")
    print(f"  F1 Score:  {results['f1']*100:.1f}%")
    print(f"  Train/Test: {results['train_samples']} / {results['test_samples']}")
    print(f"{'='*50}")

    if "feature_importance" in results:
        print("\n  Feature Importance:")
        for feat, imp in results["feature_importance"].items():
            bar = "#" * int(imp * 50)
            print(f"    {feat:18s} {imp:.4f}  {bar}")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
