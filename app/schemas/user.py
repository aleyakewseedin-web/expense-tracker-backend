from pydantic import BaseModel, EmailStr
from uuid import UUID

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

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"