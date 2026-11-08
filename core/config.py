"""Central configuration. Reads Streamlit secrets first, then environment variables."""
import os

import streamlit as st

APP_NAME = "GradPath AI"
APP_FULL_NAME = "Graduate Career Placement Prediction System (GCPPS)"
TAGLINE = "Your potential. Your pathway. Your next opportunity."
VERSION = "1.1.0"
CGPA_SCALE = 4.0  # change to 10.0 if your university uses a 10-point scale

DEGREES = ["BS", "BE / BEng", "BSc", "BBA", "MS / MSc", "MBA", "Other"]
DEPARTMENTS = [
    "Computer Science", "Software Engineering", "Data Science",
    "Information Technology", "Electrical Engineering", "Business Analytics",
]
READINESS_LEVELS = ["Needs Improvement", "Developing", "Job Ready"]

DEMO_STUDENT_EMAIL = "demo@gradpath.ai"
DEMO_STUDENT_PASSWORD = "Demo@1234"
DEMO_OFFICER_EMAIL = "officer@gradpath.ai"
DEMO_OFFICER_PASSWORD = "Officer@1234"


def get_setting(key: str, default=None):
    """Read a setting from Streamlit secrets, then the process environment."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


def database_url() -> str:
    """Return a normalized database URL, defaulting to local SQLite for development."""
    url = get_setting("DATABASE_URL")
    if not url:
        return "sqlite:///gradpath_local.db"  # local development fallback
    url = str(url).strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def using_postgres() -> bool:
    """Report whether the configured database URL targets PostgreSQL."""
    return database_url().startswith("postgresql")


def officer_access_code() -> str:
    """Secret code needed to register as a Career Officer. Empty = officer sign-up is disabled."""
    return str(get_setting("OFFICER_ACCESS_CODE", "") or "").strip()


def demo_login_enabled() -> bool:
    """Return whether demo credentials should be available on the sign-in page."""
    return str(get_setting("ENABLE_DEMO_LOGIN", "true")).lower() == "true"