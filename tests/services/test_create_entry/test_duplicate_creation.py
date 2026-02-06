from fastapi.testclient import TestClient


def test_duplicate_creation_all_services(per_test_db, example_data):
    """Create an entry for each service, then assert duplicate creation is rejected.

    Uses `per_test_db` to prepare a per-test sqlite DB next to the test file
    and `example_data` from `tests/example.json` provided by `conftest.py`.
    """
    from app.main import app

    client = TestClient(app)

    services = [
        "/sabbath_school/",
        "/worship_service/",
        "/youth_service/",
        "/wednesday_service/",
    ]

    payload = {"date": "2026-05", "data": example_data}

    for endpoint in services:
        resp = client.post(endpoint, json=payload)
        assert resp.status_code == 201, f"Expected 201 creating first entry at {endpoint}, got {resp.status_code}"

        # second attempt should fail with 409 Conflict
        resp2 = client.post(endpoint, json=payload)
        assert resp2.status_code == 409, f"Expected 409 on duplicate create at {endpoint}, got {resp2.status_code}"
