-- XAUUSD OHLCV candle data — stored as a TimescaleDB hypertable
-- for fast time-range queries and automatic chunk management.

CREATE TABLE IF NOT EXISTS candles (
    time        TIMESTAMPTZ NOT NULL,
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      DOUBLE PRECISION DEFAULT 0,
    symbol      TEXT NOT NULL DEFAULT 'XAUUSD',
    timeframe   TEXT NOT NULL DEFAULT 'H1'
);

SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_candles_symbol_tf
    ON candles (symbol, timeframe, time DESC);
