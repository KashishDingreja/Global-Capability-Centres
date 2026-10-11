"""Small direct-API wrapper for Tavily Search (no MCP server required)."""
from __future__ import annotations
import os
from typing import Any
from tavily import TavilyClient


def search_market_evidence(query: str, max_results: int = 4) -> list[dict[str, Any]]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY is not configured.")
    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=query,
        search_depth="basic",
        max_results=max(1, min(int(max_results), 4)),
        include_answer=False,
        include_raw_content=False,
    )
    normalized: list[dict[str, Any]] = []
    for item in response.get("results", []):
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        if not url or not title:
            continue
        normalized.append({
            "title": title[:500], "url": url[:2000],
            "snippet": str(item.get("content", "")).strip()[:3000],
            "published_date": item.get("published_date"),
            "score": item.get("score"),
            "source_domain": item.get("url", "").split("/")[2] if "://" in item.get("url", "") else "",
        })
    return normalized
