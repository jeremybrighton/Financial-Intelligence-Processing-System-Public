"""Institution request/response schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class InstitutionCreateRequest(BaseModel):
    institution_code: str = Field(..., min_length=3, max_length=20, pattern=r"^[A-Z0-9\-]+$")
    institution_name: str = Field(..., min_length=2, max_length=200)
    institution_type: str
    supervisory_body: str = Field(..., min_length=2, max_length=200)
    contact_email: EmailStr
    status: str = "active"


class InstitutionUpdateRequest(BaseModel):
    institution_name: Optional[str] = None
    institution_type: Optional[str] = None
    supervisory_body: Optional[str] = None
    contact_email: Optional[EmailStr] = None


class InstitutionStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(active|inactive|suspended|pending)$")


class InstitutionResponse(BaseModel):
    id: str
    institution_code: str
    institution_name: str
    institution_type: str
    supervisory_body: str
    contact_email: str
    status: str
    is_active: bool
    api_key_suffix: Optional[str] = None  # last 6 chars only — never the full key
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    """Returned only once when an API key is generated."""
    api_key: str              # raw key — shown once, never stored in plain form
    api_key_suffix: str
    message: str = "Store this key securely. It will not be shown again."
