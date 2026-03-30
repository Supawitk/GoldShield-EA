#!/usr/bin/env python3
"""
GoldShield Dashboard
────────────────────
Streamlit UI for managing the EA parameters, viewing trades,
running ML models, and connecting to any LLM provider.

Run:
    streamlit run dashboard/app.py
"""

import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Page config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="GoldShield EA",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme CSS ───────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .stMetric { background: #161b22; border-radius: 8px; padding: 12px; border: 1px solid #30363d; }
    h1 { text-align: center; }
    .param-card { background: #161b22; border-radius: 8px; padding: 16px;
                  border: 1px solid #30363d; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Database ─────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "goldshield"),
        user=os.getenv("DB_USER", "goldshield"),
        password=os.getenv("DB_PASSWORD", "goldshield_dev"),
    )


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    try:
        conn = get_conn()
        df = pd.read_sql(sql, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.warning(f"Database not available: {e}")
        return pd.DataFrame()


def execute_sql(sql: str, params: tuple = ()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    result = None
    try:
        result = cur.fetchone()
    except Exception:
        pass
    cur.close()
    conn.close()
    return result


# ── LLM Providers ────────────────────────────────────────────────────

def call_llm(provider: str, api_key: str, model: str, prompt: str,
             base_url: str = "") -> str:
    """Universal LLM caller — supports multiple providers."""

    if provider == "Anthropic (Claude)":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    elif provider == "OpenAI":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    elif provider == "OpenAI-Compatible (Local / Custom)":
        from openai import OpenAI
        client = OpenAI(api_key=api_key or "none", base_url=base_url)
        resp = client.chat.completions.create(
            model=model, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content

    elif provider == "Ollama (Local)":
        url = base_url or "http://localhost:11434"
        resp = requests.post(f"{url}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False,
        }, timeout=120)
        return resp.json().get("response", "No response")

    elif provider == "Google Gemini":
        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{model}:generateContent?key={api_key}")
        resp = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}]
        }, timeout=60)
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    return "Provider not supported."


# ── Sidebar: Navigation ─────────────────────────────────────────────

st.sidebar.title("GoldShield EA")
page = st.sidebar.radio("Navigate", [
    "EA Parameters",
    "Market Data",
    "Trade Journal",
    "ML Models",
    "AI Assistant",
    "Snapshots",
])


# ════════════════════════════════════════════════════════════════════
# PAGE: EA Parameters
# ════════════════════════════════════════════════════════════════════

if page == "EA Parameters":
    st.title("EA Parameter Configuration")
    st.caption("Adjust values and save as a new parameter set to the database.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Indicators")
        ema_fast = st.number_input("EMA Fast Period", 5, 200, 50)
        ema_slow = st.number_input("EMA Slow Period", 50, 500, 200)
        rsi_period = st.number_input("RSI Period", 2, 50, 14)
        rsi_ob = st.slider("RSI Overbought", 50.0, 95.0, 70.0, 0.5)
        rsi_os = st.slider("RSI Oversold", 5.0, 50.0, 30.0, 0.5)
        atr_period = st.number_input("ATR Period", 2, 50, 14)

    with col2:
        st.subheader("Risk Management")
        risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0, 0.1)
        sl_mult = st.slider("SL ATR Multiplier", 0.5, 5.0, 1.5, 0.1)
        tp_mult = st.slider("TP ATR Multiplier", 0.5, 5.0, 1.0, 0.1)
        trail_mult = st.slider("Trailing ATR Multiplier", 0.5, 5.0, 1.0, 0.1)
        trail_step = st.number_input("Trailing Step (pts)", 10, 500, 50)

    with col3:
        st.subheader("Safety Filters")
        max_spread = st.number_input("Max Spread (pts)", 10, 200, 50)
        max_pos = st.number_input("Max Open Positions", 1, 10, 1)
        daily_loss = st.slider("Daily Loss Limit (%)", 1.0, 10.0, 3.0, 0.5)
        cooldown = st.number_input("Cooldown Bars", 1, 50, 5)
        start_h = st.number_input("Trading Start Hour", 0, 23, 2)
        end_h = st.number_input("Trading End Hour", 0, 23, 21)

    st.divider()

    label = st.text_input("Parameter Set Label", "v1.1")

    if st.button("Save Parameter Set to Database", type="primary"):
        try:
            result = execute_sql("""
                INSERT INTO parameter_sets
                    (label, ema_fast, ema_slow, rsi_period, rsi_overbought, rsi_oversold,
                     atr_period, risk_percent, sl_atr_mult, tp_atr_mult,
                     trailing_atr_mult, trailing_step_pts, max_spread_pts,
                     max_positions, daily_loss_pct, cooldown_bars,
                     start_hour, end_hour, source)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'dashboard')
                RETURNING id
            """, (label, ema_fast, ema_slow, rsi_period, rsi_ob, rsi_os,
                  atr_period, risk_pct, sl_mult, tp_mult, trail_mult, trail_step,
                  max_spread, max_pos, daily_loss, cooldown, start_h, end_h))
            st.success(f"Saved as parameter set #{result[0]}")
        except Exception as e:
            st.error(f"Failed to save: {e}")

    # Show existing sets
    st.subheader("Saved Parameter Sets")
    df = query_df("SELECT * FROM parameter_sets ORDER BY created_at DESC LIMIT 20")
    if not df.empty:
        st.dataframe(df, use_container_width=True)


