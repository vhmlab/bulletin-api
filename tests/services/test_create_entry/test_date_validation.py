import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path so `import app` works when pytest runs
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def test_create_invalid_date_format(per_test_db, example_data):
    from app.main import app

    client = TestClient(app)

    # invalid formats
    for bad in ["2026-4", "26-04", "2026-00", "2026-54", "abcd-ef", "string"]:
        resp = client.post("/sabbath_school/", json={"date": bad})
        assert resp.status_code == 400
        assert "Invalid date format" in resp.json().get("detail", "")


def test_create_duplicate_date(per_test_db, example_data):
    from app.main import app

    client = TestClient(app)

    valid = {"date": "2026-04"}
    resp = client.post("/sabbath_school/", json=valid)
    assert resp.status_code == 201

    # creating the same date again should return 409 Conflict
    resp2 = client.post("/sabbath_school/", json=valid)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json().get("detail", "")
