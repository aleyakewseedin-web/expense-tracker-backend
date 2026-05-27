from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    base_currency: str = "USD"

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