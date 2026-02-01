from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas import ServiceCreate, ServiceUpdate, ServiceResponse, FieldUpdate
from crud import (
    create_service_entry,
    get_service_entry,
    get_service_entries,
    get_service_entries_by_date,
    update_service_entry,
    delete_service_entry,
    update_service_field_by_date,
)
from auth import get_current_user
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
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Create a new service entry"""
        db_entry = create_service_entry(db, service_type, service)
        return {"id": db_entry.id, "date": db_entry.date, "data": json.loads(db_entry.data) if db_entry.data else []}
    
    @router.get("/", response_model=List[ServiceResponse])
    def read_entries(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Get all service entries"""
        entries = get_service_entries(db, service_type, skip=skip, limit=limit)
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in entries]
    
    @router.get("/{entry_id}", response_model=ServiceResponse)
    def read_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Get a specific service entry by ID"""
        entry = get_service_entry(db, service_type, entry_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry with id {entry_id} not found"
            )
        return {"id": entry.id, "date": entry.date, "data": json.loads(entry.data) if entry.data else []}
    
    @router.get("/by-date/{date}", response_model=List[ServiceResponse])
    def read_entries_by_date(
        date: str,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Get service entries by date (format: yy/ww)"""
        entries = get_service_entries_by_date(db, service_type, date)
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in entries]

    @router.patch("/by-date/{date}/field", response_model=List[ServiceResponse])
    def update_field_by_date(
        date: str,
        field_update: FieldUpdate,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Update a specific JSON field inside the `data` column for entries matching `date`."""
        updated = update_service_field_by_date(db, service_type, date, field_update.field, field_update.value)
        return [{"id": e.id, "date": e.date, "data": json.loads(e.data) if e.data else []} for e in updated]
    
    @router.put("/{entry_id}", response_model=ServiceResponse)
    def update_entry(
        entry_id: int,
        service: ServiceUpdate,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Update a service entry"""
        entry = update_service_entry(db, service_type, entry_id, service)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry with id {entry_id} not found"
            )
        return {"id": entry.id, "date": entry.date, "data": json.loads(entry.data) if entry.data else []}
    
    @router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: str = Depends(get_current_user)
    ):
        """Delete a service entry"""
        success = delete_service_entry(db, service_type, entry_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry with id {entry_id} not found"
            )
        return None
    
    return router


# Create routers for each service type
sabbath_school_router = create_service_router("sabbath_school", "Sabbath School")
worship_service_router = create_service_router("worship_service", "Worship Service")
youth_service_router = create_service_router("youth_service", "Youth Service")
wednesday_service_router = create_service_router("wednesday_service", "Wednesday Service")
