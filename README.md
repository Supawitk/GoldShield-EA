<p align="center">
  <img src="https://img.icons8.com/3d-fluency/94/shield.png" width="80" alt="shield"/>
</p>

<h1 align="center">GoldShield EA</h1>

<p align="center">
  <strong>Safety-First XAUUSD Expert Advisor with AI-Ready Data Pipeline</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-MetaTrader_5-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTMgM2gxOHYxOEgzVjN6Ii8+PC9zdmc+" alt="MT5"/>
  <img src="https://img.shields.io/badge/Instrument-XAUUSD-gold?style=for-the-badge" alt="XAUUSD"/>
  <img src="https://img.shields.io/badge/Timeframe-H1-orange?style=for-the-badge" alt="H1"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/TimescaleDB-enabled-FDB515?style=flat-square&logo=timescale&logoColor=white" alt="TimescaleDB"/>
  <img src="https://img.shields.io/badge/pgvector-enabled-8B5CF6?style=flat-square" alt="pgvector"/>
  <img src="https://img.shields.io/badge/MCP-compatible-FF6B35?style=flat-square" alt="MCP"/>
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/scikit--learn-ML-F7931E?style=flat-square&logo=scikitlearn&logoColor=white" alt="sklearn"/>
  <img src="https://img.shields.io/badge/R-forecast-276DC3?style=flat-square&logo=r&logoColor=white" alt="R"/>
</p>

---

## Overview

GoldShield EA is a safety-first automated trading system for **XAUUSD (Gold)** on MetaTrader 5, paired with a full data pipeline that stores trades and market data in PostgreSQL — ready to connect to any AI via the **Model Context Protocol (MCP)**.

> **The EA trades. The database remembers. You bring your own AI.**

<p align="center">
  <img src="assets/architecture.png?raw=true" alt="System Architecture" width="100%"/>
</p>

---

## Features

<table>
<tr>
<td width="50%">

### Trading Engine
- EMA 50/200 crossover with RSI filter
- ATR-based dynamic SL/TP/trailing stop
- Daily loss limit, spread filter, cooldown
- Position sizing by risk percentage

</td>
<td width="50%">

### Data Pipeline
- PostgreSQL + TimescaleDB + pgvector
- Multi-timeframe candle storage (M1 to W1)
- Trade journal with full P&L tracking
- Vector embeddings for pattern matching

</td>
</tr>
<tr>
<td>

### Dashboard (Streamlit)
- Parameter adjustment UI
- Candlestick charts with Plotly
- Trade journal with cumulative P&L
- Snapshot & compare functionality

</td>
<td>

### AI & ML Integration
- MCP server with 6 tools for any AI
- Bring your own LLM (Claude, OpenAI, Gemini, Ollama, local)
- sklearn models (RF, GBM, SVM, KNN, Logistic)
- R integration (ARIMA, ETS, randomForest)

</td>
</tr>
</table>

---

## Architecture

<p align="center">
  <img src="assets/dataflow.png?raw=true" alt="Data Flow Pipeline" width="70%"/>
</p>

---

## Project Structure

```
GoldShield-EA/
├── GoldShield_EA.mq5               # MT5 Expert Advisor source
├── docker-compose.yml               # One-command database setup
├── .env.example                     # Configuration template
│
├── db/migrations/
│   ├── 001_extensions.sql           # TimescaleDB + pgvector
│   ├── 002_candles.sql              # OHLCV hypertable (unique constraint)
│   ├── 003_trades.sql               # Trade journal hypertable
│   └── 004_parameters.sql           # EA configs + vector embeddings
│
├── scripts/
│   ├── collect_data.py              # Multi-TF candle fetcher (8 timeframes)
│   └── backtest_logger.py           # MT5 report parser → DB
│
├── dashboard/
│   └── app.py                       # Streamlit UI (6 pages)
│
├── ml/
│   ├── train_model.py               # Python ML training (5 models)
│   └── train.R                      # R forecasting (ARIMA, ETS, RF)
│
├── mcp-server/
│   ├── server.py                    # MCP server (6 tools)
│   └── claude_mcp_config.example.json
│
├── snapshots/                       # Point-in-time state captures
└── assets/                          # Diagram PNGs
```

---

## Quick Start

### Prerequisites

