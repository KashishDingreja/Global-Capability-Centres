# GCC Intelligence

An evidence-led prototype for comparing Indian cities for Global Capability Centre (GCC) setup or expansion.

## Current MVP
- Streamlit city comparison dashboard
- Configurable decision weights
- Deterministic Python scoring and evidence coverage
- Evidence explorer with source and caveat fields
- Optional Groq-generated explanation (LLM does not calculate rankings)
- On-demand live market research via Tavily Search + LangGraph workflow, with Groq-based pre-search query guardrail and evidence-grounded synthesis
- Source-level evidence validation, CSV export, and optional PostgreSQL research history
- Optional local PostgreSQL persistence

> **Data integrity notice:** Bundled city values are synthetic fixtures for demonstrating the workflow. They are not verified market facts and must not be used for investment decisions. Replace them with observations from credible sources and retain source URLs, observation dates, definitions, and caveats.

## Live research guardrail\n\nBefore any Tavily request, Groq classifies the user query as `ALLOW`, `WARN`, or `BLOCK`. `ALLOW` proceeds to bounded search; `WARN` and `BLOCK` stop before retrieval and show a compliance-oriented message. If Groq is missing, errors, or returns invalid output, the workflow fails closed and makes no search request. Retrieved page text is treated as untrusted input in the synthesis prompt. This is an LLM screening layer, not a legal opinion or a guarantee against every unsafe or misclassified query. Keep the classifier prompt and decision rules under review and test representative benign, ambiguous, and clearly unlawful queries.\n\n## Run locally (Windows PowerShell)

1. Install Python 3.11 or newer.
2. Create and activate an environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`. Add `TAVILY_API_KEY` for web search and `GROQ_API_KEY` for the LLM query guardrail and AI-generated summaries. Live research fails closed (does not search) if the LLM guardrail is unavailable. Keep keys out of Git.
4. Run the demo without PostgreSQL first:
   ```powershell
   streamlit run app.py
   ```
   It uses clearly labelled illustrative data when `DATABASE_URL` is blank or PostgreSQL is unavailable.

## Local PostgreSQL with pgAdmin

1. In pgAdmin, create a database named `gcc_intelligence`.
2. Put your local connection string in `.env`, for example:
   `DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/gcc_intelligence`
3. Restart Streamlit and use **Initialize database tables** in the sidebar.
4. Add verified records to `city_metrics`. Expected metric keys are `talent_depth`, `operating_cost`, `ecosystem`, and `infrastructure`. These are desirability scores on a 0–100 scale, not raw rupee costs. Set `evidence_status` to a value such as `VERIFIED`, `PARTIAL`, or `ILLUSTRATIVE`.

The application does not automatically seed demo metrics into PostgreSQL. This avoids accidentally persisting synthetic values as real evidence.

## Scoring approach

For each city, the app calculates the weighted average of available metric scores using the selected weights. Weights are normalized automatically. Missing metrics are excluded from the average and reduce evidence coverage. This MVP expects input metric values already transformed to a consistent 0–100 desirability scale; a later data-ingestion phase should define and test normalization per metric.

## Project structure

```text
app.py
gcc_intelligence/
  __init__.py
  db.py
  llm.py
  research/
    graph.py
    tavily_client.py
    evidence.py
    persistence.py
  sample_data.py
  scoring.py
requirements.txt
.env.example
```

## Live market research (prototype)

The **Live Research** tab runs a bounded LangGraph workflow on demand. It creates up to three search queries, calls Tavily Search with at most four results per query, validates URL/required fields, optionally asks Groq for a source-grounded synthesis, and can save the run and evidence to PostgreSQL. Research results are exported as CSV and shown with source links.

- Set `TAVILY_API_KEY` to enable live research. Set `GROQ_API_KEY` to enable synthesis; without it, source snippets are shown directly.
- Local development: place `.env` in the repository root (same directory as `app.py`) and use `TAVILY_API_KEY=your_key` with no quotes required. Hosted Streamlit: add `TAVILY_API_KEY` in App Settings → Secrets instead of relying on a local `.env` file. Restart/redeploy after changing secrets.
- Keep requests on demand to control free-tier usage. Provider quotas/rate limits may change; this prototype does not intentionally configure paid fallbacks.
- `market_research_evidence.evidence_status` remains `UNVERIFIED`. Structural URL checks are not fact-checking or independent corroboration.
- The workflow never writes to `city_metrics` and never changes suitability scores. Synthetic demo fallback and the existing UI theme remain unchanged.
- MCP is intentionally deferred for this prototype; Tavily is called through its direct Python API.
- PostgreSQL persistence creates `market_research_runs` and `market_research_evidence` tables when the first research run is saved. If `DATABASE_URL` is absent, results remain available in the current Streamlit session only.

## Planned next steps
1. Add stronger source verification and independent corroboration.
2. Add tests for graph routing, provider failures, and persistence behavior.
3. Consider Tavily MCP only if standardized tool access becomes useful.


## Market Signals dataset

The **Market Signals** feature uses a separate `market_observations` table. Office-market volumes and GCC-unit estimates must never be inserted into `city_metrics`, whose values are normalized 0–100 desirability scores.

1. Download `gcc_market_observations.csv` from this repository.
2. Start Streamlit and click **Initialize database tables** in the sidebar. This creates `market_observations` without seeding or deleting records.
3. In pgAdmin, import the CSV into `market_observations` as CSV, with header enabled and comma delimiter. Map the 11 same-named CSV columns. Leave `id` and `imported_at` unmapped for PostgreSQL defaults.
4. Unique key: `(city, metric_key, period, source_name)`. For safe re-imports use a staging table and `INSERT ... ON CONFLICT DO NOTHING`; direct pgAdmin import may report duplicate-key errors rather than skip conflicts.
5. Refresh Streamlit. Market Signals reads only database observations and shows an empty state until data is imported.

### Data provenance and caveats

- JLL India office-market release, published 15 January 2026: [source](https://www.jll.com/en-in/newsroom/india-s-office-market-scales-unprecedented-highs-with-gross-leasing-activity-at-83-3-million-sq-ft-for-the-year-2025-jll). Gross leasing excludes term renewals; net absorption is the net change in occupied space. These are overall office-market measures, not GCC-only metrics.
- NASSCOM–Zinnov India GCC Landscape Report 2026, FY26E: [PDF](https://media.zinnov.com/wp-content/uploads/2026/05/zinnov-nasscom-india-gcc-landscape-2026-report.pdf). Figures ending in `+` are lower bounds, not exact audited counts.

### Verification SQL

```sql
SELECT metric_key, period, COUNT(*) AS observation_count
FROM market_observations GROUP BY metric_key, period ORDER BY metric_key, period;
```

```sql
SELECT city, metric_key, value, unit, period, evidence_status, source_url
FROM market_observations ORDER BY metric_key, period, city;
```
