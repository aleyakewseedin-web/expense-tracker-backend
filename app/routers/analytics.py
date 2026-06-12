from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from app.database import get_db
from app.models.expense import Expense
from app.models.user import User
from app.dependencies import get_current_user
from app.services.cache import get_redis_client
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/trend")
def get_spending_trend(
    months: int = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="months must be between 1 and 24")

    # Check Redis cache
    redis = get_redis_client()
    cache_key = f"trend:{current_user.id}:{months}"
    if redis:
        cached = redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return data

    # Build list of last N months
    today = date.today()
    month_list = []
    for i in range(months - 1, -1, -1):
        d = today - relativedelta(months=i)
        month_list.append((d.year, d.month))

    # Query total spending per month
    results = db.query(
        extract("year", Expense.expense_date).label("year"),
        extract("month", Expense.expense_date).label("month"),
        func.sum(Expense.amount_usd).label("total_usd")
    ).filter(
        Expense.user_id == current_user.id
    ).group_by(
        extract("year", Expense.expense_date),
        extract("month", Expense.expense_date)
    ).all()

    # Map results to dict
    spending_map = {}
    for r in results:
        key = (int(r.year), int(r.month))
        spending_map[key] = round(float(r.total_usd), 2)

    # Build response
    trend = []
    for i, (year, month) in enumerate(month_list):
        total = spending_map.get((year, month), 0.0)
        month_str = f"{year}-{str(month).zfill(2)}"
        if i == 0:
            change_pct = None
        else:
            prev_year, prev_month = month_list[i - 1]
            prev_total = spending_map.get((prev_year, prev_month), 0.0)
            if prev_total == 0:
                change_pct = None
            else:
                change_pct = round(((total - prev_total) / prev_total) * 100, 1)

        trend.append({
            "month": month_str,
            "total_usd": total,
            "change_pct": change_pct
        })

    response = {"months": trend, "cached": False}

    # Store in Redis
    if redis:
        redis.setex(cache_key, 3600, json.dumps(response))

    return response