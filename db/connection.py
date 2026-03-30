"""
Shared database utilities for the GoldShield project.
All scripts and services import from here — single source of truth.
"""

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load .env from project root (works regardless of caller's cwd)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "goldshield"),
    "user": os.getenv("DB_USER", "goldshield"),
    "password": os.getenv("DB_PASSWORD", "goldshield_dev"),
}


def get_dsn() -> str:
    return " ".join(f"{k}={v}" for k, v in DB_CONFIG.items())


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def db_cursor(dict_cursor: bool = False):
    """Context manager that yields a cursor and auto-commits/closes."""
    conn = get_connection()
    factory = psycopg2.extras.RealDictCursor if dict_cursor else None
    cur = conn.cursor(cursor_factory=factory)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def query_rows(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return list of dicts."""
    with db_cursor(dict_cursor=True) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def execute(sql: str, params: tuple = ()):
    """Run an INSERT/UPDATE/DELETE and return fetchone result or None."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        try:
            return cur.fetchone()
        except psycopg2.ProgrammingError:
            return None
