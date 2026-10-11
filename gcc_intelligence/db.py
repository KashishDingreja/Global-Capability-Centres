"""Optional local PostgreSQL persistence; demo mode works without a database."""
from __future__ import annotations
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DDL = """
CREATE TABLE IF NOT EXISTS city_metrics (
    id BIGSERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    metric_key TEXT NOT NULL,
    metric_label TEXT NOT NULL,
    value DOUBLE PRECISION,
    unit TEXT,
    source_name TEXT,
    source_url TEXT,
    observed_at TEXT,
    evidence_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    caveat TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(city, metric_key, source_name, observed_at)
);
"""

def _engine():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    # SQLAlchemy's psycopg v3 driver is used for PostgreSQL.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True, future=True)

def database_status() -> tuple[bool, str]:
    try:
        engine = _engine()
        if engine is None:
            return False, "DATABASE_URL is not configured."
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "Connected to PostgreSQL."
    except Exception as exc:
        return False, f"PostgreSQL connection failed: {type(exc).__name__}: {exc}"

def initialize_database() -> tuple[bool, str]:
    try:
        engine = _engine()
        if engine is None:
            return False, "Set DATABASE_URL in .env before initializing PostgreSQL."
        with engine.begin() as connection:
            connection.execute(text(DDL))
        return True, "city_metrics table is ready."
    except Exception as exc:
        return False, f"Could not initialize database: {type(exc).__name__}: {exc}"

def load_metrics() -> pd.DataFrame | None:
    engine = _engine()
    if engine is None:
        return None
    with engine.connect() as connection:
        try:
            return pd.read_sql(text("SELECT city, metric_key, metric_label, value, unit, source_name, source_url, observed_at, evidence_status, caveat FROM city_metrics ORDER BY city, metric_key"), connection)
        except SQLAlchemyError:
            return None
