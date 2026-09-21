"""
SQLite engine + session helpers.

The `sqlite3`/SQLAlchemy driver is synchronous, so every call through it
would block NiceGUI's single event loop (nicegui_llms.md Mental Model #7).
Callers don't use `Session` directly - they go through app/data/*.py, whose
functions wrap each query in `run.io_bound`.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

DB_PATH = Path(__file__).resolve().parent.parent / "kingshot.db"
engine = create_engine(f"sqlite:///{DB_PATH}")


def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite ignores FOREIGN KEY constraints unless this PRAGMA is set on every new
    connection - without it, the FKs declared in app/models/schema.py are decoration."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


event.listen(engine, "connect", enable_foreign_keys)


def init_db() -> None:
    """Creates any tables that don't exist yet. Safe to call on every startup -
    existing tables and data are left alone."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
