import json
import sqlite3
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

def create_sample_entries(per_test_db, create_multiple: bool = False, example_data=None):
    # Use the DB provided by the `per_test_db` fixture. The fixture already
    # creates and clears the necessary tables, so this helper only inserts
    # the sample data needed by the tests.
    db_file = per_test_db

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

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


def test_patch_valid_list_updates(per_test_db, example_data):
    create_sample_entries(per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    # update using list of dicts where keys match existing items
    # payload contains only the nested `value` dicts to apply
    # Build payload from the canonical example data to avoid duplication.
    # Use the hymn value updated to have number=35 and the scripture value
    # as provided by `example_data`.
    hymn_val = dict(example_data[0].get("value", {}))
    hymn_val["number"] = 35
    # include song and scripture values so the payload length matches stored list
    song_val = dict(example_data[1].get("value", {})) if len(example_data) > 1 else {}
    # find a scripture entry in example_data (fallback to index 2)
    scripture_val = None
    for item in example_data:
        if item.get("type") == "scripture":
            scripture_val = dict(item.get("value", {}))
            break
    if scripture_val is None and len(example_data) > 2:
        scripture_val = dict(example_data[2].get("value", {}))
    # place song_val before hymn_val so the final replacement for the
    # shared key-set lands on the hymn entry (implementation detail).
    payload = [song_val, hymn_val, scripture_val]
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

    # verify DB stored values match the payload we sent
    conn = sqlite3.connect(str(per_test_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id, date, data FROM worship_service WHERE date = ?", ("2026-04",)).fetchone()
    assert row is not None
    stored = json.loads(row["data"]) if row["data"] else []

    # Require exact 1:1 ordered match between stored nested `value` objects and payload
    assert isinstance(stored, list)
    assert len(stored) == len(payload), "stored list length does not match payload length"
    for idx, incoming in enumerate(payload):
        assert isinstance(stored[idx], dict) and isinstance(stored[idx].get("value"), dict)
        assert stored[idx].get("value") == incoming, f"stored item at index {idx} {stored[idx].get('value')} does not equal payload {incoming}"
    conn.close()


def test_patch_key_mismatch_rejected(per_test_db, example_data):
    create_sample_entries(per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    # use a dict whose keys don't match any stored nested `value` dict
    # Construct payload from example_data but with non-matching keys
    sample_title = None
    if example_data and isinstance(example_data, list) and len(example_data) > 0:
        # try to derive a human-readable title from the first entry
        first = example_data[0]
        name = first.get("name") or {}
        # pick an English hymn title if available
        sample_title = (
            name.get("Hymn", {}).get("en")
            if isinstance(name, dict) else None
        )
    if not sample_title:
        sample_title = "Non existing"
    payload = [{"title": sample_title, "value": "X"}]
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code == 400


def test_patch_non_list_rejected(per_test_db, example_data):
    create_sample_entries(per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    payload = "not-a-list"
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code in (400, 422)


def test_patch_wrong_length_rejected(per_test_db, example_data):
    # sending fewer values than stored should be rejected
    create_sample_entries(per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    hymn_val = dict(example_data[0].get("value", {}))
    hymn_val["number"] = 55
    # include only hymn and scripture (missing the song) to trigger length mismatch
    scripture_val = None
    for item in example_data:
        if item.get("type") == "scripture":
            scripture_val = dict(item.get("value", {}))
            break
    if scripture_val is None and len(example_data) > 2:
        scripture_val = dict(example_data[2].get("value", {}))
    payload = [hymn_val, scripture_val]
    r = client.patch("/worship_service/by-date/2026-04/values", json=payload)
    assert r.status_code == 400


def test_patch_atomic_across_entries(per_test_db, example_data):
    # create two entries with same date and ensure update applies to both or none
    create_sample_entries(create_multiple=True, per_test_db=per_test_db, example_data=example_data)
    from app.main import app
    client = TestClient(app)
    # Build payload from example_data (update hymn number to 99)
    hymn_val = dict(example_data[0].get("value", {}))
    hymn_val["number"] = 99
    # include song and scripture values so the payload length matches stored list
    song_val = dict(example_data[1].get("value", {})) if len(example_data) > 1 else {}
    scripture_val = None
    for item in example_data:
        if item.get("type") == "scripture":
            scripture_val = dict(item.get("value", {}))
            break
    if scripture_val is None and len(example_data) > 2:
        scripture_val = dict(example_data[2].get("value", {}))
    # place song_val before hymn_val so hymn ends up with the intended value
    payload = [song_val, hymn_val, scripture_val]
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
