import sys
from pathlib import Path
import json
import sqlite3
import importlib
import pytest

# Ensure repository root is on sys.path so `import app` works regardless of cwd
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


@pytest.fixture(scope="session")
def example_data():
    """Load and return the JSON data from tests/example.json."""
    path = repo_root / "tests" / "example.json"
    return json.loads(path.read_text())


@pytest.fixture
def per_test_db(request, tmp_path):
    """Provide a sqlite DB file placed next to the test file and ensure the
    application's `app.database.DEFAULT_DB` points to it. Also create the
    required tables and clear any existing rows so tests are idempotent.

    Returns the Path to the DB file.
    """
    test_file = Path(request.node.fspath).resolve()
    db_file = test_file.with_suffix(".db")

    # Ensure the app.database module uses this DB file
    dbmod = importlib.import_module("app.database")
    dbmod.DEFAULT_DB = db_file

    # Create/clear tables
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    for t in ["sabbath_school", "worship_service", "youth_service", "wednesday_service"]:
        conn.execute(f"CREATE TABLE IF NOT EXISTS {t} (id INTEGER PRIMARY KEY, date TEXT, data TEXT)")
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()

    return db_file