| Tool | Required | Purpose |
|------|----------|---------|
| [Docker](https://docs.docker.com/get-docker/) | Yes | Database |
| [Python 3.10+](https://www.python.org/) | Yes | Scripts, dashboard, MCP |
| [MetaTrader 5](https://www.metatrader5.com/) | For live trading | EA execution |
| [R](https://www.r-project.org/) | Optional | R-based ML models |

### 1. Start the Database

```bash
git clone https://github.com/Supawitk/GoldShield-EA.git
cd GoldShield-EA

cp .env.example .env
# Edit .env with your settings

docker compose up -d
```

PostgreSQL is now running with TimescaleDB + pgvector, all tables created automatically.

### 2. Collect Market Data

```bash
pip install -r scripts/requirements.txt

# Add your Twelve Data API key to .env (free: https://twelvedata.com)
python scripts/collect_data.py                          # H1, 500 bars
python scripts/collect_data.py --timeframe 15min        # 15-min bars
python scripts/collect_data.py --all-timeframes         # all 8 timeframes
python scripts/collect_data.py --days 90 --tf 4h        # 4H, 90 days
```

**Supported timeframes:** `1min` `5min` `15min` `30min` `1h` `4h` `1day` `1week`

### 3. Launch the Dashboard

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

<table>
<tr>
<td><strong>EA Parameters</strong> — adjust all EA inputs, save to DB</td>
<td><strong>Market Data</strong> — candlestick charts, multi-timeframe</td>
</tr>
<tr>
<td><strong>Trade Journal</strong> — P&L tracking, cumulative equity curve</td>
<td><strong>ML Models</strong> — train sklearn/R models on your data</td>
</tr>
<tr>
<td><strong>AI Assistant</strong> — connect any LLM, analyse trades</td>
<td><strong>Snapshots</strong> — save & compare EA states</td>
</tr>
</table>

### 4. Train ML Models

#### Python (scikit-learn)

```bash
pip install -r ml/requirements.txt

python ml/train_model.py                              # Random Forest
python ml/train_model.py --model gradient_boosting    # Gradient Boosting
python ml/train_model.py --model svm                  # SVM
python ml/train_model.py --model knn                  # K-Nearest Neighbors
python ml/train_model.py --model logistic             # Logistic Regression
python ml/train_model.py --export-r                   # + export CSV for R
```

#### R (forecast / randomForest)

```bash
# Prerequisites: install.packages(c("forecast", "randomForest", "caret", "jsonlite"))

python ml/train_model.py --export-r                   # export data first
Rscript ml/train.R                                    # auto.arima
Rscript ml/train.R ets                                # exponential smoothing
Rscript ml/train.R randomForest                       # random forest
```

### 5. Connect AI via MCP

```bash
pip install -r mcp-server/requirements.txt
```

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "goldshield": {
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "/absolute/path/to/GoldShield-EA"
    }
  }
}
```

### 6. Connect Any LLM (via Dashboard)

The AI Assistant page supports **bring-your-own-key** for multiple providers:

| Provider | Setup | Local? |
|----------|-------|--------|
| **Anthropic (Claude)** | Paste your `sk-ant-...` key | No |
| **OpenAI** | Paste your `sk-...` key | No |
| **Google Gemini** | Paste your API key | No |
| **Ollama** | Just run Ollama locally | Yes |
| **OpenAI-Compatible** | Any local/custom endpoint | Yes |

No API keys are stored or committed. Everything stays on your machine.

---

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `get_recent_trades` | Fetch latest N trades from the journal |
| `get_trade_stats` | Win-rate, profit factor, P&L over N days |
| `get_candles` | Recent XAUUSD H1 OHLCV data |
| `compare_parameter_sets` | Rank EA configs by performance |
| `suggest_parameters` | Best-performing config as starting point |
| `run_sql` | Run any read-only SQL query |

---

## EA Input Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `EMA_Fast_Period` | 50 | Fast EMA period |
| `EMA_Slow_Period` | 200 | Slow EMA period |
| `RSI_Period` | 14 | RSI lookback |
| `RiskPercent` | 1.0% | Risk per trade |
| `SL_ATR_Multiplier` | 1.5 | Stop loss = ATR x this |
| `TP_ATR_Multiplier` | 1.0 | Take profit = ATR x this |
| `TrailingStop_ATR_Mult` | 1.0 | Trailing distance = ATR x this |
| `MaxSpreadPoints` | 50 | Max acceptable spread |
| `DailyLossLimitPercent` | 3.0% | Daily drawdown limit |
| `MinBarsBetweenTrades` | 5 | Cooldown between entries |

All parameters are adjustable via the **Dashboard UI** or directly in MT5.

---

## Market Data APIs

| Provider | Free Tier | Best For |
|----------|-----------|----------|
| [Twelve Data](https://twelvedata.com) | 800 req/day | Historical candles (built-in support) |
| [MetaAPI](https://metaapi.cloud) | Free tier | Real-time MT5 bridge |
| [OANDA](https://developer.oanda.com) | Free demo | Professional forex data |
| [Polygon.io](https://polygon.io) | Free tier | US-focused, some forex |

---

## Disclaimer

> This project is for **educational and research purposes only**. Trading forex/gold involves substantial risk of loss. Past performance does not guarantee future results. Always test on a **demo account** before using real money. The authors are not responsible for any financial losses.

---

<p align="center">
  <sub>Built with MQL5 + PostgreSQL + TimescaleDB + pgvector + MCP + Streamlit + scikit-learn + R</sub>
</p>
