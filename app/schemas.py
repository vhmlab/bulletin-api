from pydantic import BaseModel
from typing import Optional, Any, List


class ServiceBase(BaseModel):
    date: str  # Format: yyyy-ww (e.g., "2026-04" for year 2026, week 4)
    data: List[Any]  # JSON list; will be stored as text in DB


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    date: Optional[str] = None  # Format: yyyy-ww (e.g., "2026-04")
    data: Optional[List[Any]] = None


class ServiceResponse(ServiceBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class FieldUpdate(BaseModel):
    field: str  # dot-separated path to the JSON field to update
    value: Any
