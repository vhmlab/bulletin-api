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
        # Ensure table is empty so tests are idempotent when DB file persists
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()


def test_duplicate_creation_all_services(tmp_path):
    _prepare_db(tmp_path)

    from app.main import app

    client = TestClient(app)

    services = [
        "/sabbath_school/",
        "/worship_service/",
        "/youth_service/",
        "/wednesday_service/",
    ]

    # Use realistic example data from tests/example.json
    example_path = Path(__file__).resolve().parents[1] / "example.json"
    example_data = json.loads(example_path.read_text())
    payload = {"date": "2026-05", "data": example_data}

    for endpoint in services:
        resp = client.post(endpoint, json=payload)
        assert resp.status_code == 201, f"Expected 201 creating first entry at {endpoint}, got {resp.status_code}"

        # second attempt should fail with 409 Conflict
        resp2 = client.post(endpoint, json=payload)
        assert resp2.status_code == 409, f"Expected 409 on duplicate create at {endpoint}, got {resp2.status_code}"
