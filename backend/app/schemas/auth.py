from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("Username must be 3-50 alphanumeric characters or underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class TOTPVerify(BaseModel):
    totp_code: str
    temp_token: str

    @field_validator("totp_code")
    @classmethod
    def totp_valid(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("TOTP code must be 6 digits")
        return v


class TOTPSetupResponse(BaseModel):
    qr_code_url: str
    secret: str
    temp_token: str


class LoginResponse(BaseModel):
    requires_totp: bool
    totp_enrolled: bool = False
    temp_token: Optional[str] = None
    # Populated when TOTP is disabled — client can use this directly
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user_id: Optional[int] = None
    username: Optional[str] = None
    message: str = ""


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    totp_enrolled: bool
    is_active: bool

    model_config = {"from_attributes": True}
