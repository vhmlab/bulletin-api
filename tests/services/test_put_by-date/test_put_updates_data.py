import json
import os
import sys
import sqlite3
from pathlib import Path

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def test_put_updates_data_by_date(per_test_db, example_data):
    # Use fixtures to prepare DB and example data
    db_file = per_test_db
    initial_data = example_data

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    conn.execute("DELETE FROM worship_service WHERE date = ?", ("2026-06",))
    conn.execute(
        "INSERT INTO worship_service (date, data) VALUES (?, ?)",
        ("2026-06", json.dumps(initial_data)),
    )
    conn.commit()
    conn.close()

    # Import app after environment is configured
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # New values to update (modify one field to ensure update happens)
    updated_item = initial_data[0].copy()
    updated_item["value"] = updated_item["value"].copy()
    updated_item["value"]["number"] = 99

    update_payload = {"date": "2026-06", "data": [updated_item]}

    # Perform PUT request to the endpoint that updates by date (service-specific)
    response = client.put("/worship_service/by-date/2026-06", json=update_payload)

    assert response.status_code in (200, 201)

    # Fetch the entry back to verify it was updated
    get_resp = client.get("/worship_service/by-date/2026-06")
    assert get_resp.status_code == 200
    body = get_resp.json()

    # Depending on implementation the response may wrap data; find data list
    if isinstance(body, dict) and "data" in body:
        returned = body["data"]
    else:
        returned = body

    # Ensure our updated number exists somewhere inside the returned entries' `data` lists
    found = False
    for entry in returned:
        # entry may be a dict with a `data` key or already be the data list
        data_list = entry.get("data") if isinstance(entry, dict) else entry
        if isinstance(data_list, list):
            for it in data_list:
                if (it.get("value", {}) or {}).get("number") == 99:
                    found = True
                    break
        if found:
            break

    assert found, f"Updated value not found in returned data: {returned}"
