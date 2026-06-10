from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.expense import Expense
from app.models.user import User
from app.dependencies import get_current_user
from app.services.upload import upload_receipt
from uuid import UUID

router = APIRouter(prefix="/receipts", tags=["Receipts"])

@router.post("/{expense_id}")
async def upload_expense_receipt(
    expense_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/gif"]:
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB")

    url = await upload_receipt(contents, f"{expense_id}-receipt")
    expense.receipt_reference = url
    db.commit()

    return {"message": "Receipt uploaded successfully", "receipt_url": url}

@router.delete("/{expense_id}")
def remove_receipt(
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
    
    expense.receipt_reference = None
    db.commit()
    return {"message": "Receipt removed"}