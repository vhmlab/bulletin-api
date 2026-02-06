import os
from dotenv import load_dotenv
from pathlib import Path

# Allow overriding the .env location via the DOTENV_PATH environment variable.
# If DOTENV_PATH is set, load that file; otherwise fall back to default behaviour
# (which searches for a .env in the current working directory).
dotenv_path = os.environ.get("DOTENV_PATH")
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

# When running under pytest, set sensible defaults so individual tests don't
# need to set `DATABASE_URL` and `DISABLE_AUTH` repeatedly. Pytest sets the
# `PYTEST_CURRENT_TEST` env var during test execution in the form:
# ``path/to/test_file.py::test_name (call)``. Use the test file path to place
# a sqlite DB next to the test file unless `DATABASE_URL` is explicitly set.
pytest_current = os.environ.get("PYTEST_CURRENT_TEST")
if pytest_current:
    # Respect an explicitly configured DATABASE_URL, otherwise derive one
    if not os.environ.get("DATABASE_URL"):
        test_file = pytest_current.split("::", 1)[0]
        try:
            test_path = Path(test_file).resolve()
        except Exception:
            test_path = Path(test_file)
        db_path = test_path.with_suffix(".db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    # Default to disabling auth during tests unless explicitly enabled
    if "DISABLE_AUTH" not in os.environ:
        os.environ["DISABLE_AUTH"] = "true"

class Settings:
    DISABLE_AUTH: bool = os.getenv("DISABLE_AUTH", "false").lower() == "true"
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./boletin.db")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
