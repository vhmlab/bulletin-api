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


def create_sample_entries(monkeypatch, create_multiple: bool = False):
    # Place the sqlite DB next to this test file so it can be inspected
    db_file = Path(__file__).resolve().with_suffix(".db")
    os.environ["DISABLE_AUTH"] = "true"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    # Import _resolve_db_path after setting DATABASE_URL so DEFAULT_DB resolves correctly
    from app.database import _resolve_db_path

    db_path = _resolve_db_path(os.environ["DATABASE_URL"])
    # Ensure the application's database module uses this test DB even if it was previously imported
    import importlib
    dbmod = importlib.import_module("app.database")
    dbmod.DEFAULT_DB = db_path

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    for t in ["sabbath_school", "worship_service", "youth_service", "wednesday_service"]:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, date TEXT, data TEXT)")

    # Insert one or two worship entries for 2026-04
    worship_data = [
        {"name": "Opening Prayer", "type": "hymn", "value": {"topic": 0, "sub": 0, "number": 2, "url": ""}},
        {"name": "Scripture Reading", "type": "scripture", "value": {"translation": 16, "book": "Genesis", "chapter": 1, "verse_start": 1, "verse_end": 1}},
    ]
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


def test_patch_valid_list_updates(tmp_path, monkeypatch):
    dbpath = create_sample_entries(monkeypatch)
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
    # ensure updated value is present
    found = False
    for item in data[0]["data"]:
        if isinstance(item, dict) and item.get("name") == "Opening Prayer":
            assert isinstance(item.get("value"), dict)
            assert item.get("value")["number"] == 35
            found = True
    assert found


def test_patch_key_mismatch_rejected(tmp_path, monkeypatch):
    dbpath = create_sample_entries(monkeypatch)
    from app.main import app
    client = TestClient(app)
    # use a dict whose keys don't match any stored nested `value` dict
    payload = [{"title": "Non existing", "value": "X"}]
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code == 400


def test_patch_non_list_rejected(tmp_path, monkeypatch):
    dbpath = create_sample_entries(monkeypatch)
    from app.main import app
    client = TestClient(app)
    payload = "not-a-list"
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code in (400, 422)


def test_patch_atomic_across_entries(tmp_path, monkeypatch):
    # create two entries with same date and ensure update applies to both or none
    dbpath = create_sample_entries(monkeypatch, create_multiple=True)
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
            if isinstance(item, dict) and item.get("name") == "Opening Prayer":
                assert isinstance(item.get("value"), dict)
                assert item.get("value")["number"] == 99
                found = True
        assert found
