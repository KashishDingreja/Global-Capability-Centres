"""Optional PostgreSQL persistence; raw market observations are separate from scores."""
from __future__ import annotations
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DDL = """
CREATE TABLE IF NOT EXISTS city_metrics (
 id BIGSERIAL PRIMARY KEY, city TEXT NOT NULL, metric_key TEXT NOT NULL,
 metric_label TEXT NOT NULL, value DOUBLE PRECISION, unit TEXT, source_name TEXT,
 source_url TEXT, observed_at TEXT, evidence_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
 caveat TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(city, metric_key, source_name, observed_at)
);
CREATE TABLE IF NOT EXISTS market_observations (
 id BIGSERIAL PRIMARY KEY, city TEXT NOT NULL, metric_key TEXT NOT NULL,
 metric_label TEXT NOT NULL, value DOUBLE PRECISION, unit TEXT, period TEXT NOT NULL,
 source_name TEXT, source_url TEXT, source_published_at TEXT,
 evidence_status TEXT NOT NULL DEFAULT 'UNVERIFIED', caveat TEXT,
 imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(city, metric_key, period, source_name)
);
"""
def _engine():
 url=os.getenv("DATABASE_URL","").strip()
 if not url: return None
 if url.startswith("postgres://"): url=url.replace("postgres://","postgresql+psycopg://",1)
 elif url.startswith("postgresql://"): url=url.replace("postgresql://","postgresql+psycopg://",1)
 return create_engine(url,pool_pre_ping=True,future=True)
def database_status() -> tuple[bool,str]:
 try:
  engine=_engine()
  if engine is None: return False,"DATABASE_URL is not configured."
  try:
   with engine.connect() as connection: connection.execute(text("SELECT 1"))
   return True,"Connected to PostgreSQL."
  finally: engine.dispose()
 except Exception as exc:
  return False,f"PostgreSQL connection failed ({type(exc).__name__}). Check DATABASE_URL and network access."
def initialize_database() -> tuple[bool,str]:
 try:
  engine=_engine()
  if engine is None: return False,"Set DATABASE_URL in .env before initializing PostgreSQL."
  try:
   with engine.begin() as connection: connection.execute(text(DDL))
   return True,"city_metrics and market_observations tables are ready."
  finally: engine.dispose()
 except Exception as exc:
  return False,f"Could not initialize database ({type(exc).__name__}). Check connection settings and database permissions."
def load_metrics() -> pd.DataFrame | None:
 engine=_engine()
 if engine is None: return None
 try:
  with engine.connect() as connection:
   return pd.read_sql(text("SELECT city, metric_key, metric_label, value, unit, source_name, source_url, observed_at, evidence_status, caveat FROM city_metrics ORDER BY city, metric_key"),connection)
 except SQLAlchemyError: raise
 finally: engine.dispose()
def load_market_observations() -> pd.DataFrame | None:
 """Load raw office/GCC observations without treating them as normalized scores."""
 engine=_engine()
 if engine is None: return None
 try:
  with engine.connect() as connection:
   return pd.read_sql(text("SELECT city, metric_key, metric_label, value, unit, period, source_name, source_url, source_published_at, evidence_status, caveat FROM market_observations ORDER BY metric_key, period, city"),connection)
 except SQLAlchemyError: raise
 finally: engine.dispose()
