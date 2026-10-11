# GCC Intelligence

An evidence-led prototype for comparing Indian cities for Global Capability Centre (GCC) setup or expansion.

## Current MVP
- Streamlit city comparison dashboard
- Configurable decision weights
- Deterministic Python scoring and evidence coverage
- Evidence explorer with source and caveat fields
- Optional Groq-generated explanation (LLM does not calculate rankings)
- Optional local PostgreSQL persistence

> **Data integrity notice:** The dashboard does not automatically substitute synthetic suitability scores when PostgreSQL is empty or unavailable. Market observations are shown in their original units and are not treated as 0–100 suitability scores. Explicitly illustrative/demo city metric records are excluded from ranking.

## Run locally (Windows PowerShell)

1. Install Python 3.11 or newer.
2. Create and activate an environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env`. Add `GROQ_API_KEY` only if you want the optional AI brief.
4. Run the demo without PostgreSQL first:
   ```powershell
   streamlit run app.py
   ```
   When PostgreSQL is blank or unavailable, the app shows a connection warning and does not invent city scores. Market Signals and evidence-backed comparisons require the database connection.

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
  sample_data.py
  scoring.py
requirements.txt
.env.example
```

## Planned next steps
1. Replace synthetic fixtures with a curated evidence dataset and source registry.
2. Add tests for scoring, missing-data behavior, and weight sensitivity.
3. Add assessment save/load and decision brief export.
4. Integrate research APIs/MCP after the core workflow is stable.


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
