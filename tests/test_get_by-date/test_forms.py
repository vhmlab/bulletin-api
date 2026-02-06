import os
import sys
import sqlite3
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def test_forms_by_date(tmp_path):
    # Place the sqlite DB next to this test file so it can be inspected
    db_file = Path(__file__).resolve().with_suffix(".db")
    import importlib
    dbmod = importlib.import_module("app.database")
    dbmod.DEFAULT_DB = db_file

    # Create tables and insert a sabbath_school entry for 2026-04
    from app.database import _resolve_db_path

    db_path = db_file
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    for t in ["sabbath_school", "worship_service", "youth_service", "wednesday_service"]:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, date TEXT, data TEXT)")

    conn.execute("DELETE FROM sabbath_school WHERE date = ?", ("2026-04",))
    conn.execute(
        "INSERT INTO sabbath_school (date, data) VALUES (?, ?)",
        ("2026-04", json.dumps([{"name": "example", "value": "x"}])),
    )
    conn.commit()
    conn.close()

    # Import app after environment is configured
    from app.main import app

    client = TestClient(app)
    resp = client.get("/forms/by-date/2026-04")

    assert resp.status_code == 200
    assert resp.json() == {
        "sabbath_school": True,
        "worship_service": False,
        "youth_service": False,
        "wednesday_service": False,
    }
