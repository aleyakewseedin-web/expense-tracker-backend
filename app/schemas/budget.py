from pydantic import BaseModel, field_validator, model_validator
from uuid import UUID
from decimal import Decimal
from datetime import datetime

class BudgetCreate(BaseModel):
    category_id: UUID
    month: int
    year: int
    budget_amount_usd: Decimal

    @field_validator("month")
    @classmethod
    def validate_month(cls, v):
        if v < 1 or v > 12:
            raise ValueError("Month must be between 1 and 12")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < current_year:
            raise ValueError(f"Cannot set a budget for a past year")
        if v > current_year + 5:
            raise ValueError(f"Year cannot be more than 5 years in the future")
        return v

    @field_validator("budget_amount_usd")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Budget amount must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_not_past_month(self):
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        if self.year == current_year and self.month < current_month:
            raise ValueError(
                f"Cannot set a budget for a past month. "
                f"Current month is {current_month}/{current_year}"
            )
        return self


class BudgetResponse(BaseModel):
    id: UUID
    category_id: UUID
    month: int
    year: int
    budget_amount_usd: Decimal

    class Config:
        from_attributes = True

class BudgetWithSpending(BaseModel):
    id: UUID
    category: str
    budget_amount_usd: Decimal
    spent_usd: Decimal
    remaining_usd: Decimal
    over_budget: bool