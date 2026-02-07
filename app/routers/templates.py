from fastapi import APIRouter, HTTPException, status
from pathlib import Path
import json

templates_router = APIRouter(prefix="/template", tags=["Templates"])


@templates_router.get("/{element}")
def get_template(element: str):
    """Return the JSON template file named `{element}.json` from the `app/templates` directory."""
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    file_path = templates_dir / f"{element}.json"
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Template {element}.json not found")
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Template {element}.json contains invalid JSON")
    return data
