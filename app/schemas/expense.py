from pydantic import BaseModel
from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import Optional

class ExpenseCreate(BaseModel):
    category_id: UUID
    group_id: Optional[UUID] = None
    original_amount: Decimal
    currency_code: str
    expense_date: date
    description: Optional[str] = None
    payment_method: Optional[str] = None
    receipt_reference: Optional[str] = None

class ExpenseResponse(BaseModel):
    id: UUID
    user_id: UUID
    category_id: UUID
    group_id: Optional[UUID] = None
    original_amount: Decimal
    currency_code: str
    exchange_rate: Decimal
    amount_usd: Decimal
    expense_date: date
    description: Optional[str] = None
    payment_method: Optional[str] = None

    class Config:
        from_attributes = True

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    original_amount: Optional[Decimal] = None
    currency_code: Optional[str] = None
    expense_date: Optional[date] = None
    payment_method: Optional[str] = None
    category_id: Optional[UUID] = None