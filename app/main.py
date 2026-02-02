# Wrapper to allow running uvicorn with `app.main:app`
# Re-exports the FastAPI `app` defined in project root `main.py`.
from main import app
