from pydantic import BaseModel, field_validator
from uuid import UUID
from decimal import Decimal
from typing import Optional, List

class GroupCreate(BaseModel):
    name: str
    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Group name cannot be empty")
        if len(v.strip()) < 2:
            raise ValueError("Group name must be at least 2 characters")
        if len(v.strip()) > 100:
            raise ValueError("Group name cannot exceed 100 characters")
        return v.strip()

class GroupResponse(BaseModel):
    id: UUID
    name: str
    created_by: UUID

    class Config:
        from_attributes = True

class MemberAdd(BaseModel):
    user_id: UUID

class MemberResponse(BaseModel):
    id: UUID
    name: str
    email: str

    class Config:
        from_attributes = True

class SplitInput(BaseModel):
    user_id: UUID
    percentage: Optional[Decimal] = None
    exact_amount: Optional[Decimal] = None

class GroupExpenseCreate(BaseModel):
    category_id: UUID
    original_amount: Decimal
    currency_code: str
    expense_date: str
    description: Optional[str] = None
    payment_method: Optional[str] = None
    split_type: str  # equal, percentage, exact
    splits: List[SplitInput]

    @field_validator("split_type")
    @classmethod
    def validate_split_type(cls, v):
        if v not in ["equal", "percentage", "exact"]:
            raise ValueError("split_type must be equal, percentage, or exact")
        return v

    @field_validator("original_amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("splits")
    @classmethod
    def validate_splits(cls, v, info):
        if not v:
            raise ValueError("At least one split must be provided")
        return v

class GroupExpenseResponse(BaseModel):
    id: UUID
    group_id: UUID
    original_amount: Decimal
    currency_code: str
    amount_usd: Decimal
    description: Optional[str] = None

    class Config:
        from_attributes = True

class AdminLeaveGroup(BaseModel):
    new_admin_id: UUID

class RemoveMemberRequest(BaseModel):
    new_admin_id: Optional[UUID] = None