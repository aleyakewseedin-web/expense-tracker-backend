from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from app.database import get_db
from app.models.budget import Budget
from app.models.expense import Expense
from app.models.category import Category
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetWithSpending
from app.dependencies import get_current_user
from typing import List
from uuid import UUID
from decimal import Decimal
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("", response_model=BudgetResponse, status_code=201)
@limiter.limit("30/minute")
def create_budget(
    request: Request,
    budget_data: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(
        Category.id == budget_data.category_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    existing = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.category_id == budget_data.category_id,
        Budget.month == budget_data.month,
        Budget.year == budget_data.year
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Budget already exists for this category and month"
        )

    budget = Budget(
        user_id=current_user.id,
        category_id=budget_data.category_id,
        month=budget_data.month,
        year=budget_data.year,
        budget_amount_usd=budget_data.budget_amount_usd
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("", response_model=List[BudgetWithSpending])
def get_budgets(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
        if year < 2000:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM (e.g. 2026-05)"
        )

    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == mon,
        Budget.year == year
    ).all()

    result = []
    for budget in budgets:
        spent = db.query(func.sum(Expense.amount_usd)).filter(
            Expense.user_id == current_user.id,
            Expense.category_id == budget.category_id,
            extract("month", Expense.expense_date) == mon,
            extract("year", Expense.expense_date) == year
        ).scalar() or Decimal("0")

        spent = Decimal(str(spent))
        remaining = budget.budget_amount_usd - spent
        over_budget = spent > budget.budget_amount_usd

        category = db.query(Category).filter(
            Category.id == budget.category_id
        ).first()

        result.append(BudgetWithSpending(
            id=budget.id,
            category=category.name,
            budget_amount_usd=budget.budget_amount_usd,
            spent_usd=spent,
            remaining_usd=remaining,
            over_budget=over_budget
        ))

    return result


@router.put("/{budget_id}", response_model=BudgetResponse)
@limiter.limit("30/minute")
def update_budget(
    request: Request,
    budget_id: UUID,
    budget_amount_usd: Decimal,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    budget.budget_amount_usd = budget_amount_usd
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
@limiter.limit("30/minute")
def delete_budget(
    request: Request,
    budget_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(budget)
    db.commit()
    return {"message": "Budget deleted"}