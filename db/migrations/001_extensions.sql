-- Enable required PostgreSQL extensions
-- TimescaleDB: time-series hypertables with automatic partitioning
-- pgvector:    vector similarity search for market pattern matching

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
