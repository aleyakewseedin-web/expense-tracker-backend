from fastapi import APIRouter, Depends, HTTPException, status, Request 
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
from app.models.expense import Expense
from app.models.category import Category
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.currency import get_exchange_rate
from app.services.cache import invalidate_report_cache
from app.dependencies import get_current_user
from typing import List, Optional
from uuid import UUID
from datetime import date
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import File, UploadFile
from app.services.upload import upload_receipt
from fastapi.responses import StreamingResponse
from app.services.cache import get_redis_client
import io
import csv

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("", response_model=ExpenseResponse, status_code=201)
@limiter.limit("30/minute")
async def create_expense(
    request: Request,
    expense_data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(
        Category.id == expense_data.category_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    rate = await get_exchange_rate(
        base_currency=expense_data.currency_code,
        target_currency="USD",
        db=db,
        expense_date=expense_data.expense_date
    )

    amount_usd = float(expense_data.original_amount) * rate

    expense = Expense(
        user_id=current_user.id,
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

    month_str = expense.expense_date.strftime("%Y-%m")
    invalidate_report_cache(str(current_user.id), month_str)
     
     # Invalidate trend cache
    redis = get_redis_client()
    if redis:
        for key in redis.scan_iter(f"trend:{current_user.id}:*"):
            redis.delete(key)

    return expense

@router.get("/export")
def export_expenses(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Expense).filter(Expense.user_id == current_user.id)
    if month:
        parts = month.split("-")
        try:
            year, mon = int(parts[0]), int(parts[1])
        except:
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
        query = query.filter(
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == mon
        )
    expenses = query.order_by(Expense.expense_date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Original Amount", "Currency", "Amount (USD)", "Exchange Rate", "Payment Method"])
    for e in expenses:
        category = db.query(Category).filter(Category.id == e.category_id).first()
        writer.writerow([
            e.expense_date.strftime("%Y-%m-%d"),
            e.description or "",
            category.name if category else "Unknown",
            float(e.original_amount),
            e.currency_code,
            float(e.amount_usd),
            float(e.exchange_rate),
            e.payment_method or ""
        ])
    output.seek(0)
    filename = f"expenses-{month}.csv" if month else "expenses.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("", response_model=List[ExpenseResponse])
def get_expenses(
    month: Optional[str] = None,
    category_id: Optional[UUID] = None,
    group_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Expense).filter(Expense.user_id == current_user.id)

    if month:
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
@limiter.limit("30/minute")
async def update_expense(
    request: Request,
    expense_id: UUID,
    updates: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if updates.category_id:
        category = db.query(Category).filter(Category.id == updates.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        expense.category_id = updates.category_id

    if updates.original_amount or updates.currency_code:
        new_amount = updates.original_amount or expense.original_amount
        new_currency = updates.currency_code or expense.currency_code
        rate = await get_exchange_rate(base_currency=new_currency, target_currency="USD", db=db)
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

    db.commit()
    db.refresh(expense)

    month_str = expense.expense_date.strftime("%Y-%m")
    invalidate_report_cache(str(current_user.id), month_str)

    return expense


@router.delete("/{expense_id}")
@limiter.limit("30/minute")
def delete_expense(
    request: Request,
    expense_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    month_str = expense.expense_date.strftime("%Y-%m")

    from app.models.expense import ExpenseSplit
    db.query(ExpenseSplit).filter(
        ExpenseSplit.expense_id == expense_id
    ).delete()

    db.delete(expense)
    db.commit()
    invalidate_report_cache(str(current_user.id), month_str)
    
     # Invalidate trend cache
    redis = get_redis_client()
    if redis:
        for key in redis.scan_iter(f"trend:{current_user.id}:*"):
            redis.delete(key)

    return {"message": "Expense deleted"}



