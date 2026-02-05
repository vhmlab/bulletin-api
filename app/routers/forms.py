from fastapi import APIRouter, Depends
import sqlite3
from ..database import get_db
from ..auth import get_current_user
from ..crud import get_service_entries_by_date

forms_router = APIRouter(prefix="/forms", tags=["Forms"])


@forms_router.get("/by-date/{date:path}")
def forms_by_date(
    date: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Return which service forms are available for a given date (format: yyyy-ww)."""
    ss = get_service_entries_by_date(db, "sabbath_school", date)
    ws = get_service_entries_by_date(db, "worship_service", date)
    ys = get_service_entries_by_date(db, "youth_service", date)
    wed = get_service_entries_by_date(db, "wednesday_service", date)

    return {
        "sabbath_school": bool(ss),
        "worship_service": bool(ws),
        "youth_service": bool(ys),
        "wednesday_service": bool(wed),
    }
