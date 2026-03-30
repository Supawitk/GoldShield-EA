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
</p>

---

## Overview

GoldShield EA is a safety-first automated trading system for **XAUUSD (Gold)** on MetaTrader 5, paired with a full data pipeline that stores trades and market data in PostgreSQL — ready to connect to any AI via the **Model Context Protocol (MCP)**.

> **The EA trades. The database remembers. The AI learns.**

```
┌─────────────┐     ┌──────────────────────────┐     ┌─────────────┐
│  MetaTrader  │────▶│  PostgreSQL               │────▶│  MCP Server │
│  5 Terminal  │     │  TimescaleDB + pgvector   │     │  (Python)   │
│              │     │                           │     │             │
│  GoldShield  │     │  candles ── trades        │     │  Tools:     │
│  EA.mq5      │     │  parameters ── embeddings │     │  query      │
└─────────────┘     └──────────────────────────┘     │  analyse    │
                                                      │  suggest    │
                             ┌─────────────────┐      └──────┬──────┘
                             │  Data Collector  │             │
                             │  (Twelve Data /  │             ▼
                             │   MetaAPI)       │      ┌─────────────┐
                             └─────────────────┘      │  Claude /   │
                                                      │  Any AI     │
                                                      └─────────────┘
```

---

## Trading Strategy

| Component | Details |
|-----------|---------|
| **Entry Signal** | EMA 50/200 crossover + price confirmation |
| **Filter** | RSI 14 must be between 30–70 (no extremes) |
| **Stop Loss** | 1.5x ATR below/above entry |
| **Take Profit** | 1.0x ATR target |
| **Trailing Stop** | 1.0x ATR, tightens only in profit |
| **Position Sizing** | ATR-based, risking 1% of balance per trade |

### Safety Guards

```
 Daily loss limit ─── 3% max drawdown per day, then stops
 Spread filter ────── Skips if spread > 50 points
 Cooldown ─────────── 5-bar minimum between trades
 Trading hours ────── 02:00 – 21:00 server time only
 Max positions ────── 1 open position at a time
```

---

## Project Structure

```
EA-v1.0/
├── GoldShield_EA.mq5              # MT5 Expert Advisor source
├── docker-compose.yml              # One-command database setup
├── .env.example                    # Configuration template
│
├── db/migrations/
│   ├── 001_extensions.sql          # TimescaleDB + pgvector
│   ├── 002_candles.sql             # OHLCV hypertable
│   ├── 003_trades.sql              # Trade journal hypertable
│   └── 004_parameters.sql          # EA param sets + embeddings
│
├── scripts/
│   ├── requirements.txt
│   ├── collect_data.py             # Fetch XAUUSD candles → DB
│   └── backtest_logger.py          # MT5 report → DB
│
└── mcp-server/
    ├── requirements.txt
    ├── server.py                   # MCP server (6 tools)
    └── claude_mcp_config.example.json
```

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Python 3.10+](https://www.python.org/)
- [MetaTrader 5](https://www.metatrader5.com/) (for running the EA)

### 1. Start the Database

```bash
cp .env.example .env
# Edit .env with your API key (optional for data collection)

docker compose up -d
```

That's it — PostgreSQL with TimescaleDB and pgvector is running, all tables created.

### 2. Collect Market Data

```bash
cd scripts
pip install -r requirements.txt

# Add your free Twelve Data API key to .env first
python collect_data.py              # latest 500 candles
python collect_data.py --days 90    # last 90 days
```

### 3. Load the EA in MetaTrader 5

1. Copy `GoldShield_EA.mq5` to your MT5 `Experts` folder
2. Compile it in MetaEditor
3. Attach to an **XAUUSD H1** chart (use a **demo account** first)
4. Enable **AutoTrading**

### 4. Log Backtest Results

After running a backtest in MT5's Strategy Tester, export the HTML report:

```bash
python scripts/backtest_logger.py path/to/report.html --label "v1-default"
```

### 5. Connect AI via MCP

```bash
cd mcp-server
pip install -r requirements.txt
```

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "goldshield": {
      "command": "python",
      "args": ["mcp-server/server.py"],
      "cwd": "/absolute/path/to/EA-v1.0"
    }
  }
}
```

Now Claude can query your trades, compare parameter sets, and suggest optimisations.

---

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `get_recent_trades` | Fetch latest N trades from the journal |
| `get_trade_stats` | Win-rate, profit factor, P&L over N days |
| `get_candles` | Recent XAUUSD H1 OHLCV data |
| `compare_parameter_sets` | Rank EA configs by performance |
| `suggest_parameters` | Best-performing config as a starting point |
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

---

## Data Flow

```
  Market Data API                MT5 Strategy Tester
  (Twelve Data)                  (HTML Reports)
       │                              │
       ▼                              ▼
  collect_data.py              backtest_logger.py
       │                              │
       ▼                              ▼
  ┌────────────────────────────────────────┐
  │          PostgreSQL 16                 │
  │  ┌──────────┐  ┌──────────────────┐   │
  │  │TimescaleDB│  │    pgvector      │   │
  │  │          │  │                  │   │
  │  │ candles  │  │ market_embeddings│   │
  │  │ trades   │  │ (128-dim vectors)│   │
  │  └──────────┘  └──────────────────┘   │
  │                                        │
  │  parameter_sets (configs + metrics)    │
  └────────────────────┬───────────────────┘
                       │
                       ▼
                  MCP Server
                       │
                       ▼
               Claude / Any AI
          "Analyse my last 50 trades"
          "Which params had best Sharpe?"
          "Suggest new SL multiplier"
```

---

## Market Data APIs

| Provider | Free Tier | Best For |
|----------|-----------|----------|
| [Twelve Data](https://twelvedata.com) | 800 req/day | Historical candles (used in `collect_data.py`) |
| [MetaAPI](https://metaapi.cloud) | Free tier | Real-time MT5 bridge |
| [OANDA](https://developer.oanda.com) | Free demo | Professional forex data |
| [Polygon.io](https://polygon.io) | Free tier | US-focused, some forex |

---

## Disclaimer

> This project is for **educational and research purposes only**. Trading forex/gold involves substantial risk of loss. Past performance does not guarantee future results. Always test on a **demo account** before using real money. The authors are not responsible for any financial losses.

---

<p align="center">
  <sub>Built with MQL5 + PostgreSQL + TimescaleDB + pgvector + MCP</sub>
</p>
