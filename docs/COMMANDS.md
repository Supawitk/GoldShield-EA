# Command Reference

Full list of all CLI scripts, options, and MCP tools available in GoldShield EA.

---

## Scripts

### Data Collection

```bash
python scripts/collect_data.py                          # H1, latest 500 bars
python scripts/collect_data.py --days 30                # H1, last 30 days
python scripts/collect_data.py --timeframe 15min        # 15-minute bars
python scripts/collect_data.py --timeframe 4h --days 90 # 4H, last 90 days
python scripts/collect_data.py --all-timeframes         # all 8 timeframes at once
```

| Flag | Default | Description |
|------|---------|-------------|
| `--days` | 0 | Days of history to fetch (0 = latest 500 bars) |
| `--timeframe`, `-tf` | `1h` | Timeframe: `1min` `5min` `15min` `30min` `1h` `4h` `1day` `1week` |
| `--all-timeframes` | off | Fetch all 8 timeframes in one run |

Requires `TWELVE_DATA_API_KEY` in `.env` ([free tier: 800 req/day](https://twelvedata.com)).

---

### Trade Logging API

```bash
python scripts/trade_api.py                             # default: 0.0.0.0:5555
python scripts/trade_api.py --port 8080                 # custom port
python scripts/trade_api.py --host 127.0.0.1            # localhost only
```

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/trade/open` | POST | `{"direction":"BUY","lot_size":0.1,"entry_price":2350.50,"stop_loss":2340,"take_profit":2360}` | Log trade entry |
| `/trade/close` | POST | `{"trade_id":1,"exit_price":2355.00,"exit_reason":"TP hit"}` | Log trade exit + P&L |
| `/health` | GET | — | Health check |

**MT5 setup**: Tools > Options > Expert Advisors > add `http://localhost:5555` to allowed URLs.

---

### CSV Export

```bash
python scripts/export_csv.py                            # export all tables
python scripts/export_csv.py --table trades             # trades only
python scripts/export_csv.py --table candles            # candles only
python scripts/export_csv.py --table parameter_sets     # parameter sets only
python scripts/export_csv.py --table trades --limit 100 # limit rows
```

| Flag | Default | Description |
|------|---------|-------------|
| `--table`, `-t` | all | `trades`, `candles`, or `parameter_sets` |
| `--limit`, `-l` | 5000 | Max rows to export |

Output goes to `exports/` directory.

---

### Backtest Logger

```bash
python scripts/backtest_logger.py report.html                # default label
python scripts/backtest_logger.py report.html --label "v2"   # custom label
```

Parses MT5 Strategy Tester HTML reports and saves metrics (total trades, win rate, profit factor, drawdown, Sharpe, P&L) to `parameter_sets` table.

---

### Embedding Generator

```bash
python scripts/generate_embeddings.py                   # 50-bar windows, step 10, H1
python scripts/generate_embeddings.py --window 100      # 100-bar windows
python scripts/generate_embeddings.py --step 5          # every 5 bars (denser)
python scripts/generate_embeddings.py --timeframe H4    # use 4H candles
python scripts/generate_embeddings.py --limit 10000     # load more candles
```

| Flag | Default | Description |
|------|---------|-------------|
| `--window`, `-w` | 50 | Bars per embedding window |
| `--step`, `-s` | 10 | Step between windows |
| `--timeframe`, `-tf` | `H1` | Timeframe to embed |
| `--limit` | 5000 | Max candles to load |

Each embedding is a 128-dim normalized vector capturing: returns, body ratios, wicks, momentum, volatility, RSI approximation, volume trend. Stored in `market_embeddings` (pgvector).

---

## ML Models

### Python (scikit-learn)

```bash
python ml/train_model.py                                # Random Forest (default)
python ml/train_model.py --model gradient_boosting      # Gradient Boosting
python ml/train_model.py --model svm                    # SVM
python ml/train_model.py --model knn                    # K-Nearest Neighbors
python ml/train_model.py --model logistic               # Logistic Regression
python ml/train_model.py --lookback 300                 # use 300 bars
python ml/train_model.py --split 75                     # 75/25 train/test
python ml/train_model.py --export-r                     # also export CSV for R
```

| Flag | Default | Description |
|------|---------|-------------|
| `--model`, `-m` | `random_forest` | `random_forest`, `gradient_boosting`, `svm`, `knn`, `logistic` |
| `--lookback` | 200 | Number of bars to use |
| `--split` | 80 | Train/test split percentage |
| `--export-r` | off | Export `ml/candles_export.csv` for R scripts |

Features: EMA ratio, RSI, ATR, body size, wicks, hour, day of week, momentum (5 & 10 bar), volume.

### R (forecast / randomForest)

```bash
# First export data
python ml/train_model.py --export-r

# Then run R models
Rscript ml/train.R                                     # auto.arima (default)
Rscript ml/train.R ets                                 # Exponential Smoothing
Rscript ml/train.R randomForest                        # Random Forest classifier
```

Requires: `install.packages(c("forecast", "randomForest", "caret", "jsonlite"))`

---

## Dashboard

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

| Page | Description |
|------|-------------|
| **EA Parameters** | Adjust all EA inputs (indicators, risk, safety filters), save as parameter set |
| **Market Data** | Candlestick chart with timeframe picker (M1–W1) |
| **Trade Journal** | Trade table + cumulative P&L equity curve |
| **ML Models** | Train sklearn models in-browser, view feature importance |
| **AI Assistant** | Connect any LLM (Claude, OpenAI, Gemini, Ollama, local), query DB context |
| **Snapshots** | Save, compare, and restore point-in-time EA states |

---

## MCP Server

```bash
pip install -r mcp-server/requirements.txt
python mcp-server/server.py                             # stdio transport
```

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_recent_trades` | `limit` (default: 20) | Latest trades from journal |
| `get_trade_stats` | `days` (default: 30) | Win-rate, profit factor, net P&L |
| `get_candles` | `hours` (default: 100) | Recent XAUUSD H1 candles |
| `compare_parameter_sets` | `limit` (default: 10) | Rank EA configs by profit factor |
| `suggest_parameters` | — | Best-performing config (requires 10+ trades) |
| `find_similar_conditions` | `hours_ago`, `top_k` | pgvector cosine similarity search |
| `export_csv` | `table`, `limit` | Export to CSV file |
| `run_sql` | `query` | Read-only SELECT queries |

---

## EA Input Parameters

Set in MT5 when attaching the EA to a chart, or via the Dashboard.

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `MagicNumber` | 20260330 | — | Unique EA identifier |
| `TradeComment` | GoldShield | — | Order comment label |
| `TradeAPI_URL` | http://localhost:5555 | — | Trade logging endpoint (blank to disable) |
| `EMA_Fast_Period` | 50 | 5–200 | Fast EMA period |
| `EMA_Slow_Period` | 200 | 50–500 | Slow EMA period |
| `RSI_Period` | 14 | 2–50 | RSI lookback |
| `RSI_Overbought` | 70.0 | 50–95 | RSI overbought threshold |
| `RSI_Oversold` | 30.0 | 5–50 | RSI oversold threshold |
| `ATR_Period` | 14 | 2–50 | ATR lookback |
| `RiskPercent` | 1.0 | 0.1–5.0 | Risk per trade (% of balance) |
| `SL_ATR_Multiplier` | 1.5 | 0.5–5.0 | Stop loss = ATR x this |
| `TP_ATR_Multiplier` | 1.0 | 0.5–5.0 | Take profit = ATR x this |
| `TrailingStop_ATR_Mult` | 1.0 | 0.5–5.0 | Trailing stop distance |
| `TrailingStep_Points` | 50 | 10–500 | Min trailing step (points) |
| `MaxSpreadPoints` | 50 | 10–200 | Max acceptable spread |
| `MaxOpenPositions` | 1 | 1–10 | Concurrent positions |
| `DailyLossLimitPercent` | 3.0 | 1.0–10.0 | Daily drawdown limit (%) |
| `MinBarsBetweenTrades` | 5 | 1–50 | Cooldown bars between entries |
| `TradingStartHour` | 2 | 0–23 | Start trading (server time) |
| `TradingEndHour` | 21 | 0–23 | Stop trading (server time) |

---

## Database Tables

| Table | Type | Description |
|-------|------|-------------|
| `candles` | TimescaleDB hypertable | OHLCV data, unique on (time, symbol, timeframe) |
| `trades` | TimescaleDB hypertable | Trade journal with entry/exit/P&L |
| `parameter_sets` | Regular table | EA configurations + performance metrics |
| `market_embeddings` | TimescaleDB hypertable | 128-dim pgvector embeddings for similarity search |
