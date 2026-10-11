# GCC Intelligence

An evidence-led prototype for comparing Indian cities for Global Capability Centre (GCC) setup or expansion.

## Current MVP
- Streamlit city comparison dashboard
- Configurable decision weights
- Deterministic Python scoring and evidence coverage
- Evidence explorer with source and caveat fields
- Optional Groq-generated explanation (LLM does not calculate rankings)
- Optional local PostgreSQL persistence

> **Data integrity notice:** Bundled city values are synthetic fixtures for demonstrating the workflow. They are not verified market facts and must not be used for investment decisions. Replace them with observations from credible sources and retain source URLs, observation dates, definitions, and caveats.

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
