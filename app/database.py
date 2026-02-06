"""SQLite-backed DB access (drop-in replacement for previous SQLAlchemy usage).

This module provides a `get_db` dependency that yields a sqlite3.Connection
and a lightweight `init_db` that ensures the database file exists. The
connection uses `sqlite3.Row` as row factory so callers can access rows as
mappings.
"""
import os
import sqlite3
from pathlib import Path
from typing import Generator

from .config import settings
from fastapi import HTTPException


# Resolve filesystem path from DATABASE_URL which may be like
# sqlite:///./boletin.db
def _resolve_db_path(db_url: str) -> Path:
    if db_url.startswith("sqlite:///"):
        return Path(db_url.replace("sqlite:///", "", 1)).resolve()
    return Path(db_url).resolve()


DEFAULT_DB = _resolve_db_path(settings.DATABASE_URL)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a sqlite3.Connection with row factory set to sqlite3.Row.

    Implemented as a plain generator so FastAPI can use it as a dependency
    that runs cleanup after the request.
    """
    try:
        conn = sqlite3.connect(str(DEFAULT_DB))
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Ensure the database file exists; do not attempt to create schema.

    The project typically ships with an existing SQLite file (e.g. `boletin.db`).
    Creating tables automatically could be surprising, so this only ensures the
    file exists for local development or container startup.
    """
    db_path = DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        # Create an empty sqlite file
        open(db_path, "a").close()
    # Ensure a UNIQUE index exists on the `date` column for each service table.
    # This enforces uniqueness at the DB level without modifying table schemas.
    tables = ["sabbath_school", "worship_service", "youth_service", "wednesday_service"]
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for t in tables:
            # Only attempt to create the index if the table exists
            r = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (t,)).fetchone()
            if not r:
                continue
            # Create a unique index on date if it doesn't already exist
            idx_name = f"idx_{t}_date_unique"
            try:
                cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {t}(date)")
            except sqlite3.OperationalError:
                # If something goes wrong creating the index, ignore to avoid
                # startup failure; application-level checks also exist.
                pass
        conn.commit()
    except sqlite3.OperationalError:
        # Ignore DB errors here; other parts of the app will raise HTTP 500
        # when attempting to open the DB during requests.
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
