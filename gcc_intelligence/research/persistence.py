"""Optional PostgreSQL storage for research runs and source-level evidence."""
from __future__ import annotations
import json
import os
from typing import Any
from sqlalchemy import create_engine, text

DDL_RESEARCH_RUNS = """
CREATE TABLE IF NOT EXISTS market_research_runs (
 id BIGSERIAL PRIMARY KEY, city TEXT NOT NULL, question TEXT NOT NULL,
 status TEXT NOT NULL, summary TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
DDL_RESEARCH_EVIDENCE = """
CREATE TABLE IF NOT EXISTS market_research_evidence (
 id BIGSERIAL PRIMARY KEY, run_id BIGINT NOT NULL REFERENCES market_research_runs(id) ON DELETE CASCADE,
 city TEXT NOT NULL, title TEXT NOT NULL, source_url TEXT NOT NULL,
 source_domain TEXT, snippet TEXT, published_date TEXT, search_score DOUBLE PRECISION,
 evidence_status TEXT NOT NULL DEFAULT 'UNVERIFIED', validation_note TEXT,
 retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE(run_id, source_url)
);
"""


def _engine():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True, future=True)


def save_research_run(city: str, question: str, evidence: list[dict[str, Any]], summary: str, status: str) -> int | None:
    engine = _engine()
    if engine is None:
        return None
    try:
        with engine.begin() as connection:
            connection.execute(text(DDL_RESEARCH_RUNS))
            connection.execute(text(DDL_RESEARCH_EVIDENCE))
            run_id = connection.execute(text(
                "INSERT INTO market_research_runs(city, question, status, summary) "
                "VALUES (:city, :question, :status, :summary) RETURNING id"
            ), {"city": city, "question": question, "status": status, "summary": summary}).scalar_one()
            for item in evidence:
                connection.execute(text("""
                    INSERT INTO market_research_evidence
                    (run_id, city, title, source_url, source_domain, snippet, published_date,
                     search_score, evidence_status, validation_note, retrieved_at)
                    VALUES (:run_id, :city, :title, :source_url, :source_domain, :snippet,
                            :published_date, :search_score, :evidence_status, :validation_note,
                            CAST(:retrieved_at AS timestamptz))
                    ON CONFLICT (run_id, source_url) DO NOTHING
                """), {
                    "run_id": run_id, "city": city, "title": item["title"],
                    "source_url": item["url"], "source_domain": item["source_domain"],
                    "snippet": item["snippet"], "published_date": item.get("published_date"),
                    "search_score": item.get("search_score"), "evidence_status": item["evidence_status"],
                    "validation_note": item["validation_note"], "retrieved_at": item["retrieved_at"],
                })
            return int(run_id)
    finally:
        engine.dispose()
