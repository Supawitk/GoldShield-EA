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

**Data Pipeline** — PostgreSQL + TimescaleDB + pgvector, 8 timeframes (M1--W1), trade journal, vector embeddings

</td>
<td width="50%">

**Dashboard** — Streamlit UI with parameter editor, candlestick charts, P&L curves, ML training, snapshots with restore

**AI & ML** — MCP server (8 tools), bring-your-own LLM, sklearn (5 models), R (ARIMA/ETS/RF), CSV export, pgvector similarity search

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
python scripts/collect_data.py --all-timeframes   # all 8 timeframes
```

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py                    # launch UI
```

```bash
python scripts/trade_api.py                       # start trade logging API
python scripts/generate_embeddings.py             # generate pgvector embeddings
```

> **Full command reference with all flags and options:** **[docs/COMMANDS.md](docs/COMMANDS.md)**

---

## MCP Server

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

8 tools available: `get_recent_trades` `get_trade_stats` `get_candles` `compare_parameter_sets` `suggest_parameters` `find_similar_conditions` `export_csv` `run_sql`

**Bring your own LLM** via the Dashboard AI page — supports Claude, OpenAI, Gemini, Ollama, or any OpenAI-compatible endpoint. No keys stored.

> See [docs/COMMANDS.md](docs/COMMANDS.md) for full tool parameters and API endpoint docs.

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
│   ├── trade_api.py              # HTTP trade logging server
│   ├── generate_embeddings.py    # pgvector embedding generator
│   ├── export_csv.py             # CSV export
│   └── backtest_logger.py        # MT5 report parser
├── dashboard/app.py              # Streamlit UI (6 pages)
├── ml/                           # sklearn + R models
├── mcp-server/server.py          # MCP server (8 tools)
├── docs/COMMANDS.md              # Full CLI & API reference
├── snapshots/                    # Point-in-time state captures
└── exports/                      # CSV output
```

---

## Changelog

### v1.1.0
- Shared `db/connection.py` — single DB utility with context managers (was duplicated 6x)
- Trade logging HTTP API + MQL5 WebRequest integration (EA auto-logs to PostgreSQL)
- Embedding generator for pgvector similarity search
- Snapshot restore in dashboard
- Full command reference moved to [docs/COMMANDS.md](docs/COMMANDS.md)

### v1.1
- Dashboard UI (6 pages), multi-timeframe collection, ML models (sklearn + R)
- AI Assistant with bring-your-own-key LLM, MCP server with CSV export + vector search

### v1.0
- Initial release: GoldShield EA for XAUUSD H1
- PostgreSQL + TimescaleDB + pgvector via Docker Compose

---

## Disclaimer

> For **educational and research purposes only**. Trading involves substantial risk. Always use a **demo account** first.

---

<p align="center">
  <sub>Built with MQL5 + PostgreSQL + TimescaleDB + pgvector + MCP + Streamlit + scikit-learn + R</sub>
</p>
