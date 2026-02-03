from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import sqlite3

from ..database import get_db
from ..schemas import ServiceCreate, ServiceUpdate, ServiceResponse, FieldUpdate
from ..crud import (
    create_service_entry,
    get_service_entries,
    get_service_entries_by_date,
    update_service_entry,
    delete_service_entry,
    update_service_entries_by_date,
    delete_service_entries_by_date,
    update_service_field_by_date,
)
from ..auth import get_current_user
import json


def create_service_router(service_type: str, service_name: str) -> APIRouter:
    """Factory function to create routers for each service type"""
    router = APIRouter(
        prefix=f"/{service_type}",
        tags=[service_name],
    )

    @router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
    def create_entry(
        service: ServiceCreate,
        db: sqlite3.Connection = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        db_entry = create_service_entry(db, service_type, service)
        return {"id": db_entry.id, "date": db_entry.date, "data": json.loads(db_entry.data) if db_entry.data else []}

    @router.get("/", response_model=List[ServiceResponse])
    def read_entries(
        skip: int = 0,
        limit: int = 100,
        db: sqlite3.Connection = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        entries = get_service_entries(db, service_type, skip=skip, limit=limit)
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in entries]

    @router.get("/by-date/{date:path}", response_model=List[ServiceResponse])
    def read_entries_by_date(
        date: str,
        db: sqlite3.Connection = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        entries = get_service_entries_by_date(db, service_type, date)
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in entries]

    @router.patch("/by-date/{date:path}/field", response_model=List[ServiceResponse])
    def update_field_by_date(
        date: str,
        field_update: FieldUpdate,
        db: sqlite3.Connection = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        result = update_service_field_by_date(db, service_type, date, field_update.field, field_update.value)
        if result is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error updating field")
        if not isinstance(result, dict):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected result type from update: {type(result)}")
        if not result.get("date_found"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No entries found for date {date}")
        if not result.get("field_found"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Field '{field_update.field}' not found for date {date}")
        updated = result.get("updated", [])
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in updated]

    @router.put("/by-date/{date:path}", response_model=List[ServiceResponse])
    def update_entries_by_date(
        date: str,
        service: ServiceUpdate,
        db: sqlite3.Connection = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        updated = update_service_entries_by_date(db, service_type, date, service)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No entries found for date {date}"
            )
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in updated]

    @router.delete("/by-date/{date:path}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_entries_by_date(
        date: str,
        db: sqlite3.Connection = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        count = delete_service_entries_by_date(db, service_type, date)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No entries found for date {date}"
            )
        return None

    return router


# Create routers for each service type
sabbath_school_router = create_service_router("sabbath_school", "Sabbath School")
worship_service_router = create_service_router("worship_service", "Worship Service")
youth_service_router = create_service_router("youth_service", "Youth Service")
wednesday_service_router = create_service_router("wednesday_service", "Wednesday Service")
