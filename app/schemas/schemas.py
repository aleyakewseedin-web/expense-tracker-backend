from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class CategorySummary(BaseModel):
    category_id: str
    category_name: str
    spent_usd: Decimal
    budget_usd: Optional[Decimal] = None
    remaining_usd: Optional[Decimal] = None
    over_budget: bool = False
    over_by_usd: Decimal = Decimal("0")

class MonthlyReportResponse(BaseModel):
    month: str
    structured_summary: dict
    ai_narrative: Optional[str] = None
    generated_at: Optional[str] = None
    cached: bool = False