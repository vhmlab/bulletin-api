import os
import sys
import sqlite3
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def test_forms_by_date(per_test_db, example_data):
    # Prepare per-test DB and insert a sabbath_school entry for 2026-04
    db_file = per_test_db

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    conn.execute("DELETE FROM sabbath_school WHERE date = ?", ("2026-04",))
    conn.execute(
        "INSERT INTO sabbath_school (date, data) VALUES (?, ?)",
        ("2026-04", json.dumps(example_data)),
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
