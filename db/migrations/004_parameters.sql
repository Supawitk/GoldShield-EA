-- EA parameter sets and their performance metrics.
-- Each row = one configuration the EA was tested with.

CREATE TABLE IF NOT EXISTS parameter_sets (
    id                  SERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    label               TEXT,

    -- Indicator params
    ema_fast            INTEGER NOT NULL DEFAULT 50,
    ema_slow            INTEGER NOT NULL DEFAULT 200,
    rsi_period          INTEGER NOT NULL DEFAULT 14,
    rsi_overbought      DOUBLE PRECISION NOT NULL DEFAULT 70,
    rsi_oversold        DOUBLE PRECISION NOT NULL DEFAULT 30,
    atr_period          INTEGER NOT NULL DEFAULT 14,

    -- Risk params
    risk_percent        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    sl_atr_mult         DOUBLE PRECISION NOT NULL DEFAULT 1.5,
    tp_atr_mult         DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    trailing_atr_mult   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    trailing_step_pts   INTEGER NOT NULL DEFAULT 50,

    -- Safety params
    max_spread_pts      INTEGER NOT NULL DEFAULT 50,
    max_positions       INTEGER NOT NULL DEFAULT 1,
    daily_loss_pct      DOUBLE PRECISION NOT NULL DEFAULT 3.0,
    cooldown_bars       INTEGER NOT NULL DEFAULT 5,
    start_hour          INTEGER NOT NULL DEFAULT 2,
    end_hour            INTEGER NOT NULL DEFAULT 21,

    -- Performance (filled after backtest / live run)
    total_trades        INTEGER,
    win_rate            DOUBLE PRECISION,
    profit_factor       DOUBLE PRECISION,
    max_drawdown_pct    DOUBLE PRECISION,
    sharpe_ratio        DOUBLE PRECISION,
    net_pnl             DOUBLE PRECISION,
    test_start          DATE,
    test_end            DATE,
    source              TEXT DEFAULT 'manual'
);

-- Market-condition embeddings for similarity search
CREATE TABLE IF NOT EXISTS market_embeddings (
    id          BIGSERIAL,
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL DEFAULT 'XAUUSD',
    timeframe   TEXT NOT NULL DEFAULT 'H1',
    window_bars INTEGER NOT NULL DEFAULT 50,
    embedding   vector(128),
    label       TEXT
);

SELECT create_hypertable('market_embeddings', 'time', if_not_exists => TRUE);
