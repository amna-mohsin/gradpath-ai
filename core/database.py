"""Database engine, sessions and safe, repeatable initialisation."""
from contextlib import contextmanager

import streamlit as st
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from core.config import database_url
from core.models import Base


@st.cache_resource(show_spinner=False)
def get_engine():
    """Create the cached SQLAlchemy engine with SQLite- or PostgreSQL-specific options."""
    url = database_url()
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    # pool_pre_ping + pool_recycle handle Neon's auto-suspend (idle connections get dropped)
    return create_engine(url, pool_pre_ping=True, pool_recycle=240, pool_size=3, max_overflow=2)


@st.cache_resource(show_spinner=False)
def get_sessionmaker():
    """Return a cached session factory whose objects remain usable after commit."""
    # expire_on_commit=False keeps objects usable after the session closes
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope():
    """Yield a database session and commit it, rolling back if its work fails."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# (table, column, SQL type, default) - added only if the column is missing (keeps existing data)
MIGRATIONS = [
    ("students", "phone", "VARCHAR(30)", "''"),
    ("students", "city", "VARCHAR(80)", "''"),
    ("students", "portfolio_url", "VARCHAR(200)", "''"),
    ("jobs", "created_by", "INTEGER", "NULL"),
    ("jobs", "is_open", "BOOLEAN", "TRUE"),
    ("job_applications", "resume_pdf", "BYTEA", "NULL"),
]


def run_migrations(engine) -> None:
    """Add missing compatibility columns without dropping or rewriting existing data."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for table, column, ddl, default in MIGRATIONS:
        if table not in tables:
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        if column not in existing:
            if table == "job_applications" and engine.dialect.name == "sqlite":
                ddl = "BLOB"
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl} DEFAULT {default}"))


@st.cache_resource(show_spinner="Setting up the database...")
def init_database() -> bool:
    """Creates missing tables and seeds demo data once. Never deletes existing data."""
    from data.seed import seed_demo_data

    engine = get_engine()
    Base.metadata.create_all(engine)
    run_migrations(engine)
    seed_demo_data()
    return True
