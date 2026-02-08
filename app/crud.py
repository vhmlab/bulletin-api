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

    # First pass: ensure that for every row, the incoming list length equals the
    # stored list length and that each incoming dict's keys match the keys of the
    # corresponding stored item's `value` dict (strict positional mapping).
    for row in rows:
        try:
            data_obj = json.loads(row["data"]) if row["data"] else []
        except Exception:
            data_obj = []

        if not isinstance(data_obj, list):
            return {"updated": [], "date_found": True, "field_found": False}

        # Require exact length match for atomic, position-based updates.
        if len(values_list) != len(data_obj):
            return {"updated": [], "date_found": True, "field_found": False}

        # Ensure each incoming dict matches the stored item's nested `value` keys at the same index.
        for idx, incoming in enumerate(values_list):
            if not isinstance(incoming, dict):
                return {"updated": [], "date_found": True, "field_found": False}
            item = data_obj[idx]
            if not (isinstance(item, dict) and isinstance(item.get("value"), dict)):
                return {"updated": [], "date_found": True, "field_found": False}
            incoming_keys = set(incoming.keys())
            if set(item.get("value").keys()) != incoming_keys:
                return {"updated": [], "date_found": True, "field_found": False}

    # Second pass: apply updates (matching by keys, incoming order matters).
    # We apply each incoming dict to the first stored item whose nested `value`
    # keys match; this mimics the original behavior where later incoming items
    # can overwrite earlier replacements when key-sets are identical.
    updated = []
    for row in rows:
        data_obj = json.loads(row["data"]) if row["data"] else []

        # Build a mapping from incoming positions to best-matching stored item
        # indices. We pick the unused stored item with the highest number of
        # matching key-value pairs (simple similarity score). This allows the
        # API to align incoming values with the most appropriate stored item
        # when multiple items share the same key-set.
        used = set()
        mapping = {}
        for i, incoming in enumerate(values_list):
            best_j = None
            best_score = -1
            for j, item in enumerate(data_obj):
                if j in used:
                    continue
                if not (isinstance(item, dict) and isinstance(item.get("value"), dict)):
                    continue
                if set(item.get("value").keys()) != set(incoming.keys()):
                    continue
                # compute simple score: number of equal key-value pairs
                score = 0
                # Prefer matches where a common 'select' discriminator aligns
                try:
                    if isinstance(item.get("value"), dict) and isinstance(incoming, dict):
                        if item.get("value", {}).get("select") == incoming.get("select"):
                            score += 100
                except Exception:
                    pass
                for k, v in incoming.items():
                    try:
                        if item.get("value", {}).get(k) == v:
                            score += 1
                    except Exception:
                        pass
                if score > best_score:
                    best_score = score
                    best_j = j
            if best_j is None:
                # should not happen because we validated presence earlier
                return {"updated": [], "date_found": True, "field_found": False}
            mapping[i] = best_j
            used.add(best_j)

        # Construct new ordered list where position i corresponds to incoming i,
        # using the matched stored item (with non-value fields preserved) but
        # replacing its nested `value` with the incoming dict. Also update
        # the stored item's `type` when the incoming value includes a
        # 'select' discriminator (e.g. 'song' vs 'hymn') so callers relying on
        # `type` behavior can observe the intended semantics.
        new_data = []
        for i in range(len(values_list)):
            j = mapping[i]
            item = data_obj[j]
            # copy to avoid mutating original structure unexpectedly
            if isinstance(item, dict):
                new_item = dict(item)
                new_item["value"] = values_list[i]
                # If incoming value includes a 'select' field, reflect that
                # in the stored item's `type` where appropriate.
                try:
                    if isinstance(values_list[i], dict) and "select" in values_list[i]:
                        sel = values_list[i].get("select")
                        if isinstance(sel, str) and sel:
                            new_item["type"] = sel
                except Exception:
                    pass
            else:
                new_item = {"value": values_list[i]} if isinstance(values_list[i], dict) else values_list[i]
            new_data.append(new_item)

        data_obj = new_data

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
