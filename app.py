import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from gcc_intelligence.sample_data import demo_metrics
from gcc_intelligence.scoring import score_cities, DEFAULT_WEIGHTS, METRICS
from gcc_intelligence.db import database_status, load_metrics, load_market_observations, initialize_database
from gcc_intelligence.llm import generate_decision_brief
from gcc_intelligence.research.graph import run_market_research
from gcc_intelligence.config import get_setting

load_dotenv()
st.set_page_config(page_title="GCC Intelligence", page_icon="🌐", layout="wide")

NAVY = "#F4F5FA"
TEAL = "#2E9CCA"
BLUE = "#29648A"
MUTED = "#AAABB8"
GRID = "#464866"
PANEL = "#464866"
BG = "#25274D"
METRIC_LABELS = {
    "talent_depth": "Talent depth",
    "operating_cost": "Cost attractiveness",
    "ecosystem": "GCC ecosystem",
    "infrastructure": "Infrastructure",
}

st.markdown("""
<style>
:root { --primary-color: #2E9CCA; }
.stApp { background: #25274D; color: #F4F5FA; }
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px; }
[data-testid="stHeader"] { background: rgba(37,39,77,.94); }
[data-testid="stSidebar"] { background: #464866; border-right: 1px solid #29648A; }
[data-testid="stSidebar"] * { color: #F4F5FA; }
[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] { background: #2E9CCA; }
[data-testid="stMetric"] { background: #464866; border: 1px solid #29648A; padding: 14px 16px; border-radius: 12px; }
[data-testid="stMetricLabel"] { color: #AAABB8; }
[data-testid="stMetricValue"] { color: #F4F5FA; }
h1, h2, h3, h4 { color: #F4F5FA; letter-spacing: -0.02em; }
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: #E4E5EE; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #2E9CCA; border-bottom-color: #2E9CCA; }
.stButton > button[kind="primary"] { background: #2E9CCA; border-color: #2E9CCA; color: #25274D; font-weight: 650; }
.stButton > button { border-radius: 9px; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid #29648A; border-radius: 10px; }
div[data-testid="stAlert"] { border-radius: 10px; background: #464866; }
a { color: #55BDE7; }
hr { border-color: #29648A; }
[data-testid="stExpander"] { background: rgba(70,72,102,.45); border: 1px solid #464866; border-radius: 10px; }
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] { background: #464866; }
</style>
""", unsafe_allow_html=True)


st.title("GCC Intelligence")
st.caption("LOCATION STRATEGY  /  INDIA  ·  A decision workspace for GCC setup and expansion.")

with st.sidebar:
    st.markdown("## Assessment setup")
    st.caption("Configure the shortlist and what matters most to your organisation.")
    selected_cities = st.multiselect(
        "Cities to compare",
        ["Bengaluru", "Hyderabad", "Pune", "Chennai"],
        default=["Bengaluru", "Hyderabad", "Pune", "Chennai"],
    )
    st.divider()
    st.markdown("### Decision priorities")
    weights = {}
    for key, label in METRIC_LABELS.items():
        weights[key] = st.slider(label, 0, 100, DEFAULT_WEIGHTS[key], 5, key=f"weight_{key}")
    total_weight = sum(weights.values())
    if total_weight == 0:
        st.warning("Set at least one priority above zero to calculate a ranking.")
    st.caption(f"Total priority points: {total_weight} · weights are normalized for scoring.")
    st.divider()
    use_database = st.toggle("Use configured PostgreSQL", value=True)
    if st.button("Initialize database tables", use_container_width=True):
        ok, message = initialize_database()
        (st.success if ok else st.error)(message)

metrics = None
data_mode = "ILLUSTRATIVE DEMO"
db_connected = False
db_detail = "PostgreSQL is disabled for this session."
if use_database:
    db_connected, db_detail = database_status()
    if db_connected:
        try:
            stored = load_metrics()
            if stored is not None and not stored.empty:
                metrics = stored
                data_mode = "DATABASE RECORDS"
                db_detail = f"Connected · {len(stored):,} metric records loaded."
            else:
                db_detail = "Connected, but no metric records were found. Showing clearly labelled illustrative demo data."
        except Exception as exc:
            db_detail = f"Database read failed ({type(exc).__name__}). Showing illustrative demo data."
    else:
        db_detail = f"{db_detail} Showing illustrative demo data."

if metrics is None:
    metrics = demo_metrics()

