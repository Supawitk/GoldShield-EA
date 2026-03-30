#!/usr/bin/env python3
"""
Train ML models on XAUUSD candle data from the GoldShield database.

Usage:
    python ml/train_model.py                              # Random Forest
    python ml/train_model.py --model gradient_boosting    # Gradient Boosting
    python ml/train_model.py --model logistic             # Logistic Regression
    python ml/train_model.py --lookback 200 --split 75    # custom params
    python ml/train_model.py --export-r                   # export CSV for R
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import query_rows

MODELS = {
    "random_forest":      "RandomForestClassifier",
    "gradient_boosting":  "GradientBoostingClassifier",
    "logistic":           "LogisticRegression",
    "svm":                "SVC",
    "knn":                "KNeighborsClassifier",
}


def load_candles(lookback: int) -> pd.DataFrame:
    rows = query_rows("""
        SELECT time, open, high, low, close, volume
        FROM candles
        WHERE symbol = 'XAUUSD' AND timeframe = 'H1'
        ORDER BY time ASC
    """)
    df = pd.DataFrame(rows)

    if len(df) < lookback:
        raise SystemExit(
            f"Need at least {lookback} candles, got {len(df)}. "
            "Run: python scripts/collect_data.py --days 90"
        )
    return df.tail(lookback * 2).reset_index(drop=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["return"] = df["close"].pct_change()
    df["target"] = (df["return"].shift(-1) > 0).astype(int)

    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["ema_ratio"] = df["ema_50"] / df["ema_200"]

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift(1)),
            abs(df["low"] - df["close"].shift(1))
        )
    )
    df["atr"] = df["tr"].rolling(14).mean()

    df["body"] = abs(df["close"] - df["open"])
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    df["hour"] = pd.to_datetime(df["time"]).dt.hour
    df["day_of_week"] = pd.to_datetime(df["time"]).dt.dayofweek

    df["momentum_5"] = df["close"].pct_change(5)
    df["momentum_10"] = df["close"].pct_change(10)

    return df.dropna()


def train(model_name: str, df: pd.DataFrame, split_pct: int):
    feature_cols = [
        "ema_ratio", "rsi", "atr", "body", "upper_wick", "lower_wick",
        "hour", "day_of_week", "momentum_5", "momentum_10", "volume",
    ]

    X = df[feature_cols].values
    y = df["target"].values

    split = int(len(X) * split_pct / 100)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    needs_scaling = model_name in ("logistic", "svm", "knn")
    if needs_scaling:
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

    if model_name == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_name == "gradient_boosting":
        from sklearn.ensemble import GradientBoostingClassifier
        clf = GradientBoostingClassifier(n_estimators=100, random_state=42)
    elif model_name == "logistic":
        from sklearn.linear_model import LogisticRegression
        clf = LogisticRegression(max_iter=1000, random_state=42)
    elif model_name == "svm":
        from sklearn.svm import SVC
        clf = SVC(kernel="rbf", random_state=42)
    elif model_name == "knn":
        from sklearn.neighbors import KNeighborsClassifier
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

    if hasattr(clf, "feature_importances_"):
        imp = dict(zip(feature_cols, [round(float(v), 4) for v in clf.feature_importances_]))
        results["feature_importance"] = dict(sorted(imp.items(), key=lambda x: -x[1]))

    return results


def export_for_r(df: pd.DataFrame):
    out = os.path.join(os.path.dirname(__file__), "candles_export.csv")
    df.to_csv(out, index=False)
    print(f"Exported {len(df)} rows to {out} (for R scripts)")


def main():
    parser = argparse.ArgumentParser(description="Train ML model on XAUUSD data")
    parser.add_argument("--model", "-m", default="random_forest",
                        choices=list(MODELS.keys()))
    parser.add_argument("--lookback", type=int, default=200)
    parser.add_argument("--split", type=int, default=80)
    parser.add_argument("--export-r", action="store_true")
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

    out_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
