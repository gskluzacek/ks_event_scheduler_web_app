"""
SQLite engine + session helpers.

The `sqlite3`/SQLAlchemy driver is synchronous, so every call through it
would block NiceGUI's single event loop (nicegui_llms.md Mental Model #7).
Callers don't use `Session` directly - they go through app/data/*.py, whose
functions wrap each query in `run.io_bound`.
"""
from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = Path(__file__).resolve().parent.parent / "kingshot.db"
engine = create_engine(f"sqlite:///{DB_PATH}")


def init_db() -> None:
    """Creates any tables that don't exist yet. Safe to call on every startup -
    existing tables and data are left alone."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
