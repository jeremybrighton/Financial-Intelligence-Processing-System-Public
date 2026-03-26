from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from backend.models.common import DocumentModel, InstitutionStatus, InstitutionType

class InstitutionCreateRequest(BaseModel):
    institution_code: str = Field(..., min_length=3, max_length=20, pattern=r"^[A-Z0-9\-]+$")
    name: str = Field(..., min_length=2, max_length=200)
    institution_type: InstitutionType; licence_number: str
    country: str = Field("MU", min_length=2, max_length=2)
    contact_email: EmailStr; contact_name: str
    contact_phone: Optional[str] = None; address: Optional[str] = None; notes: Optional[str] = None

class InstitutionUpdateRequest(BaseModel):
    name: Optional[str] = None; institution_type: Optional[InstitutionType] = None
    contact_email: Optional[EmailStr] = None; contact_name: Optional[str] = None
    contact_phone: Optional[str] = None; address: Optional[str] = None
    status: Optional[InstitutionStatus] = None; notes: Optional[str] = None

class ApiKeyCreateRequest(BaseModel):
    label: str = Field(..., min_length=2, max_length=100); expires_at: Optional[datetime] = None
