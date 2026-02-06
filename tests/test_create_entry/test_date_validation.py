import os
import sys
import sqlite3
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def _prepare_db(tmp_path):
    # Place the sqlite DB next to this test file so it can be inspected
    db_file = Path(__file__).resolve().with_suffix(".db")
    import importlib
    dbmod = importlib.import_module("app.database")
    dbmod.DEFAULT_DB = db_file

    db_path = db_file
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    for t in ["sabbath_school", "worship_service", "youth_service", "wednesday_service"]:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, date TEXT, data TEXT)")
        # Ensure table is empty so tests run idempotently when DB file persists
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()


def test_create_invalid_date_format(per_test_db, example_data):
    from app.main import app

    client = TestClient(app)

    # invalid formats
    for bad in ["2026-4", "26-04", "2026-00", "2026-54", "abcd-ef"]:
        resp = client.post("/sabbath_school/", json={"date": bad, "data": example_data})
        assert resp.status_code == 400
        assert "Invalid date format" in resp.json().get("detail", "")


def test_create_duplicate_date(per_test_db, example_data):
    from app.main import app

    client = TestClient(app)

    valid = {"date": "2026-04", "data": example_data}
    resp = client.post("/sabbath_school/", json=valid)
    assert resp.status_code == 201

    # creating the same date again should return 409 Conflict
    resp2 = client.post("/sabbath_school/", json=valid)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json().get("detail", "")
