<p align="center">
  <img src="https://img.icons8.com/3d-fluency/94/shield.png" width="80" alt="shield"/>
</p>

<h1 align="center">GoldShield EA</h1>

<p align="center">
  <strong>Safety-First XAUUSD Expert Advisor with AI-Ready Data Pipeline</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-MetaTrader_5-blue?style=for-the-badge" alt="MT5"/>
  <img src="https://img.shields.io/badge/Instrument-XAUUSD-gold?style=for-the-badge" alt="XAUUSD"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/TimescaleDB-FDB515?style=flat-square&logo=timescale&logoColor=white"/>
  <img src="https://img.shields.io/badge/pgvector-8B5CF6?style=flat-square"/>
  <img src="https://img.shields.io/badge/MCP-FF6B35?style=flat-square"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white"/>
  <img src="https://img.shields.io/badge/R-276DC3?style=flat-square&logo=r&logoColor=white"/>
</p>

---

> **The EA trades. The database remembers. You bring your own AI.**

<p align="center">
  <img src="assets/architecture.png?raw=true" alt="System Architecture" width="100%"/>
</p>

---

## Features

<table>
<tr>
<td width="50%">

**Trading Engine** — EMA crossover + RSI filter, ATR-based SL/TP/trailing, daily loss limit, spread guard, cooldown, risk-based sizing

**Data Pipeline** — PostgreSQL + TimescaleDB + pgvector, 8 timeframes (M1–W1), trade journal, vector embeddings

</td>
<td width="50%">

**Dashboard** — Streamlit UI with parameter editor, candlestick charts, P&L curves, ML training, snapshots

**AI & ML** — MCP server (8 tools), bring-your-own LLM, sklearn (5 models), R (ARIMA/ETS/RF), CSV export, vector similarity search

</td>
</tr>
</table>

<p align="center">
  <img src="assets/dataflow.png?raw=true" alt="Data Flow" width="60%"/>
</p>

---

## Quick Start

```bash
git clone https://github.com/Supawitk/GoldShield-EA.git && cd GoldShield-EA
cp .env.example .env              # add your Twelve Data API key (free)
docker compose up -d              # PostgreSQL + TimescaleDB + pgvector
```

```bash
pip install -r scripts/requirements.txt
python scripts/collect_data.py                    # fetch H1 candles
python scripts/collect_data.py --all-timeframes   # fetch all 8 timeframes
```

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py                    # launch UI
```

---

## MCP Server + AI

```bash
pip install -r mcp-server/requirements.txt
```

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

| Tool | Description |
|------|-------------|
| `get_recent_trades` | Latest trades from journal |
| `get_trade_stats` | Win-rate, profit factor, P&L |
| `get_candles` | XAUUSD OHLCV data |
| `compare_parameter_sets` | Rank configs by performance |
| `suggest_parameters` | Best-performing config |
| `find_similar_conditions` | pgvector similarity search |
| `export_csv` | Export trades/candles/params to CSV |
| `run_sql` | Read-only SQL queries |

**Bring your own LLM** via the Dashboard AI page — supports Claude, OpenAI, Gemini, Ollama, or any OpenAI-compatible endpoint. No keys stored.

---

## ML Models

```bash
pip install -r ml/requirements.txt
python ml/train_model.py                           # Random Forest
python ml/train_model.py -m gradient_boosting      # Gradient Boosting
python ml/train_model.py -m svm                    # SVM
python ml/train_model.py -m knn                    # KNN
python ml/train_model.py -m logistic               # Logistic Regression
python ml/train_model.py --export-r                # export CSV for R
Rscript ml/train.R                                 # R: auto.arima
Rscript ml/train.R randomForest                    # R: random forest
```

---

## Export Data

```bash
python scripts/export_csv.py                       # export all tables
python scripts/export_csv.py --table trades        # trades only
python scripts/export_csv.py --table candles -l 1000
```

Or use the `export_csv` MCP tool to let AI export for you.

---

## Trade Logging API

The EA logs trades to PostgreSQL in real-time via HTTP. Start the API, then the EA sends trade open/close events automatically.

```bash
python scripts/trade_api.py                        # default port 5555
python scripts/trade_api.py --port 8080            # custom port
```

In MT5: go to **Tools > Options > Expert Advisors** and add `http://localhost:5555` to the allowed URLs list.

---

## Vector Embeddings

Generate market-condition embeddings from candle data for pgvector similarity search:

```bash
python scripts/generate_embeddings.py              # 50-bar windows, H1
python scripts/generate_embeddings.py --window 100 # 100-bar windows
python scripts/generate_embeddings.py --step 5     # denser coverage
```

Then use the `find_similar_conditions` MCP tool to find historically similar market states.

---

## Project Structure

```
GoldShield-EA/
├── GoldShield_EA.mq5            # MT5 EA (with WebRequest trade logging)
├── docker-compose.yml            # One-command DB setup
├── db/
│   ├── connection.py             # Shared DB utilities (used by all scripts)
│   └── migrations/               # SQL schema (4 files)
├── scripts/
│   ├── collect_data.py           # Multi-TF candle fetcher
│   ├── export_csv.py             # CSV export
│   ├── generate_embeddings.py    # pgvector embedding generator
│   ├── trade_api.py              # HTTP trade logging server
│   └── backtest_logger.py        # MT5 report parser
├── dashboard/app.py              # Streamlit UI (6 pages)
├── ml/                           # sklearn + R models
├── mcp-server/server.py          # MCP server (8 tools)
├── snapshots/                    # Point-in-time state captures
└── exports/                      # CSV output
```

---

## Changelog

### v1.1.0
- **Refactor**: Shared `db/connection.py` module — all scripts use one DB utility with context managers (was duplicated 6 times)
- **New**: Trade logging HTTP API (`scripts/trade_api.py`) — receives trade events from EA
- **New**: MQL5 WebRequest integration — EA auto-logs trades to PostgreSQL on open/close
- **New**: Embedding generator (`scripts/generate_embeddings.py`) — populates `market_embeddings` table for pgvector similarity search
- **New**: Snapshot restore — dashboard can now load saved snapshots back as active parameter sets
- **Fix**: All DB connections use context managers (no more connection leaks)

### v1.1
- Dashboard UI with 6 pages (params, charts, trades, ML, AI, snapshots)
- Multi-timeframe data collection (M1 to W1)
- ML models: sklearn (5 models) + R (ARIMA, ETS, RF)
- AI Assistant with bring-your-own-key LLM support
- MCP server with vector similarity search + CSV export

### v1.0
- Initial release: GoldShield EA for XAUUSD H1
- PostgreSQL + TimescaleDB + pgvector via Docker Compose
- Data collection from Twelve Data API

---

## Disclaimer

> For **educational and research purposes only**. Trading involves substantial risk. Always use a **demo account** first.

---

<p align="center">
  <sub>Built with MQL5 + PostgreSQL + TimescaleDB + pgvector + MCP + Streamlit + scikit-learn + R</sub>
</p>