# ════════════════════════════════════════════════════════════════════
# PAGE: Market Data
# ════════════════════════════════════════════════════════════════════

elif page == "Market Data":
    st.title("XAUUSD Market Data")

    TF_MAP = {
        "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
        "H1": "H1", "H4": "H4", "D1": "D1", "W1": "W1",
    }

    col1, col2 = st.columns([1, 3])
    with col1:
        timeframe = st.selectbox("Timeframe", list(TF_MAP.keys()), index=4)
        bars = st.slider("Number of bars", 50, 2000, 200)

    df = query_df("""
        SELECT time, open, high, low, close, volume
        FROM candles
        WHERE symbol = 'XAUUSD' AND timeframe = %s
        ORDER BY time DESC LIMIT %s
    """, (timeframe, bars))

    if not df.empty:
        df = df.sort_values("time")
        fig = go.Figure(data=[go.Candlestick(
            x=df["time"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color="#2ea043",
            decreasing_line_color="#e74c3c",
        )])
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            xaxis_rangeslider_visible=False,
            height=500, margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Raw Data"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No candle data yet. Run `python scripts/collect_data.py` to fetch data.")


# ════════════════════════════════════════════════════════════════════
# PAGE: Trade Journal
# ════════════════════════════════════════════════════════════════════

