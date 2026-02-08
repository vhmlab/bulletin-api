import json
import sqlite3
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))


def test_post_date_only_creates_entry(per_test_db):
    """POST /{service}/ with only `date` should create an entry with `data` == []"""
    from app.main import app

    client = TestClient(app)

    payload = {"date": "2026-05"}
    resp = client.post("/worship_service/", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body, dict)
    assert body.get("date") == "2026-05"
    assert isinstance(body.get("id"), int)
    assert body.get("data") == []

    # Verify DB row exists and stored data is empty list
    conn = sqlite3.connect(str(per_test_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id, date, data FROM worship_service WHERE date = ?", ("2026-05",)).fetchone()
    assert row is not None
    stored = json.loads(row["data"]) if row["data"] else []
    assert stored == []
    conn.close()
