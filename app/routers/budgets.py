from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from app.database import get_db
from app.models.budget import Budget
from app.models.expense import Expense
from app.models.category import Category
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetWithSpending
from typing import List
from uuid import UUID
from decimal import Decimal

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post("", response_model=BudgetResponse, status_code=201)
def create_budget(
    user_id: UUID,
    budget_data: BudgetCreate,
    db: Session = Depends(get_db)
):
    # Check category exists
    category = db.query(Category).filter(
        Category.id == budget_data.category_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if budget already exists for this category+month+year
    existing = db.query(Budget).filter(
        Budget.user_id == user_id,
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
        user_id=user_id,
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
    user_id: UUID,
    month: str,
    db: Session = Depends(get_db)
):
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
        if year < 2000:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid month format. Use YYYY-MM (e.g. 2026-05)"
        )


    # Parse month string e.g. "2026-05"
    year, mon = month.split("-")
    year, mon = int(year), int(mon)

    # Get all budgets for this user and month
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == mon,
        Budget.year == year
    ).all()

    result = []
    for budget in budgets:
        # Sum all expenses for this category this month
        spent = db.query(func.sum(Expense.amount_usd)).filter(
            Expense.user_id == user_id,
            Expense.category_id == budget.category_id,
            extract("month", Expense.expense_date) == mon,
            extract("year", Expense.expense_date) == year
        ).scalar() or Decimal("0")

        spent = Decimal(str(spent))
        remaining = budget.budget_amount_usd - spent
        over_budget = spent > budget.budget_amount_usd

        # Get category name
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
def update_budget(
    budget_id: UUID,
    user_id: UUID,
    budget_amount_usd: Decimal,
    db: Session = Depends(get_db)
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == user_id
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    budget.budget_amount_usd = budget_amount_usd
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id,
        Budget.user_id == user_id
    ).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(budget)
    db.commit()
    return {"message": "Budget deleted"}