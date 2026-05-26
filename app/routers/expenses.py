from app.models import expense
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
from app.models.expense import Expense
from app.models.category import Category
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.currency import get_exchange_rate
from typing import List, Optional
from uuid import UUID
from datetime import date
from app.services.cache import invalidate_report_cache

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    user_id: UUID,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db)
):
    # Verify category exists
    category = db.query(Category).filter(
        Category.id == expense_data.category_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get exchange rate and convert to USD
    rate = await get_exchange_rate(
        base_currency=expense_data.currency_code,
        target_currency="USD",
        db=db,
        expense_date=expense_data.expense_date
    )

    amount_usd = float(expense_data.original_amount) * rate

    expense = Expense(
        user_id=user_id,
        category_id=expense_data.category_id,
        group_id=expense_data.group_id,
        original_amount=expense_data.original_amount,
        currency_code=expense_data.currency_code.upper(),
        exchange_rate=rate,
        amount_usd=round(amount_usd, 2),
        expense_date=expense_data.expense_date,
        description=expense_data.description,
        payment_method=expense_data.payment_method,
        receipt_reference=expense_data.receipt_reference
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Invalidate monthly cache for this user and month
    month_str = expense.expense_date.strftime("%Y-%m")
    invalidate_report_cache(str(user_id), month_str)

    return expense
    



@router.get("", response_model=List[ExpenseResponse])
def get_expenses(
    user_id: UUID,
    month: Optional[str] = None,
    category_id: Optional[UUID] = None,
    group_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Expense).filter(Expense.user_id == user_id)

    if month:
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

        query = query.filter(
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == mon
        )

    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if group_id:
        query = query.filter(Expense.group_id == group_id)

    return query.order_by(Expense.expense_date.desc()).all()

@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == user_id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: UUID,
    user_id: UUID,
    updates: ExpenseUpdate,
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == user_id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # If amount or currency changed, recalculate USD
    if updates.original_amount or updates.currency_code:
        new_amount = updates.original_amount or expense.original_amount
        new_currency = updates.currency_code or expense.currency_code
        rate = await get_exchange_rate(
            base_currency=new_currency,
            target_currency="USD",
            db=db
        )
        expense.exchange_rate = rate
        expense.amount_usd = round(float(new_amount) * rate, 2)

    if updates.original_amount:
        expense.original_amount = updates.original_amount
    if updates.currency_code:
        expense.currency_code = updates.currency_code.upper()
    if updates.description is not None:
        expense.description = updates.description
    if updates.expense_date:
        expense.expense_date = updates.expense_date
    if updates.payment_method:
        expense.payment_method = updates.payment_method
    if updates.category_id:
        expense.category_id = updates.category_id
    
    if updates.category_id:
      category = db.query(Category).filter(
        Category.id == updates.category_id
    ).first()
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )
    expense.category_id = updates.category_id

    db.commit()
    month_str = expense.expense_date.strftime("%Y-%m")
    invalidate_report_cache(str(user_id), month_str)
    
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == user_id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    month_str = expense.expense_date.strftime("%Y-%m")
    invalidate_report_cache(str(user_id), month_str)
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted"}


