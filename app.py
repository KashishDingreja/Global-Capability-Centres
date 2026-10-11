import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from gcc_intelligence.sample_data import demo_metrics
from gcc_intelligence.scoring import score_cities, DEFAULT_WEIGHTS, METRICS
from gcc_intelligence.db import database_status, load_metrics, initialize_database
from gcc_intelligence.llm import generate_decision_brief

load_dotenv()
st.set_page_config(page_title="GCC Intelligence", page_icon="🌐", layout="wide")

NAVY = "#10243A"
TEAL = "#0F9D91"
PALE_TEAL = "#E7F5F3"
SLATE = "#5B6B7A"
METRIC_LABELS = {
    "talent_depth": "Talent depth",
    "operating_cost": "Cost attractiveness",
    "ecosystem": "GCC ecosystem",
    "infrastructure": "Infrastructure",
}

st.markdown("""
<style>
:root { --primary-color: #0F9D91; }
.stApp { background: #F7F9FC; color: #172B3A; }
.block-container { padding-top: 1.4rem; padding-bottom: 2.4rem; max-width: 1500px; }
[data-testid="stSidebar"] { background: #10243A; }
[data-testid="stSidebar"] * { color: #F4F8FB; }
[data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] { background: #0F9D91; }
[data-testid="stMetric"] { background: white; border: 1px solid #E4EAF0; padding: 16px 18px; border-radius: 14px; box-shadow: 0 2px 8px rgba(16,36,58,.035); }
[data-testid="stMetricLabel"] { color: #5B6B7A; }
h1, h2, h3 { color: #10243A; letter-spacing: -0.02em; }
div[data-testid="stTabs"] button[aria-selected="true"] { color: #0F766E; border-bottom-color: #0F9D91; }
.stButton > button[kind="primary"] { background: #0F9D91; border-color: #0F9D91; }
div[data-testid="stAlert"] { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("GCC Intelligence")
st.caption("A decision workspace for evaluating Indian cities for Global Capability Centre setup and expansion.")

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

tab1, tab2, tab3 = st.tabs(["City comparison", "Evidence explorer", "Decision brief"])

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
            chart.update_xaxes(gridcolor="#E5EBF0", zeroline=False)
            chart.update_yaxes(showgrid=False)
            st.plotly_chart(chart, use_container_width=True)
    with right:
        st.markdown("#### Metric profile")
        radar_city = st.selectbox("City profile", ranked["city"].tolist(), key="radar_city")
        radar_row = ranked[ranked["city"] == radar_city].iloc[0]
        radar_values = [radar_row[k] if pd.notna(radar_row[k]) else 0 for k in METRICS]
        radar_labels = [METRIC_LABELS[k] for k in METRICS]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(r=radar_values + radar_values[:1], theta=radar_labels + radar_labels[:1], fill="toself", name=radar_city, line=dict(color=TEAL, width=2), fillcolor="rgba(15,157,145,0.16)"))
        radar.update_layout(height=330, showlegend=False, margin=dict(l=26, r=26, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", font_color=NAVY, polar=dict(radialaxis=dict(visible=True, range=[0, 100], gridcolor="#E5EBF0"), angularaxis=dict(gridcolor="#E5EBF0")))
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

with tab3:
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

st.divider()
st.caption("GCC Intelligence MVP · Deterministic scoring · PostgreSQL persistence · Optional Groq explanation")
