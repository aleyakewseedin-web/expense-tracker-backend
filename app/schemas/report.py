from pydantic import BaseModel
from typing import Optional

class MonthlyReportResponse(BaseModel):
    month: str
    structured_summary: dict
    ai_narrative: Optional[str] = None
    generated_at: Optional[str] = None
    cached: bool = False