"""Bounded LangGraph workflow for sourced, on-demand GCC market research.

This module uses the direct Tavily API. It does not require MCP and never
changes city suitability scores.
"""
from __future__ import annotations

import os
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from gcc_intelligence.research.tavily_client import search_market_evidence
from gcc_intelligence.research.evidence import validate_evidence
from gcc_intelligence.research.persistence import save_research_run


class ResearchState(TypedDict, total=False):
    question: str
    city: str
    queries: list[str]
    raw_results: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    summary: str
    status: str
    errors: list[str]
    run_id: int | None


def plan_queries(state: ResearchState) -> ResearchState:
    """Create a small, bounded query set without an extra LLM call."""
    city = state["city"].strip()
    question = state["question"].strip()
    queries = [
        f'{city} India GCC expansion hiring office announcement 2025 2026',
        f'{city} India office leasing talent infrastructure GCC market {question}',
        f'{city} global capability centre investment jobs official company announcement',
    ]
    return {"queries": queries[:3], "errors": []}


def search_node(state: ResearchState) -> ResearchState:
    results: list[dict[str, Any]] = []
    errors = list(state.get("errors", []))
    for query in state.get("queries", [])[:3]:
        try:
            # Keep each request bounded to protect the provider's free quota.
            results.extend(search_market_evidence(query, max_results=4))
        except Exception as exc:
            errors.append(f"Search failed ({type(exc).__name__}).")
    # Deduplicate by canonical URL and keep a hard cap on stored evidence.
    unique: dict[str, dict[str, Any]] = {}
    for item in results:
        url = str(item.get("url", "")).strip()
        if url and url not in unique:
            unique[url] = item
    return {"raw_results": list(unique.values())[:12], "errors": errors}


def validation_node(state: ResearchState) -> ResearchState:
    evidence = validate_evidence(state.get("raw_results", []))
    status = "evidence_found" if evidence else "no_evidence"
    return {"evidence": evidence, "status": status}


def summary_node(state: ResearchState) -> ResearchState:
    evidence = state.get("evidence", [])
    if not evidence:
        return {
            "summary": (
                "No usable live evidence was returned. Check the Tavily key/quota or try a narrower query. "
                "No city scores were changed."
            )
        }
    # Use Groq only when configured; the no-key path remains useful and sourced.
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        bullets = [
            f'- **{item["title"]}** — {item["snippet"]} ([source]({item["url"]}))'
            for item in evidence[:8]
        ]
        return {"summary": "Groq is not configured, so here are the retrieved sources without an AI synthesis:\n\n" + "\n".join(bullets)}
    try:
        from langchain_groq import ChatGroq
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(model=model_name, api_key=api_key, temperature=0.1)
        prompt = f"""You are assisting with a GCC location-strategy prototype.
Answer the user's research question using ONLY the source records below.
Do not invent facts, dates, metrics, or citations. Distinguish announcements from
independent market measurements, identify conflicts/gaps, and state that search
results are not independently verified. Include source URLs inline for every
material factual claim. Do not calculate or change city suitability scores.
Question: {state.get('question')}
City: {state.get('city')}
Evidence JSON: {evidence}
Return a concise brief with Findings, Caveats, and What to verify next.
"""
        response = llm.invoke(prompt)
        return {"summary": str(response.content)}
    except Exception as exc:
        return {
            "summary": "Groq synthesis was unavailable; the sourced evidence is still shown below. "
            f"({type(exc).__name__})"
        }


def persist_node(state: ResearchState) -> ResearchState:
    try:
        run_id = save_research_run(
            city=state.get("city", ""), question=state.get("question", ""),
            evidence=state.get("evidence", []), summary=state.get("summary", ""),
            status=state.get("status", "unknown"),
        )
        return {"run_id": run_id}
    except Exception as exc:
        errors = list(state.get("errors", []))
        errors.append(f"Persistence unavailable ({type(exc).__name__}); results remain in this session.")
        return {"errors": errors, "run_id": None}


def build_research_graph():
    workflow = StateGraph(ResearchState)
    workflow.add_node("plan", plan_queries)
    workflow.add_node("search", search_node)
    workflow.add_node("validate", validation_node)
    workflow.add_node("summarize", summary_node)
    workflow.add_node("persist", persist_node)
    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "search")
    workflow.add_edge("search", "validate")
    workflow.add_edge("validate", "summarize")
    workflow.add_edge("summarize", "persist")
    workflow.add_edge("persist", END)
    return workflow.compile()


def run_market_research(city: str, question: str) -> dict[str, Any]:
    """Run one bounded research job and return its final state."""
    city = city.strip()
    question = question.strip()
    if not city or not question:
        raise ValueError("Both city and research question are required.")
    if not os.getenv("TAVILY_API_KEY", "").strip():
        raise RuntimeError("TAVILY_API_KEY is not configured. Add it to your local .env file.")
    graph = build_research_graph()
    return graph.invoke({
        "city": city[:100], "question": question[:500], "queries": [],
        "raw_results": [], "evidence": [], "summary": "", "status": "started",
        "errors": [], "run_id": None,
    })
