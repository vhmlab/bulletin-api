"""CRUD helpers using sqlite3 connections instead of SQLAlchemy.

Each function expects `db` to be a `sqlite3.Connection` (as provided by
`app.database.get_db`) and returns lightweight `Entry` objects with
attribute-style access (`id`, `date`, `data`).
"""
import json
import logging
from typing import List, Optional, Any

from .schemas import ServiceCreate, ServiceUpdate

logger = logging.getLogger(__name__)


class Entry:
    """Simple object to mimic ORM-like attribute access for rows."""

    def __init__(self, row: Optional[dict]):
        if row is None:
            self.id = None
            self.date = None
            self.data = None
        else:
            # row may be sqlite3.Row or a mapping
            self.id = row["id"]
            self.date = row["date"]
            self.data = row["data"]


def _table_for(service_type: str) -> Optional[str]:
    tables = {
        "sabbath_school": "sabbath_school",
        "worship_service": "worship_service",
        "youth_service": "youth_service",
        "wednesday_service": "wednesday_service",
    }
    return tables.get(service_type)


def create_service_entry(db, service_type: str, service_data: ServiceCreate):
    table = _table_for(service_type)
    if not table:
        return None
    cur = db.execute(f"INSERT INTO {table} (date, data) VALUES (?, ?)", (service_data.date, json.dumps(service_data.data)))
    db.commit()
    rowid = cur.lastrowid
    row = db.execute(f"SELECT id, date, data FROM {table} WHERE id = ?", (rowid,)).fetchone()
    return Entry(row)


def get_service_entry(db, service_type: str, entry_id: int):
    table = _table_for(service_type)
    if not table:
        return None
    row = db.execute(f"SELECT id, date, data FROM {table} WHERE id = ?", (entry_id,)).fetchone()
    return Entry(row) if row else None


def get_service_entries(db, service_type: str, skip: int = 0, limit: int = 100) -> List[Entry]:
    table = _table_for(service_type)
    if not table:
        return []
    cursor = db.execute(f"SELECT id, date, data FROM {table} ORDER BY id LIMIT ? OFFSET ?", (limit, skip))
    return [Entry(r) for r in cursor.fetchall()]


def get_service_entries_by_date(db, service_type: str, date: str) -> List[Entry]:
    table = _table_for(service_type)
    if not table:
        return []
    cursor = db.execute(f"SELECT id, date, data FROM {table} WHERE date = ?", (date,))
    return [Entry(r) for r in cursor.fetchall()]


def update_service_entry(db, service_type: str, entry_id: int, service_data: ServiceUpdate):
    table = _table_for(service_type)
    if not table:
        return None
    row = db.execute(f"SELECT id, date, data FROM {table} WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        return None

    update_data = service_data.model_dump(exclude_unset=True)
    # build set clause
    sets = []
    params = []
    for key, value in update_data.items():
        if key == "data":
            sets.append("data = ?")
            params.append(json.dumps(value))
        else:
            sets.append(f"{key} = ?")
            params.append(value)
    if sets:
        params.append(entry_id)
        db.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?", tuple(params))
        db.commit()

    updated = db.execute(f"SELECT id, date, data FROM {table} WHERE id = ?", (entry_id,)).fetchone()
    return Entry(updated)


def delete_service_entry(db, service_type: str, entry_id: int):
    table = _table_for(service_type)
    if not table:
        return False
    row = db.execute(f"SELECT id FROM {table} WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        return False
    db.execute(f"DELETE FROM {table} WHERE id = ?", (entry_id,))
    db.commit()
    return True


def update_service_field_by_date(db, service_type: str, date: str, values_list: list):
    table = _table_for(service_type)
    if not table:
        return []

    cursor = db.execute(f"SELECT id, date, data FROM {table} WHERE date = ?", (date,))
    rows = cursor.fetchall()
    if not rows:
        return {"updated": [], "date_found": False, "field_found": False}
    # Validate that input is a list of dicts
    if not isinstance(values_list, list) or not all(isinstance(v, dict) for v in values_list):
        return {"updated": [], "date_found": True, "field_found": False}

    # First pass: ensure that for every row, each incoming dict matches at least one
    # existing dict by keys. If any row does not contain a matching-key dict for any
    # incoming dict, fail the whole operation.
    for row in rows:
        try:
            data_obj = json.loads(row["data"]) if row["data"] else []
        except Exception:
            data_obj = []

        if not isinstance(data_obj, list):
            return {"updated": [], "date_found": True, "field_found": False}

        # Require the incoming list to match the stored list length exactly.
        # If lengths differ, reject the operation for atomicity and data integrity.
        if len(values_list) != len(data_obj):
            return {"updated": [], "date_found": True, "field_found": False}

        for incoming in values_list:
            incoming_keys = set(incoming.keys())
            found = False
            for item in data_obj:
                if isinstance(item, dict) and isinstance(item.get("value"), dict) and set(item.get("value").keys()) == incoming_keys:
                    found = True
                    break
            if not found:
                return {"updated": [], "date_found": True, "field_found": False}

    # Second pass: apply updates (now that validation passed for all rows)
    updated = []
    for row in rows:
        data_obj = json.loads(row["data"]) if row["data"] else []
        # For each incoming dict, update matching item(s) in the data list by replacing the
        # nested `value` dict when its keys match the incoming dict keys.
        for incoming in values_list:
            incoming_keys = set(incoming.keys())
            for idx, item in enumerate(data_obj):
                if isinstance(item, dict) and isinstance(item.get("value"), dict) and set(item.get("value").keys()) == incoming_keys:
                    # replace the nested value dict
                    item["value"] = incoming
                    data_obj[idx] = item

        db.execute(f"UPDATE {table} SET data = ? WHERE id = ?", (json.dumps(data_obj), row["id"]))
        updated.append(Entry({"id": row["id"], "date": row["date"], "data": json.dumps(data_obj)}))

    db.commit()
    return {"updated": updated, "date_found": True, "field_found": True}


def update_service_entries_by_date(db, service_type: str, date: str, service_data: ServiceUpdate):
    table = _table_for(service_type)
    if not table:
        return []
    cursor = db.execute(f"SELECT id, date, data FROM {table} WHERE date = ?", (date,))
    rows = cursor.fetchall()
    if not rows:
        return []

    update_data = service_data.model_dump(exclude_unset=True)
    updated = []
    for row in rows:
        sets = []
        params = []
        for key, value in update_data.items():
            if key == "data":
                sets.append("data = ?")
                params.append(json.dumps(value))
            else:
                sets.append(f"{key} = ?")
                params.append(value)
        if sets:
            params.append(row["id"])
            db.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?", tuple(params))
            updated.append(Entry({"id": row["id"], "date": row["date"], "data": update_data.get("data", row["data"]) if isinstance(update_data.get("data", row["data"]), str) else json.dumps(update_data.get("data", row["data"]))}))

    db.commit()
    return updated


def delete_service_entries_by_date(db, service_type: str, date: str):
    table = _table_for(service_type)
    if not table:
        return 0
    cursor = db.execute(f"SELECT id FROM {table} WHERE date = ?", (date,))
    rows = cursor.fetchall()
    if not rows:
        return 0
    ids = [r["id"] for r in rows]
    for _id in ids:
        db.execute(f"DELETE FROM {table} WHERE id = ?", (_id,))
    db.commit()
    return len(ids)
