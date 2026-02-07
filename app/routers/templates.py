from fastapi import APIRouter, HTTPException, status, Depends
from pathlib import Path
import json
from sqlite3 import Connection

from ..database import get_db

templates_router = APIRouter(prefix="/template", tags=["Templates"])


@templates_router.get("/{element}")
def get_template(element: str, db: Connection = Depends(get_db)):
    """Return the template named `element` from the `templates` DB table.

    The `data` column is stored as JSON text and will be parsed before
    returning. If the template is not present or contains invalid JSON,
    an appropriate HTTP error is raised.
    """
    cur = db.execute("SELECT data FROM templates WHERE name = ?", (element,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template {element} not found")
    raw = row[0]
    try:
        data = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Template {element} contains invalid JSON")
    return data
