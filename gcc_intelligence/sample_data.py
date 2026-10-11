"""Clearly labelled synthetic starter data for interface and scoring development."""
import pandas as pd

DEMO_NOTICE = "Illustrative demo value — replace with a verified source before decision use."

def demo_metrics() -> pd.DataFrame:
    # These numbers are deliberately synthetic. They are not claims about actual cities.
    raw = {
        "Bengaluru": {"talent_depth": 88, "operating_cost": 55, "ecosystem": 92, "infrastructure": 78},
        "Hyderabad": {"talent_depth": 79, "operating_cost": 72, "ecosystem": 80, "infrastructure": 80},
        "Pune": {"talent_depth": 72, "operating_cost": 76, "ecosystem": 72, "infrastructure": 73},
        "Chennai": {"talent_depth": 74, "operating_cost": 74, "ecosystem": 73, "infrastructure": 77},
    }
    metric_info = {
        "talent_depth": ("Talent depth", "index points"),
        "operating_cost": ("Operating cost attractiveness", "index points"),
        "ecosystem": ("GCC ecosystem maturity", "index points"),
        "infrastructure": ("Infrastructure readiness", "index points"),
    }
    rows = []
    for city, values in raw.items():
        for key, value in values.items():
            label, unit = metric_info[key]
            rows.append({
                "city": city, "metric_key": key, "metric_label": label,
                "value": value, "unit": unit, "source_name": "Synthetic prototype fixture",
                "source_url": "", "observed_at": "Not applicable",
                "evidence_status": "ILLUSTRATIVE", "caveat": DEMO_NOTICE,
            })
    return pd.DataFrame(rows)
