from sqlalchemy.orm import Session
from typing import List, Optional, Type, Any
import json

from database import SabbathSchool, WorshipService, YouthService, WednesdayService
from schemas import ServiceCreate, ServiceUpdate


def get_service_model(service_type: str) -> Type:
    """Get the appropriate model class based on service type"""
    models = {
        "sabbath_school": SabbathSchool,
        "worship_service": WorshipService,
        "youth_service": YouthService,
        "wednesday_service": WednesdayService,
    }
    return models.get(service_type)


def create_service_entry(
    db: Session, service_type: str, service_data: ServiceCreate
):
    """Create a new service entry"""
    model = get_service_model(service_type)
    if not model:
        return None
    
    # store the JSON list as text
    db_entry = model(date=service_data.date, data=json.dumps(service_data.data))
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def get_service_entry(db: Session, service_type: str, entry_id: int):
    """Get a service entry by ID"""
    model = get_service_model(service_type)
    if not model:
        return None
    
    return db.query(model).filter(model.id == entry_id).first()


def get_service_entries(
    db: Session, service_type: str, skip: int = 0, limit: int = 100
):
    """Get all service entries with pagination"""
    model = get_service_model(service_type)
    if not model:
        return []
    
    return db.query(model).offset(skip).limit(limit).all()


def get_service_entries_by_date(
    db: Session, service_type: str, date: str
):
    """Get service entries by date (format: yy/ww)"""
    model = get_service_model(service_type)
    if not model:
        return []
    
    return db.query(model).filter(model.date == date).all()


def update_service_entry(
    db: Session, service_type: str, entry_id: int, service_data: ServiceUpdate
):
    """Update a service entry"""
    model = get_service_model(service_type)
    if not model:
        return None
    
    db_entry = db.query(model).filter(model.id == entry_id).first()
    if not db_entry:
        return None
    
    update_data = service_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "data":
            # data comes as a JSON list; store as text
            setattr(db_entry, "data", json.dumps(value))
        else:
            setattr(db_entry, key, value)
    
    db.commit()
    db.refresh(db_entry)
    return db_entry


def delete_service_entry(db: Session, service_type: str, entry_id: int):
    """Delete a service entry"""
    model = get_service_model(service_type)
    if not model:
        return False
    
    db_entry = db.query(model).filter(model.id == entry_id).first()
    if not db_entry:
        return False
    
    db.delete(db_entry)
    db.commit()
    return True


def update_service_field_by_date(
    db: Session, service_type: str, date: str, field_path: str, value: Any
):
    """Update a JSON field inside the `data` column for entries matching `date`.

    `field_path` is a dot-separated path into the JSON object (e.g. "meta.author.name").
    Returns the list of updated entries.
    """
    model = get_service_model(service_type)
    if not model:
        return []

    entries = db.query(model).filter(model.date == date).all()
    if not entries:
        return []

    def set_nested(d: dict, path: list, val: Any):
        cur = d
        for p in path[:-1]:
            if p not in cur or not isinstance(cur[p], dict):
                cur[p] = {}
            cur = cur[p]
        cur[path[-1]] = val

    path_parts = [p for p in field_path.split('.') if p]
    updated = []
    for entry in entries:
        try:
            data_obj = json.loads(entry.data) if entry.data else {}
        except Exception:
            data_obj = {}

        set_nested(data_obj, path_parts, value)
        entry.data = json.dumps(data_obj)
        db.add(entry)
        updated.append(entry)

    db.commit()
    for e in updated:
        db.refresh(e)

    return updated
