"""Deterministic validation for web-search evidence; not a truth classifier."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


def validate_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for item in items:
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not title or not snippet:
            continue
        canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/").lower()
        if canonical in seen:
            continue
        seen.add(canonical)
        validated.append({
            "title": title[:500], "url": url[:2000], "snippet": snippet[:3000],
            "published_date": str(item.get("published_date") or "")[:100] or None,
            "source_domain": parsed.netloc.lower(),
            "search_score": item.get("score"),
            "evidence_status": "UNVERIFIED",
            "validation_note": "URL and required fields passed structural checks; factual accuracy has not been verified.",
            "retrieved_at": retrieved_at,
        })
    return validated[:12]
