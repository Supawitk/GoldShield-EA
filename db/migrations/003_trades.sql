-- Trade journal — every entry/exit the EA makes.
-- Stored as a hypertable so aggregate queries (win-rate by week, etc.) are fast.

CREATE TABLE IF NOT EXISTS trades (
    id              BIGSERIAL,
    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          TEXT NOT NULL DEFAULT 'XAUUSD',
    direction       TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    lot_size        DOUBLE PRECISION NOT NULL,
    entry_price     DOUBLE PRECISION NOT NULL,
    stop_loss       DOUBLE PRECISION,
    take_profit     DOUBLE PRECISION,
    exit_price      DOUBLE PRECISION,
    exit_time       TIMESTAMPTZ,
    pnl             DOUBLE PRECISION,
    pnl_pips        DOUBLE PRECISION,
    commission      DOUBLE PRECISION DEFAULT 0,
    swap            DOUBLE PRECISION DEFAULT 0,
    duration_mins   INTEGER,
    exit_reason     TEXT,
    param_set_id    INTEGER,
    notes           TEXT
);

SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);
