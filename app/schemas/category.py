from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class CategoryCreate(BaseModel):
    name: str

class CategoryResponse(BaseModel):
    id: UUID
    name: str
    is_system: bool
    user_id: Optional[UUID] = None

    class Config:
        from_attributes = True