is_demo = data_mode == "ILLUSTRATIVE DEMO"
if is_demo:
    st.warning(
        "DEMO MODE — City values are synthetic fixtures used to demonstrate the workflow. "
        "They are not verified market facts and must not inform an actual investment decision.",
        icon="⚠️",
    )
else:
    st.success("DATABASE MODE — The dashboard is using records stored in PostgreSQL. Check each record's evidence status before relying on it.")

with st.expander("Data connection and trust status", expanded=False):
    st.write(f"**Active data mode:** {data_mode}")
    st.write(f"**PostgreSQL:** {db_detail}")
    st.caption("A successful database connection does not make a metric verified. Source, date, definition, status and caveat should be checked record by record.")

if not selected_cities:
    st.info("Choose at least one city in the sidebar to start comparing.")
    st.stop()
if total_weight <= 0:
    st.error("The total decision weight is zero. Increase at least one priority in the sidebar.")
    st.stop()

filtered = metrics[metrics["city"].isin(selected_cities)].copy()
if filtered.empty:
    st.warning("There are no metric records for the selected cities. Add records to PostgreSQL or select other cities.")
    st.stop()

results = score_cities(filtered, weights)
ranked = results.sort_values("overall_score", ascending=False, na_position="last").reset_index(drop=True)
ranked["rank"] = range(1, len(ranked) + 1)
ranked["rank_label"] = ranked["rank"].map(lambda n: f"#{n}")
best_rows = ranked[ranked["overall_score"].notna()]
best = best_rows.iloc[0] if not best_rows.empty else None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cities compared", len(ranked))
c2.metric("Current leader", best["city"] if best is not None else "Not enough data")
c3.metric("Top score", f'{best["overall_score"]:.1f}/100' if best is not None else "—")
c4.metric("Average metric coverage", f'{ranked["evidence_coverage"].mean():.0f}%' if not ranked.empty else "0%")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["City comparison", "Market Signals", "Evidence explorer", "Decision brief", "Live Research"])

