from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import Optional

SUPPORTED_CURRENCIES = {
    "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK",
    "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "ISK",
    "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN",
    "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR"
}

class ExpenseCreate(BaseModel):
    category_id: UUID
    group_id: Optional[UUID] = None
    original_amount: Decimal
    currency_code: str
    expense_date: date
    description: Optional[str] = None
    payment_method: Optional[str] = None
    receipt_reference: Optional[str] = None

    @field_validator("original_amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, v):
        if v.upper() not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Invalid currency code '{v}'. Must be a valid ISO 4217 code.")
        return v.upper()

    @field_validator("expense_date")
    @classmethod
    def validate_date(cls, v):
        if v > date.today():
            raise ValueError("Expense date cannot be in the future")
        return v

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, v):
        if v is None:
            return v
        allowed = {"cash", "credit_card", "debit_card", "transfer"}
        if v not in allowed:
            raise ValueError(f"Payment method must be one of: {', '.join(allowed)}")
        return v

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
    receipt_reference: Optional[str] = None
    class Config:
        from_attributes = True

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    original_amount: Optional[Decimal] = None
    currency_code: Optional[str] = None
    expense_date: Optional[date] = None
    payment_method: Optional[str] = None
    category_id: Optional[UUID] = None

    @field_validator("original_amount")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, v):
        if v is None:
            return v
        if v.upper() not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Invalid currency code '{v}'")
        return v.upper()

    @field_validator("expense_date")
    @classmethod
    def validate_date(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Expense date cannot be in the future")
        return v