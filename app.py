import os
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from gcc_intelligence.sample_data import demo_metrics
from gcc_intelligence.scoring import score_cities, DEFAULT_WEIGHTS
from gcc_intelligence.db import database_status, load_metrics, initialize_database
from gcc_intelligence.llm import generate_decision_brief

load_dotenv()
st.set_page_config(page_title="GCC Intelligence", page_icon="🌐", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: #f5f7fb; padding: 14px 16px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("GCC Intelligence")
st.caption("Evidence-led decisions for selecting and expanding Global Capability Centres in India")
st.info(
    "Prototype data notice: the starter city metrics are illustrative demo values, not verified market facts. "
    "Replace them with sourced observations before using rankings for a real investment decision.",
    icon="ℹ️",
)

with st.sidebar:
    st.header("Assessment setup")
    selected_cities = st.multiselect(
        "Cities to compare",
        ["Bengaluru", "Hyderabad", "Pune", "Chennai"],
        default=["Bengaluru", "Hyderabad", "Pune", "Chennai"],
    )
    st.divider()
    st.subheader("Decision priorities")
    st.caption("Adjust weights to reflect your organization's needs.")
    weights = {}
    labels = {
        "talent_depth": "Talent depth",
        "operating_cost": "Operating cost",
        "ecosystem": "GCC ecosystem",
        "infrastructure": "Infrastructure",
    }
    for key, label in labels.items():
        weights[key] = st.slider(label, 0, 100, DEFAULT_WEIGHTS[key], 5)
    st.caption("Weights are normalized automatically; zero total weight is not allowed.")
    st.divider()
    use_database = st.toggle("Use local PostgreSQL if configured", value=True)
    if st.button("Initialize database tables", use_container_width=True):
        ok, message = initialize_database()
        (st.success if ok else st.warning)(message)

metrics = None
db_message = "Using bundled illustrative demo data."
if use_database:
    try:
        stored = load_metrics()
        if stored is not None and not stored.empty:
            metrics = stored
            db_message = "Loaded metrics from local PostgreSQL."
    except Exception as exc:
        db_message = f"PostgreSQL unavailable; using demo data instead ({type(exc).__name__})."
if metrics is None:
    metrics = demo_metrics()

st.caption(f"Data source: {db_message}")
filtered = metrics[metrics["city"].isin(selected_cities)].copy()
if filtered.empty:
    st.warning("Select at least one city to begin.")
    st.stop()

results = score_cities(filtered, weights)
ranked = results.sort_values("overall_score", ascending=False).reset_index(drop=True)

best = ranked.iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Cities compared", len(ranked))
c2.metric("Top-ranked city", best["city"])
c3.metric("Top score", f'{best["overall_score"]:.0f}/100')
c4.metric("Evidence coverage", f'{ranked["evidence_coverage"].mean():.0f}%')

tab1, tab2, tab3 = st.tabs(["City comparison", "Evidence explorer", "Decision brief"])

with tab1:
    st.subheader("Compare city suitability")
    st.caption("Scores are normalized to 0–100 from the currently available metric values. Evidence coverage is shown separately.")
    chart = px.bar(
        ranked.sort_values("overall_score"),
        x="overall_score", y="city", orientation="h",
        text="overall_score", range_x=[0, 100],
        labels={"overall_score": "Weighted suitability score", "city": ""},
    )
    chart.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    chart.update_layout(height=320, margin=dict(l=10, r=30, t=20, b=10))
    st.plotly_chart(chart, use_container_width=True)
    display_cols = ["city", "overall_score", "evidence_coverage", *labels.keys()]
    display = ranked[display_cols].rename(columns={
        "city": "City", "overall_score": "Suitability score",
        "evidence_coverage": "Evidence coverage (%)",
        "talent_depth": "Talent", "operating_cost": "Cost",
        "ecosystem": "Ecosystem", "infrastructure": "Infrastructure",
    })
    st.dataframe(display.round(1), use_container_width=True, hide_index=True)
    st.download_button(
        "Export comparison as CSV",
        ranked.to_csv(index=False).encode("utf-8"),
        file_name="gcc_city_comparison.csv",
        mime="text/csv",
    )

with tab2:
    st.subheader("Metric-level evidence")
    city_choice = st.selectbox("Choose a city", ranked["city"].tolist())
    city_rows = filtered[filtered["city"] == city_choice].copy()
    if "metric_label" not in city_rows.columns:
        city_rows["metric_label"] = city_rows["metric_key"].map(labels).fillna(city_rows["metric_key"])
    cols = [c for c in ["metric_label", "value", "unit", "source_name", "source_url", "observed_at", "evidence_status", "caveat"] if c in city_rows.columns]
    st.dataframe(city_rows[cols], use_container_width=True, hide_index=True)
    st.caption("A source URL is only meaningful when it points to the original publisher and supports the specific observation.")

with tab3:
    st.subheader("Decision brief")
    priorities = ", ".join(f"{labels[k]} ({v})" for k, v in weights.items())
    st.write(f"**Assessment priorities:** {priorities}")
    st.write(f"**Current leader:** {best['city']} with a weighted score of {best['overall_score']:.1f}/100.")
    st.write("**Interpretation:** Treat this as a screening result, not a probability or an investment recommendation. Confirm source quality, data recency, role-specific talent availability, and city-level costs before deciding.")
    if st.button("Draft explanation with Groq", type="primary"):
        with st.spinner("Preparing an evidence-grounded explanation…"):
            brief, note = generate_decision_brief(ranked, filtered, weights)
        st.markdown(brief)
        if note:
            st.caption(note)

st.divider()
st.caption("GCC Intelligence MVP · Research connectors intentionally deferred until the core assessment workflow is stable.")
