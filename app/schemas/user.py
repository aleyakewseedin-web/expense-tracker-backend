from pydantic import BaseModel, EmailStr,field_validator
from uuid import UUID
from typing import Optional

    

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    base_currency: str = "USD"
@field_validator("password")
@classmethod
def validate_password(cls, v):
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v):
        raise ValueError("Password must contain at least one symbol")
    return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    base_currency: str
    is_2fa_enabled: bool = False

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None