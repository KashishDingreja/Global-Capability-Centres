"""Optional Groq explanation layer. Ranking is always calculated in Python."""
from __future__ import annotations
import os
import pandas as pd

def generate_decision_brief(ranked: pd.DataFrame, source_metrics: pd.DataFrame, weights: dict[str, float]) -> tuple[str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "Groq is not configured. Add GROQ_API_KEY to your local `.env` file to enable AI-generated explanations. "
            "The deterministic city comparison above remains available without an API key.",
            "No external LLM request was made.",
        )
    try:
        from langchain_groq import ChatGroq
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        llm = ChatGroq(model=model_name, api_key=api_key, temperature=0.2)
        columns = [c for c in ["city", "overall_score", "evidence_coverage", *weights.keys()] if c in ranked.columns]
        compact = ranked[columns].round(2).to_dict(orient="records")
        evidence_status = sorted(set(source_metrics.get("evidence_status", pd.Series(dtype=str)).astype(str)))
        prompt = f"""
Write a concise executive decision brief for a Global Capability Centre (GCC) city screening.
Use only the data provided below. The values are prototype data and may be illustrative.
Do not add external market facts, invent citations, or present the ranking as a probability.
Explain the top result, trade-offs, evidence coverage, and what should be verified next.
If evidence is illustrative or unverified, state that prominently.
Weights: {weights}
City scores: {compact}
Evidence statuses present: {evidence_status}
Return short headings and practical bullets.
"""
        response = llm.invoke(prompt)
        return str(response.content), f"Generated with Groq model `{model_name}`. Validate all claims against source records before reuse."
    except Exception as exc:
        return (
            "The Groq request could not be completed. The scoring results are still available; check your model name, API key, and network connection.",
            f"Groq error: {type(exc).__name__}: {exc}",
        )