with tab1:
    st.subheader("Compare city suitability")
    st.caption("Scores are weighted averages of the available 0–100 desirability scores. Evidence coverage is separate; it is not a quality guarantee.")
    left, right = st.columns([1.4, 1])
    with left:
        chart_data = ranked[ranked["overall_score"].notna()].sort_values("overall_score")
        if chart_data.empty:
            st.info("No selected city has enough metric data to calculate a score.")
        else:
            chart = px.bar(
                chart_data, x="overall_score", y="city", orientation="h",
                text="overall_score", range_x=[0, 105],
                color_discrete_sequence=[TEAL],
                labels={"overall_score": "Weighted suitability score", "city": ""},
            )
            chart.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
            chart.update_layout(height=330, margin=dict(l=8, r=34, t=12, b=12), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=NAVY)
            chart.update_xaxes(gridcolor=GRID, zeroline=False)
            chart.update_yaxes(showgrid=False)
            st.plotly_chart(chart, use_container_width=True)
    with right:
        st.markdown("#### Metric profile")
        radar_city = st.selectbox("City profile", ranked["city"].tolist(), key="radar_city")
        radar_row = ranked[ranked["city"] == radar_city].iloc[0]
        radar_values = [radar_row[k] if pd.notna(radar_row[k]) else 0 for k in METRICS]
        radar_labels = [METRIC_LABELS[k] for k in METRICS]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(r=radar_values + radar_values[:1], theta=radar_labels + radar_labels[:1], fill="toself", name=radar_city, line=dict(color=TEAL, width=2), fillcolor="rgba(46,156,202,0.22)"))
        radar.update_layout(height=330, showlegend=False, margin=dict(l=26, r=26, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", font_color=NAVY, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID, color=MUTED), angularaxis=dict(gridcolor=GRID, color=MUTED)))
        st.plotly_chart(radar, use_container_width=True)
        missing = [METRIC_LABELS[k] for k in METRICS if pd.isna(radar_row[k])]
        if missing:
            st.caption("Missing metrics: " + ", ".join(missing))
    display_cols = ["rank", "city", "overall_score", "evidence_coverage", *METRICS]
    display = ranked[display_cols].rename(columns={
        "rank": "Rank", "city": "City", "overall_score": "Suitability score",
        "evidence_coverage": "Metric coverage (%)", **{k: METRIC_LABELS[k] for k in METRICS},
    })
    st.dataframe(display.round(1), use_container_width=True, hide_index=True)
    if best is not None:
        st.markdown("#### What is driving this result?")
        active_metrics = [k for k in METRICS if weights.get(k, 0) > 0 and pd.notna(best[k])]
        if active_metrics:
            strongest = sorted(active_metrics, key=lambda k: best[k], reverse=True)[:2]
            weakest = sorted(active_metrics, key=lambda k: best[k])[:2]
            x1, x2 = st.columns(2)
            x1.markdown("**Highest-scoring dimensions**")
            for k in strongest:
                x1.write(f"• {METRIC_LABELS[k]}: {best[k]:.1f}/100")
            x2.markdown("**Lowest-scoring dimensions**")
            for k in weakest:
                x2.write(f"• {METRIC_LABELS[k]}: {best[k]:.1f}/100")
        else:
            st.caption("No weighted metric values are available for this city.")
    st.download_button(
        "Export comparison as CSV",
        ranked.drop(columns=["rank_label"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name="gcc_city_comparison.csv",
        mime="text/csv",
    )

with tab2:
    st.subheader("Market Signals")
    st.caption("Office-market indicators are a proxy for the broader office ecosystem, not direct evidence of GCC-specific demand.")
    market = None
    market_error = None
    if use_database and db_connected:
        try:
            market = load_market_observations()
        except Exception as exc:
            market_error = type(exc).__name__
    if market_error:
        st.error(f"Could not load market observations ({market_error}). Check connection and table initialization.")
    elif market is None or market.empty:
        st.info("No market data imported yet. Click 'Initialize database tables', then import gcc_market_observations.csv into market_observations.")
        st.caption("No market values are invented or substituted from illustrative suitability fixtures.")
    else:
        market["value"] = pd.to_numeric(market["value"], errors="coerce")
        cities = sorted(market["city"].dropna().unique().tolist())
        focus = st.selectbox("Focus city", cities, index=cities.index("Bengaluru") if "Bengaluru" in cities else 0, key="market_focus_city")
        chosen = market[market["city"] == focus]
        gross = chosen[chosen["metric_key"] == "office_gross_leasing"]
        absorption = chosen[chosen["metric_key"] == "office_net_absorption"]
        gcc = chosen[chosen["metric_key"] == "gcc_unit_estimate"]
        def metric_value(frame, period):
            values = frame.loc[frame["period"].astype(str) == period, "value"]
            return float(values.iloc[0]) if not values.empty and pd.notna(values.iloc[0]) else None
        g24, g25 = metric_value(gross, "2024"), metric_value(gross, "2025")
        a24, a25 = metric_value(absorption, "2024"), metric_value(absorption, "2025")
        units = metric_value(gcc, "FY26E")
        k1,k2,k3,k4 = st.columns(4)
        k1.metric("2025 gross leasing", f"{g25:.1f} mn sq ft" if g25 is not None else "No data imported", f"{g25-g24:+.1f} vs 2024" if g25 is not None and g24 is not None else None)
        k2.metric("2025 net absorption", f"{a25:.1f} mn sq ft" if a25 is not None else "No data imported", f"{a25-a24:+.1f} vs 2024" if a25 is not None and a24 is not None else None)
        k3.metric("Gross leasing YoY", f"{(g25/g24-1)*100:+.1f}%" if g25 is not None and g24 not in (None,0) else "No data imported")
        k4.metric("Estimated GCC units", f"At least {int(units):,}+" if units is not None else "No data imported")
        st.markdown("#### Office-market gross leasing")
        st.caption("Overall office-market transactions, excluding term renewals; not GCC-only leasing. Million sq ft.")
        def office_chart(metric_key, title, caption):
            frame = market[market["metric_key"] == metric_key].copy()
            frame["period"] = frame["period"].astype(str)
            frame = frame[frame["period"].isin(["2024","2025"])]
            if frame.empty:
                st.info(f"No observations available for {title.lower()}.")
                return
            order = frame[frame["period"] == "2025"].sort_values("value", ascending=True)["city"].tolist()
            fig = px.bar(frame, x="value", y="city", color="period", barmode="group", orientation="h",
                         category_orders={"city":order,"period":["2024","2025"]},
                         color_discrete_map={"2024":"#29648A","2025":"#2E9CCA"},
                         labels={"value":"Million sq ft","city":"","period":"Year"})
            fig.update_layout(height=max(330,len(order)*40),margin=dict(l=8,r=18,t=8,b=12),
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color=NAVY,
                legend_title_text="",xaxis=dict(gridcolor=GRID,zeroline=False),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig,use_container_width=True)
        office_chart("office_gross_leasing","Gross leasing","")
        st.markdown("#### Net absorption")
        st.caption("Net change in occupied office space after accounting for space vacated. Million sq ft.")
        office_chart("office_net_absorption","Net absorption","")
        st.markdown("#### GCC landscape · FY26E")
        st.caption("Estimates are lower bounds, not exact audited counts. Numeric bars show lower bounds; labels retain '+'.")
        gc = market[market["metric_key"] == "gcc_unit_estimate"].copy()
        gc = gc[gc["period"].astype(str) == "FY26E"].sort_values("value", ascending=True)
        if not gc.empty:
            fig = px.bar(gc,x="value",y="city",orientation="h",text=gc["value"].map(lambda v:f"{int(v):,}+"),
                         color_discrete_sequence=["#2E9CCA"],labels={"value":"Estimated GCC units (lower bound)","city":""})
            fig.update_traces(textposition="outside",cliponaxis=False)
            fig.update_layout(height=max(340,len(gc)*38),margin=dict(l=8,r=55,t=8,b=12),
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color=NAVY,
                xaxis=dict(gridcolor=GRID,zeroline=False),yaxis=dict(gridcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig,use_container_width=True)
        with st.expander("Sources & methodology"):
            st.caption("One concise summary per source; record-level caveats remain available in the downloaded data.")
            for source_name, rows in market.groupby("source_name", dropna=False):
                statuses = rows["evidence_status"].fillna("UNVERIFIED").astype(str).str.upper()
                dates = rows["source_published_at"].dropna().astype(str).unique().tolist()
                urls = rows["source_url"].dropna().unique().tolist()
                st.markdown(f"**{source_name}**")
                st.caption(f"{len(rows)} observations · Published: {', '.join(dates) if dates else 'Date not supplied'} · Status: {', '.join(sorted(statuses.unique()))}")
                if urls:
                    st.markdown(f"[Open original source]({urls[0]})")
                source_text = " ".join(rows["caveat"].dropna().astype(str).unique().tolist()).lower()
                if "lower bound" in source_text or "user-supplied figure" in source_text:
                    st.write("**Caveat:** City-level GCC counts are lower bounds (shown with “+”); exact figures have not been independently confirmed.")
                elif "overall office-market" in source_text or "not gcc-only" in source_text:
                    st.write("**Caveat:** Office-market activity is a proxy for the wider ecosystem, not GCC-only leasing. Gross leasing excludes term renewals.")
                else:
                    st.write("**Caveat:** Review the underlying observation definitions before using these figures for a decision.")
                st.divider()
        st.download_button("Download loaded market observations",market.to_csv(index=False).encode("utf-8"),file_name="market_observations_export.csv",mime="text/csv")

with tab3:
    st.subheader("Metric-level evidence")
    city_choice = st.selectbox("Choose a city", ranked["city"].tolist(), key="evidence_city")
    city_rows = filtered[filtered["city"] == city_choice].copy()
    if "metric_label" not in city_rows.columns:
        city_rows["metric_label"] = city_rows["metric_key"].map(METRIC_LABELS).fillna(city_rows["metric_key"])
    evidence_cols = [c for c in ["metric_label", "value", "unit", "source_name", "source_url", "observed_at", "evidence_status", "caveat"] if c in city_rows.columns]
    evidence = city_rows[evidence_cols].rename(columns={
        "metric_label": "Metric", "value": "Value", "unit": "Unit", "source_name": "Source",
        "source_url": "Source URL", "observed_at": "Observed at", "evidence_status": "Evidence status", "caveat": "Caveat",
    })
    if "Source URL" in evidence.columns:
        st.dataframe(evidence, use_container_width=True, hide_index=True, column_config={"Source URL": st.column_config.LinkColumn("Source URL", display_text="Open source")})
    else:
        st.dataframe(evidence, use_container_width=True, hide_index=True)
    if "evidence_status" in city_rows.columns:
        statuses = city_rows["evidence_status"].fillna("UNVERIFIED").astype(str).str.upper()
        st.caption("Evidence-status counts: " + " · ".join(f"{status}: {int(count)}" for status, count in statuses.value_counts().items()))
    st.caption("A source link should lead to the original publisher and substantiate the specific observation. Database records are not automatically verified.")

with tab4:
    st.subheader("Decision brief")
    st.write("**Assessment priorities:** " + ", ".join(f"{METRIC_LABELS[k]} ({v})" for k, v in weights.items()))
    if best is not None:
        st.write(f'**Current leader:** {best["city"]} with a weighted score of {best["overall_score"]:.1f}/100.')
    else:
        st.write("**Current leader:** unavailable because selected cities do not have enough scored metrics.")
    st.write("**Decision guardrail:** This is a screening result, not a probability or an investment recommendation. Validate source quality, observation dates, role-specific talent availability and city-level costs before deciding.")
    if is_demo:
        st.warning("This brief is based on synthetic demo values. Do not reuse its ranking as a real-world conclusion.")
    if st.button("Draft explanation with Groq", type="primary", disabled=best is None):
        with st.spinner("Preparing an evidence-grounded explanation…"):
            brief, note = generate_decision_brief(ranked, filtered, weights)
        st.markdown(brief)
        if note:
            st.caption(note)


with tab5:
    st.subheader("Live GCC Market Research")
    st.caption("On-demand web research using Tavily, with optional Groq synthesis. Search results remain unverified evidence and do not alter city scores.")
    with st.form("live_market_research_form"):
        research_city = st.selectbox("Research city", ["Bengaluru", "Hyderabad", "Pune", "Chennai"], key="research_city")
        research_question = st.text_input(
            "What would you like to investigate?",
            value="Recent GCC expansion, hiring, office demand, talent and infrastructure signals",
            max_chars=500,
        )
        run_research = st.form_submit_button("Research this city", type="primary")
    if not get_setting("TAVILY_API_KEY"):
        st.info("Live research is not configured yet. Add TAVILY_API_KEY to your local .env file. The rest of the dashboard works without it.")
    if run_research:
        if not get_setting("TAVILY_API_KEY"):
            st.error("TAVILY_API_KEY was not found. For local runs, put it in the project-root .env file. For Streamlit Community Cloud, add it under App Settings → Secrets. Then restart/redeploy the app.")
        else:
            try:
                with st.spinner("Searching sources, checking evidence fields, and preparing a brief…"):
                    research_result = run_market_research(research_city, research_question)
                st.markdown("### Research brief")
                st.markdown(research_result.get("summary", "No summary returned."))
                if research_result.get("run_id"):
                    st.caption(f"Research run saved to PostgreSQL · run ID {research_result['run_id']}")
                elif get_setting("DATABASE_URL"):
                    st.caption("Research completed, but the run could not be saved to PostgreSQL.")
                else:
                    st.caption("DATABASE_URL is not configured; results were kept in this session only.")
                errors = research_result.get("errors", [])
                if errors:
                    with st.expander("Workflow notes"):
                        for error in errors:
                            st.write(f"• {error}")
                evidence = research_result.get("evidence", [])
                st.markdown(f"### Sources retrieved ({len(evidence)})")
                if evidence:
                    for item in evidence:
                        with st.expander(item.get("title", "Untitled source")):
                            st.markdown(f"[Open original source]({item.get('url', '')})")
                            st.caption(
                                f"Domain: {item.get('source_domain', 'unknown')} · "
                                f"Published: {item.get('published_date') or 'Date not supplied'} · "
                                f"Status: {item.get('evidence_status', 'UNVERIFIED')}"
                            )
                            st.write(item.get("snippet", ""))
                            st.caption(item.get("validation_note", ""))
                    export_rows = [{
                        "city": research_city,
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source_domain": item.get("source_domain"),
                        "published_date": item.get("published_date"),
                        "retrieved_at": item.get("retrieved_at"),
                        "evidence_status": item.get("evidence_status"),
                        "snippet": item.get("snippet"),
                    } for item in evidence]
                    st.download_button(
                        "Export research evidence as CSV",
                        pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8"),
                        file_name=f"gcc_research_{research_city.lower()}.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No usable source records were returned for this run.")
            except Exception as exc:
                st.error(f"Live research could not complete ({type(exc).__name__}). Check the API key, provider quota, and network access.")
    st.warning("Trust guardrail: URL validation is not factual verification. All search results are labelled UNVERIFIED until reviewed; live findings never modify the synthetic demo metrics or ranking.")

st.divider()
st.caption("GCC Intelligence MVP · Deterministic scoring · PostgreSQL persistence · Optional Groq explanation · On-demand live research")
