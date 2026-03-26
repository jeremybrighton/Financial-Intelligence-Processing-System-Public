from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from backend.models.common import DocumentModel, UserRole

class UserDocument(DocumentModel):
    email: str; full_name: str; role: UserRole; is_active: bool = True
    last_login: Optional[datetime] = None; otp_code: Optional[str] = None
    otp_expiry: Optional[datetime] = None; otp_purpose: Optional[str] = None

class UserCreateRequest(BaseModel):
    email: EmailStr; full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128); role: UserRole = UserRole.FRC_ANALYST

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None; role: Optional[UserRole] = None; is_active: Optional[bool] = None

class LoginRequest(BaseModel):
    email: EmailStr; password: str

class PasswordChangeRequest(BaseModel):
    current_password: str; new_password: str = Field(..., min_length=8)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr; otp_code: str; new_password: str = Field(..., min_length=8)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(DocumentModel):
    email: str; full_name: str; role: UserRole; is_active: bool
    last_login: Optional[datetime] = None
