import sys
from pathlib import Path
import json
import sqlite3
import importlib
import pytest
import time
import json as _json

# Ensure repository root is on sys.path so `import app` works regardless of cwd
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def pytest_sessionstart(session):
    """Truncate any existing per-test .log files before the test run begins.

    We truncate at session start (not per-test) because multiple test cases
    append to the same test-level log file; truncating per-test would erase
    earlier test logs from the same file.
    """
    tests_dir = repo_root / "tests"
    if tests_dir.exists():
        # Truncate .log files
        for p in tests_dir.rglob("*.log"):
            try:
                p.write_text("", encoding="utf-8")
            except Exception:
                # best-effort: if we can't truncate, continue
                pass

        # Remove old .db files so each run starts clean. We don't fail if
        # removal isn't possible (permissions, open handles, etc.).
        for p in tests_dir.rglob("*.db"):
            try:
                p.unlink()
            except Exception:
                # best-effort: skip files we can't remove
                pass


@pytest.fixture(scope="session")
def example_data():
    """Load and return the JSON data from tests/example.json."""
    path = repo_root / "tests" / "example.json"
    return json.loads(path.read_text())


@pytest.fixture
def per_test_db(request):
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


@pytest.fixture(autouse=True)
def per_test_logger(request, monkeypatch):
    """Create a per-test .log file next to the test file and monkeypatch
    sqlite3.connect and TestClient to record DB and HTTP activity.

    Yields the Path to the log file.
    """
    test_file = Path(request.node.fspath).resolve()
    log_file = test_file.with_suffix(".log")
    lf = open(log_file, "a", encoding="utf-8")
    start = time.time()
    lf.write(f"=== TEST {request.node.name} START {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    lf.flush()

    # Wrap sqlite3.connect so connections log SQL operations
    orig_connect = sqlite3.connect

    def connect_wrapped(*a, **kw):
        real_conn = orig_connect(*a, **kw)

        def _log(msg):
            lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
            lf.flush()

        class ConnProxy:
            def __init__(self, inner):
                object.__setattr__(self, "_inner", inner)

            def execute(self, sql, *params, **exec_kw):
                _log(f"EXECUTE: {sql!r} params={params}")
                return self._inner.execute(sql, *params, **exec_kw)

            def executemany(self, sql, seq_of_params, **exec_kw):
                _log(f"EXECUTEMANY: {sql!r} params={seq_of_params}")
                return self._inner.executemany(sql, seq_of_params, **exec_kw)

            def commit(self):
                _log("COMMIT")
                return self._inner.commit()

            def close(self):
                _log("CLOSE")
                return self._inner.close()

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __setattr__(self, name, value):
                if name == "_inner":
                    object.__setattr__(self, name, value)
                else:
                    setattr(self._inner, name, value)

        return ConnProxy(real_conn)

    monkeypatch.setattr(sqlite3, "connect", connect_wrapped)

    # Wrap TestClient to log requests/responses (if available)
    try:
        import fastapi.testclient as _tc
        OrigClient = _tc.TestClient

        class LoggedTestClient(OrigClient):
            def request(self, method, url, *args, **kwargs):
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP REQUEST: {method} {url}\n")
                if "json" in kwargs:
                    try:
                        lf.write(f"  JSON: {_json.dumps(kwargs['json'], ensure_ascii=False)}\n")
                    except Exception:
                        lf.write("  JSON: <unserializable>\n")
                resp = super().request(method, url, *args, **kwargs)
                body = resp.text or ""
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP RESPONSE: {resp.status_code} {body}\n")
                lf.flush()
                return resp

        monkeypatch.setattr(_tc, "TestClient", LoggedTestClient)
    except Exception:
        # If TestClient isn't available at fixture time, skip wrapping it.
        pass

    # Also wrap requests.Session.request so pre-instantiated TestClient
    # instances (created at module import time) still produce log entries.
    try:
        import requests
        orig_session_request = requests.sessions.Session.request

        def session_request_wrapped(self, method, url, *args, **kwargs):
            lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP SESSION REQUEST: {method} {url}\n")
            if "json" in kwargs:
                try:
                    lf.write(f"  JSON: {_json.dumps(kwargs['json'], ensure_ascii=False)}\n")
                except Exception:
                    lf.write("  JSON: <unserializable>\n")
            resp = orig_session_request(self, method, url, *args, **kwargs)
            try:
                body = resp.text or ""
            except Exception:
                body = "<no body>"
            lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP SESSION RESPONSE: {resp.status_code} {body}\n")
            lf.flush()
            return resp

        monkeypatch.setattr(requests.sessions.Session, "request", session_request_wrapped, raising=True)
    except Exception:
        pass

    # Also wrap httpx clients if tests use them (AsyncClient or Client)
    try:
        import httpx

        if hasattr(httpx, "Client"):
            orig_httpx_client_request = httpx.Client.request

            def httpx_client_request_wrapped(self, method, url, *args, **kwargs):
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTPX CLIENT REQUEST: {method} {url}\n")
                if "json" in kwargs:
                    try:
                        lf.write(f"  JSON: {_json.dumps(kwargs['json'], ensure_ascii=False)}\n")
                    except Exception:
                        lf.write("  JSON: <unserializable>\n")
                resp = orig_httpx_client_request(self, method, url, *args, **kwargs)
                try:
                    body = resp.text or ""
                except Exception:
                    body = "<no body>"
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTPX CLIENT RESPONSE: {getattr(resp, 'status_code', getattr(resp, 'status', '<no-status>'))} {body}\n")
                lf.flush()
                return resp

            monkeypatch.setattr(httpx.Client, "request", httpx_client_request_wrapped, raising=False)

        if hasattr(httpx, "AsyncClient"):
            orig_httpx_async_request = httpx.AsyncClient.request

            async def httpx_async_request_wrapped(self, method, url, *args, **kwargs):
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTPX ASYNC REQUEST: {method} {url}\n")
                if "json" in kwargs:
                    try:
                        lf.write(f"  JSON: {_json.dumps(kwargs['json'], ensure_ascii=False)}\n")
                    except Exception:
                        lf.write("  JSON: <unserializable>\n")
                resp = await orig_httpx_async_request(self, method, url, *args, **kwargs)
                try:
                    body = resp.text or ""
                except Exception:
                    body = "<no body>"
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTPX ASYNC RESPONSE: {getattr(resp, 'status_code', getattr(resp, 'status', '<no-status>'))} {body}\n")
                lf.flush()
                return resp

            monkeypatch.setattr(httpx.AsyncClient, "request", httpx_async_request_wrapped, raising=False)
    except Exception:
        pass

    yield log_file

    lf.write(f"=== TEST {request.node.name} END {time.strftime('%Y-%m-%d %H:%M:%S')} duration={(time.time()-start):.3f}s ===\n\n")
    lf.close()
