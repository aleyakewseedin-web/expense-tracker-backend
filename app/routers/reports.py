from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from app.database import get_db
from app.models.expense import Expense
from app.models.budget import Budget
from app.models.category import Category
from app.models.report import MonthlyReport
from app.schemas.report import MonthlyReportResponse
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.services.cache import get_cached_report, set_cached_report, invalidate_report_cache
from app.services.ai_report import generate_financial_narrative

router = APIRouter(prefix="/reports", tags=["Reports"])


def build_monthly_summary(user_id: UUID, year: int, month: int, db: Session) -> dict:
    # Get all expenses for this user this month
    expenses = db.query(Expense).filter(
        Expense.user_id == user_id,
        extract("year", Expense.expense_date) == year,
        extract("month", Expense.expense_date) == month
    ).all()

    # Get previous month expenses for comparison
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year = year - 1

    prev_expenses = db.query(Expense).filter(
        Expense.user_id == user_id,
        extract("year", Expense.expense_date) == prev_year,
        extract("month", Expense.expense_date) == prev_month
    ).all()

    # Total spending
    total_spent = sum(float(e.amount_usd) for e in expenses)
    prev_total = sum(float(e.amount_usd) for e in prev_expenses)

    # Month over month change
    if prev_total > 0:
        mom_change = round(((total_spent - prev_total) / prev_total) * 100, 1)
    else:
        mom_change = 0.0

    # Group expenses by category
    category_totals = {}
    for expense in expenses:
        cat_id = str(expense.category_id)
        if cat_id not in category_totals:
            category_totals[cat_id] = Decimal("0")
        category_totals[cat_id] += expense.amount_usd

    # Get budgets for this month
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.year == year
    ).all()
    budget_map = {str(b.category_id): b.budget_amount_usd for b in budgets}

    # Build category summaries
    categories = []
    for cat_id, spent in category_totals.items():
        category = db.query(Category).filter(
            Category.id == cat_id
        ).first()
        if not category:
            continue

        budget_usd = budget_map.get(cat_id)
        over_budget = False
        over_by = Decimal("0")
        remaining = None

        if budget_usd:
            over_budget = spent > budget_usd
            over_by = max(spent - budget_usd, Decimal("0"))
            remaining = budget_usd - spent

        categories.append({
            "category_id": cat_id,
            "category_name": category.name,
            "spent_usd": float(round(spent, 2)),
            "budget_usd": float(budget_usd) if budget_usd else None,
            "remaining_usd": float(remaining) if remaining is not None else None,
            "over_budget": over_budget,
            "over_by_usd": float(over_by)
        })

    # Sort by most spent first
    categories.sort(key=lambda x: x["spent_usd"], reverse=True)

    return {
        "total_spent_usd": round(total_spent, 2),
        "previous_month_total_usd": round(prev_total, 2),
        "month_over_month_change_pct": mom_change,
        "total_expenses_count": len(expenses),
        "categories": categories
    }


@router.get("/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    user_id: UUID,
    month: str,
    db: Session = Depends(get_db)
):
    print(f"=== REPORT CALLED for user {user_id} month {month} ===")

    # Validate month format
    parts = month.split("-")
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM (e.g. 2026-05)"
        )
    try:
        year, mon = int(parts[0]), int(parts[1])
        if mon < 1 or mon > 12:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM (e.g. 2026-05)"
        )

    # Check Redis cache first
    cached = get_cached_report(str(user_id), month)
    if cached:
        return MonthlyReportResponse(
            month=month,
            structured_summary=cached["structured_summary"],
            ai_narrative=cached.get("ai_narrative"),
            generated_at=cached.get("generated_at"),
            cached=True
        )

    # No cache — compute the summary
    summary = build_monthly_summary(user_id, year, mon, db)

    # Handle empty month
    if summary["total_expenses_count"] == 0:
        return MonthlyReportResponse(
            month=month,
            structured_summary=summary,
            ai_narrative="No expenses recorded for this period.",
            generated_at=datetime.utcnow().isoformat(),
            cached=False
        )

    # Check if AI narrative already exists in DB
    existing_report = db.query(MonthlyReport).filter(
        MonthlyReport.user_id == user_id,
        MonthlyReport.month == mon,
        MonthlyReport.year == year
    ).first()

    if existing_report:
        print("=== FOUND EXISTING REPORT IN DB ===")
        ai_narrative = existing_report.ai_insight
        generated_at = existing_report.generated_at.isoformat()
    else:
        print("=== GENERATING NEW AI NARRATIVE ===")
        try:
            ai_narrative = generate_financial_narrative(summary, month)
            print(f"=== AI NARRATIVE GENERATED: {ai_narrative[:50]} ===")
        except Exception as e:
            print(f"=== AI ERROR: {str(e)} ===")
            ai_narrative = f"ERROR: {str(e)}"

        generated_at = datetime.utcnow().isoformat()

        new_report = MonthlyReport(
            user_id=user_id,
            month=mon,
            year=year,
            summary_json=summary,
            ai_insight=ai_narrative
        )
        db.add(new_report)
        db.commit()

    # Cache it
    response_data = {
        "structured_summary": summary,
        "ai_narrative": ai_narrative,
        "generated_at": generated_at
    }
    set_cached_report(str(user_id), month, response_data)

    return MonthlyReportResponse(
        month=month,
        structured_summary=summary,
        ai_narrative=ai_narrative,
        generated_at=generated_at,
        cached=False
    )

@router.delete("/monthly/regenerate")
def regenerate_report(
    user_id: UUID,
    month: str,
    db: Session = Depends(get_db)
):
    parts = month.split("-")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    year, mon = int(parts[0]), int(parts[1])

    db.query(MonthlyReport).filter(
        MonthlyReport.user_id == user_id,
        MonthlyReport.month == mon,
        MonthlyReport.year == year
    ).delete()
    db.commit()

    invalidate_report_cache(str(user_id), month)

    return {"message": "Report cleared — call GET /reports/monthly to regenerate"}