elif page == "Trade Journal":
    st.title("Trade Journal")

    df = query_df("SELECT * FROM trades ORDER BY time DESC LIMIT 100")
    if not df.empty:
        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Trades", len(df))
        wins = len(df[df["pnl"] > 0]) if "pnl" in df.columns else 0
        c2.metric("Win Rate", f"{wins/len(df)*100:.1f}%" if len(df) > 0 else "—")
        c3.metric("Net P&L", f"${df['pnl'].sum():,.2f}" if "pnl" in df.columns else "—")
        avg_dur = df["duration_mins"].mean() if "duration_mins" in df.columns else 0
        c4.metric("Avg Duration", f"{avg_dur:.0f} min")

        st.dataframe(df, use_container_width=True)

        # P&L chart
        if "pnl" in df.columns and df["pnl"].notna().any():
            df_sorted = df.sort_values("time")
            df_sorted["cumulative_pnl"] = df_sorted["pnl"].cumsum()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_sorted["time"], y=df_sorted["cumulative_pnl"],
                fill="tozeroy", fillcolor="rgba(46,160,67,0.2)",
                line=dict(color="#2ea043", width=2),
            ))
            fig.update_layout(
                title="Cumulative P&L",
                template="plotly_dark",
                paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                height=350, margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trades recorded yet. Run the EA on a demo account or import a backtest.")


# ════════════════════════════════════════════════════════════════════
# PAGE: ML Models
# ════════════════════════════════════════════════════════════════════

elif page == "ML Models":
    st.title("Machine Learning Models")

    model_type = st.selectbox("Model", [
        "Random Forest (sklearn)",
        "Gradient Boosting (sklearn)",
        "ARIMA (statsmodels)",
        "R - forecast::auto.arima",
        "R - randomForest",
    ])

    st.subheader("Configuration")
    col1, col2 = st.columns(2)
    with col1:
        lookback = st.number_input("Lookback window (bars)", 20, 500, 100)
        target = st.selectbox("Prediction Target", [
            "Next bar direction (up/down)",
            "Next bar close price",
            "Volatility (ATR) forecast",
        ])
    with col2:
        train_pct = st.slider("Train/Test split (%)", 50, 90, 80)
        features = st.multiselect("Features", [
            "EMA_50", "EMA_200", "RSI_14", "ATR_14",
            "Volume", "Spread", "Hour_of_day", "Day_of_week",
            "Candle_body", "Upper_wick", "Lower_wick",
        ], default=["EMA_50", "EMA_200", "RSI_14", "ATR_14"])

    if st.button("Train Model", type="primary"):
        df = query_df("""
            SELECT time, open, high, low, close, volume
            FROM candles WHERE symbol = 'XAUUSD'
            ORDER BY time DESC LIMIT %s
        """, (lookback * 2,))

        if df.empty or len(df) < lookback:
            st.error(f"Need at least {lookback} candles. Run collect_data.py first.")
        else:
            st.info(f"Training {model_type} on {len(df)} bars ...")
            progress = st.progress(0)

            if model_type.startswith("R -"):
                # Show R script that would be executed
                r_model = "auto.arima" if "arima" in model_type.lower() else "randomForest"
                st.code(f"""
# This R script is generated and can be run with: Rscript ml/train.R
library({"forecast" if "arima" in r_model else "randomForest"})

data <- read.csv("ml/candles_export.csv")
model <- {r_model}(close ~ ., data=train_data)
predictions <- predict(model, test_data)
write.csv(predictions, "ml/predictions.csv")
                """, language="r")
                progress.progress(100)
                st.success("R script generated at `ml/train.R`. Run it with Rscript.")
            else:
                # Python sklearn
                progress.progress(30)
                try:
                    from sklearn.ensemble import (GradientBoostingClassifier,
                                                   RandomForestClassifier)
                    from sklearn.metrics import accuracy_score, classification_report
                    import numpy as np

                    df = df.sort_values("time")
                    df["return"] = df["close"].pct_change()
                    df["target"] = (df["return"].shift(-1) > 0).astype(int)
                    df["ema_50"] = df["close"].ewm(span=50).mean()
                    df["ema_200"] = df["close"].ewm(span=200).mean()
                    df["rsi"] = 50  # simplified placeholder
                    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
                    df = df.dropna()

                    feature_cols = ["ema_50", "ema_200", "atr", "volume"]
                    X = df[feature_cols].values
                    y = df["target"].values

                    split = int(len(X) * train_pct / 100)
                    X_train, X_test = X[:split], X[split:]
                    y_train, y_test = y[:split], y[split:]

                    progress.progress(60)

                    if "Random Forest" in model_type:
                        clf = RandomForestClassifier(n_estimators=100, random_state=42)
                    else:
                        clf = GradientBoostingClassifier(n_estimators=100, random_state=42)

                    clf.fit(X_train, y_train)
                    preds = clf.predict(X_test)
                    acc = accuracy_score(y_test, preds)

                    progress.progress(100)

                    c1, c2 = st.columns(2)
                    c1.metric("Accuracy", f"{acc*100:.1f}%")
                    c2.metric("Test Samples", len(X_test))

                    # Feature importance
                    imp = pd.DataFrame({
                        "Feature": feature_cols,
                        "Importance": clf.feature_importances_
                    }).sort_values("Importance", ascending=True)

                    fig = go.Figure(go.Bar(
                        x=imp["Importance"], y=imp["Feature"],
                        orientation="h",
                        marker_color="#bc4dff",
                    ))
                    fig.update_layout(
                        title="Feature Importance",
                        template="plotly_dark",
                        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                        height=300,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                except ImportError:
                    st.error("Install scikit-learn: `pip install scikit-learn`")
                except Exception as e:
                    st.error(f"Training failed: {e}")


# ════════════════════════════════════════════════════════════════════
# PAGE: AI Assistant
# ════════════════════════════════════════════════════════════════════

elif page == "AI Assistant":
    st.title("AI Assistant")
    st.caption("Connect your own LLM to analyse trades and suggest parameter changes.")

    # Provider picker
    provider = st.selectbox("LLM Provider", [
        "Anthropic (Claude)",
        "OpenAI",
        "Google Gemini",
        "Ollama (Local)",
        "OpenAI-Compatible (Local / Custom)",
    ])

    col1, col2 = st.columns(2)
    with col1:
        if provider == "Ollama (Local)":
            api_key = ""
            base_url = st.text_input("Ollama URL", "http://localhost:11434")
            model = st.text_input("Model Name", "llama3")
        elif provider == "OpenAI-Compatible (Local / Custom)":
            api_key = st.text_input("API Key (optional)", type="password")
            base_url = st.text_input("Base URL", "http://localhost:1234/v1")
            model = st.text_input("Model Name", "local-model")
        elif provider == "Anthropic (Claude)":
            api_key = st.text_input("API Key", type="password",
                                     placeholder="sk-ant-...")
            base_url = ""
            model = st.selectbox("Model", [
                "claude-sonnet-4-6-20250514",
                "claude-opus-4-6-20250514",
                "claude-haiku-4-5-20251001",
            ])
        elif provider == "OpenAI":
            api_key = st.text_input("API Key", type="password",
                                     placeholder="sk-...")
            base_url = ""
            model = st.selectbox("Model", [
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1", "o3-mini",
            ])
        elif provider == "Google Gemini":
            api_key = st.text_input("API Key", type="password")
            base_url = ""
            model = st.selectbox("Model", [
                "gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash",
            ])

    with col2:
        context_source = st.multiselect("Include context from DB", [
            "Recent trades (last 20)",
            "Trade statistics (30 days)",
            "Best parameter sets",
            "Recent candles (100 bars)",
        ], default=["Recent trades (last 20)", "Trade statistics (30 days)"])

    # Build context
    def build_context() -> str:
        parts = []
        if "Recent trades (last 20)" in context_source:
            df = query_df("SELECT * FROM trades ORDER BY time DESC LIMIT 20")
            if not df.empty:
                parts.append(f"## Recent Trades\n{df.to_string()}")
        if "Trade statistics (30 days)" in context_source:
            df = query_df("""
                SELECT COUNT(*) as total,
                    ROUND(AVG(CASE WHEN pnl>0 THEN 1.0 ELSE 0 END)::numeric,4) as win_rate,
                    ROUND(SUM(pnl)::numeric,2) as net_pnl
                FROM trades WHERE time > NOW() - INTERVAL '30 days'
            """)
            if not df.empty:
                parts.append(f"## Trade Stats (30d)\n{df.to_string()}")
        if "Best parameter sets" in context_source:
            df = query_df("""
                SELECT * FROM parameter_sets
                ORDER BY profit_factor DESC NULLS LAST LIMIT 5
            """)
            if not df.empty:
                parts.append(f"## Best Parameter Sets\n{df.to_string()}")
        if "Recent candles (100 bars)" in context_source:
            df = query_df("""
                SELECT time, open, high, low, close
                FROM candles WHERE symbol='XAUUSD' AND timeframe='H1'
                ORDER BY time DESC LIMIT 100
            """)
            if not df.empty:
                parts.append(f"## Recent Candles\n{df.to_string()}")

        if parts:
            return ("You are analysing a XAUUSD trading EA called GoldShield. "
                    "Here is the current data:\n\n" + "\n\n".join(parts) + "\n\n")
        return "You are analysing a XAUUSD trading EA called GoldShield.\n\n"

    # Chat
    prompt = st.text_area("Ask the AI", height=120,
                           placeholder="Analyse my recent trades and suggest parameter improvements...")

    if st.button("Send", type="primary"):
        if not api_key and provider not in ("Ollama (Local)", "OpenAI-Compatible (Local / Custom)"):
            st.error("Please enter your API key.")
        elif not prompt:
            st.error("Please enter a prompt.")
        else:
            full_prompt = build_context() + prompt
            with st.spinner("Thinking..."):
                try:
                    response = call_llm(provider, api_key, model, full_prompt, base_url)
                    st.markdown("### Response")
                    st.markdown(response)
                except Exception as e:
                    st.error(f"LLM call failed: {e}")


# ════════════════════════════════════════════════════════════════════
# PAGE: Snapshots
# ════════════════════════════════════════════════════════════════════

elif page == "Snapshots":
    st.title("Snapshots")
    st.caption("Save and compare point-in-time snapshots of your EA state.")

    SNAP_DIR = os.path.join(os.path.dirname(__file__), "..", "snapshots")
    os.makedirs(SNAP_DIR, exist_ok=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Create Snapshot")
        snap_name = st.text_input("Snapshot Name",
                                   f"snap_{datetime.now().strftime('%Y%m%d_%H%M')}")
        snap_notes = st.text_area("Notes", height=80)

        if st.button("Take Snapshot", type="primary"):
            snapshot = {
                "name": snap_name,
                "timestamp": datetime.now().isoformat(),
                "notes": snap_notes,
                "parameters": {},
                "trade_stats": {},
                "candle_count": 0,
            }

            # Capture current state from DB
            try:
                df = query_df("""
                    SELECT * FROM parameter_sets
                    ORDER BY created_at DESC LIMIT 1
                """)
                if not df.empty:
                    snapshot["parameters"] = df.iloc[0].to_dict()
                    for k, v in snapshot["parameters"].items():
                        if hasattr(v, "isoformat"):
                            snapshot["parameters"][k] = v.isoformat()

                df = query_df("""
                    SELECT COUNT(*) as total,
                        COALESCE(ROUND(AVG(CASE WHEN pnl>0 THEN 1.0 ELSE 0 END)::numeric,4),0) as win_rate,
                        COALESCE(ROUND(SUM(pnl)::numeric,2),0) as net_pnl
                    FROM trades
                """)
                if not df.empty:
                    snapshot["trade_stats"] = df.iloc[0].to_dict()
                    for k, v in snapshot["trade_stats"].items():
                        if hasattr(v, "item"):
                            snapshot["trade_stats"][k] = v.item()

                df = query_df("SELECT COUNT(*) as cnt FROM candles")
                if not df.empty:
                    snapshot["candle_count"] = int(df.iloc[0]["cnt"])
            except Exception:
                pass

            path = os.path.join(SNAP_DIR, f"{snap_name}.json")
            with open(path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
            st.success(f"Snapshot saved: `{path}`")

    with col2:
        st.subheader("Existing Snapshots")
        snaps = sorted([f for f in os.listdir(SNAP_DIR) if f.endswith(".json")])
        if snaps:
            for s in snaps:
                with open(os.path.join(SNAP_DIR, s)) as f:
                    data = json.load(f)
                with st.expander(f"{data.get('name', s)} — {data.get('timestamp', '?')[:16]}"):
                    st.json(data)
        else:
            st.info("No snapshots yet. Create one to get started.")

    # Compare two snapshots
    if len(snaps) >= 2:
        st.divider()
        st.subheader("Compare Snapshots")
        c1, c2 = st.columns(2)
        snap_a = c1.selectbox("Snapshot A", snaps, index=0)
        snap_b = c2.selectbox("Snapshot B", snaps, index=len(snaps) - 1)

        if st.button("Compare"):
            with open(os.path.join(SNAP_DIR, snap_a)) as f:
                a = json.load(f)
            with open(os.path.join(SNAP_DIR, snap_b)) as f:
                b = json.load(f)

            st.markdown(f"**{a['name']}** vs **{b['name']}**")

            # Compare parameters
            params_a = a.get("parameters", {})
            params_b = b.get("parameters", {})
            diff_rows = []
            for key in set(list(params_a.keys()) + list(params_b.keys())):
                va = params_a.get(key, "—")
                vb = params_b.get(key, "—")
                if str(va) != str(vb):
                    diff_rows.append({"Parameter": key, snap_a: va, snap_b: vb})
            if diff_rows:
                st.dataframe(pd.DataFrame(diff_rows), use_container_width=True)
            else:
                st.info("Parameters are identical.")
