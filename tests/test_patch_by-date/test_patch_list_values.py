import json
import os
import sqlite3
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

# NOTE: do not import app.database at module import time; import inside helpers
_resolve_db_path = None


def create_sample_entries(monkeypatch, create_multiple: bool = False, per_test_db=None, example_data=None):
    # If fixtures are provided directly, use them; otherwise set up DB next to test
    if per_test_db is None:
        db_file = Path(__file__).resolve().with_suffix(".db")
        import importlib
        dbmod = importlib.import_module("app.database")
        dbmod.DEFAULT_DB = db_file
    else:
        db_file = per_test_db

    db_path = db_file
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    for t in ["sabbath_school", "worship_service", "youth_service", "wednesday_service"]:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, date TEXT, data TEXT)")

    # Use provided example_data fixture if available
    if example_data is None:
        example_path = Path(__file__).resolve().parents[1] / "example.json"
        worship_data = json.loads(example_path.read_text())
    else:
        worship_data = example_data

    conn.execute("DELETE FROM worship_service WHERE date = ?", ("2026-04",))
    conn.execute(
        "INSERT INTO worship_service (date, data) VALUES (?, ?)",
        ("2026-04", json.dumps(worship_data)),
    )
    if create_multiple:
        conn.execute(
            "INSERT INTO worship_service (date, data) VALUES (?, ?)",
            ("2026-04", json.dumps(worship_data)),
        )
    conn.commit()
    conn.close()
    return db_file


def test_patch_valid_list_updates(per_test_db, example_data, monkeypatch):
    dbpath = create_sample_entries(monkeypatch, per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    # update using list of dicts where keys match existing items
    # payload contains only the nested `value` dicts to apply
    payload = [{"topic": 0, "sub": 0, "number": 35, "url": ""}, {"translation": 16, "book": "Genesis", "chapter": 2, "verse_start": 5, "verse_end": 5}]
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["date"] == "2026-04"
    # ensure updated value is present for the hymn entry
    found = False
    for item in data[0]["data"]:
        if isinstance(item, dict) and item.get("type") == "hymn":
            assert isinstance(item.get("value"), dict)
            assert item.get("value")["number"] == 35
            found = True
            break
    assert found


def test_patch_key_mismatch_rejected(per_test_db, example_data, monkeypatch):
    dbpath = create_sample_entries(monkeypatch, per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    # use a dict whose keys don't match any stored nested `value` dict
    payload = [{"title": "Non existing", "value": "X"}]
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code == 400


def test_patch_non_list_rejected(per_test_db, example_data, monkeypatch):
    dbpath = create_sample_entries(monkeypatch, per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    payload = "not-a-list"
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code in (400, 422)


def test_patch_atomic_across_entries(per_test_db, example_data, monkeypatch):
    # create two entries with same date and ensure update applies to both or none
    dbpath = create_sample_entries(monkeypatch, create_multiple=True, per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    payload = [{"topic": 0, "sub": 0, "number": 99, "url": ""}]
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code == 200
    data = r.json()
    # If multiple entries exist for the same date, the update should apply to all
    assert len(data) >= 2
    for entry in data:
        found = False
        for item in entry["data"]:
            if isinstance(item, dict) and item.get("type") == "hymn":
                assert isinstance(item.get("value"), dict)
                assert item.get("value")["number"] == 99
                found = True
                break
        assert found
