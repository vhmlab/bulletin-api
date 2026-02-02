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
        return {"updated": [], "date_found": False, "field_found": False}

    path_parts = [p for p in field_path.split('.') if p]

    # If the field_path is a single non-numeric token, treat it as the name
    # of an element inside the top-level list (`data`) and set its `value`.
    is_name_lookup = len(path_parts) == 1 and not path_parts[0].isdigit()

    def exists_nested(obj: Any, parts: list) -> bool:
        cur = obj
        for p in parts:
            if p.isdigit():
                if not isinstance(cur, list):
                    return False
                idx = int(p)
                if idx < 0 or idx >= len(cur):
                    return False
                cur = cur[idx]
            else:
                if not isinstance(cur, dict):
                    return False
                if p not in cur:
                    return False
                cur = cur[p]
        return True

    def set_nested_if_exists(d: Any, parts: list, val: Any):
        # Only set if the full path exists; traverse and set the leaf
        cur = d
        for i, p in enumerate(parts):
            last = (i == len(parts) - 1)
            if p.isdigit():
                idx = int(p)
                if not isinstance(cur, list) or idx < 0 or idx >= len(cur):
                    return False
                if last:
                    cur[idx] = val
                    return True
                cur = cur[idx]
            else:
                if not isinstance(cur, dict) or p not in cur:
                    return False
                if last:
                    cur[p] = val
                    return True
                cur = cur[p]
        return False

    field_found_any = False
    updated = []
    for entry in entries:
        try:
            data_obj = json.loads(entry.data) if entry.data else []
        except Exception:
            data_obj = []

        # Name-based lookup: search list items for a dict with matching "name" and set its "value"
        if is_name_lookup:
            found_in_entry = False
            if isinstance(data_obj, list):
                for item in data_obj:
                    if isinstance(item, dict) and item.get("name") == path_parts[0]:
                        item["value"] = value
                        found_in_entry = True
            if found_in_entry:
                field_found_any = True
                entry.data = json.dumps(data_obj)
                db.add(entry)
                updated.append(entry)
            continue

        # Fallback: path-based nested update
        if exists_nested(data_obj, path_parts):
            field_found_any = True
            ok = set_nested_if_exists(data_obj, path_parts, value)
            if ok:
                entry.data = json.dumps(data_obj)
                db.add(entry)
                updated.append(entry)

    if not field_found_any:
        # date exists but field not found in any entry
        return {"updated": [], "date_found": True, "field_found": False}

    db.commit()
    for e in updated:
        db.refresh(e)

    return {"updated": updated, "date_found": True, "field_found": True}


def update_service_entries_by_date(
    db: Session, service_type: str, date: str, service_data: ServiceUpdate
):
    """Update all entries matching `date` with fields from `service_data`.

    Returns list of updated entries.
    """
    model = get_service_model(service_type)
    if not model:
        return []

    entries = db.query(model).filter(model.date == date).all()
    if not entries:
        return []

    update_data = service_data.model_dump(exclude_unset=True)
    updated = []
    for entry in entries:
        for key, value in update_data.items():
            if key == "data":
                entry.data = json.dumps(value)
            else:
                setattr(entry, key, value)
        db.add(entry)
        updated.append(entry)

    db.commit()
    for e in updated:
        db.refresh(e)

    return updated


def delete_service_entries_by_date(db: Session, service_type: str, date: str):
    """Delete all entries matching `date`. Returns number of deleted rows."""
    model = get_service_model(service_type)
    if not model:
        return 0

    entries = db.query(model).filter(model.date == date).all()
    if not entries:
        return 0

    count = 0
    for entry in entries:
        db.delete(entry)
        count += 1

    db.commit()
    return count
