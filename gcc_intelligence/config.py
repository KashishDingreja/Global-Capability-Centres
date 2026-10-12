"""Centralized environment and Streamlit Secrets configuration."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
# Load from the repository root even when Streamlit is launched from another cwd.
load_dotenv(dotenv_path=ENV_FILE, override=False)


def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    # Streamlit Community Cloud uses app Settings > Secrets instead of a local .env.
    try:
        import streamlit as st
        secret = st.secrets.get(name, default)
        return str(secret).strip() if secret is not None else default
    except Exception:
        return default
