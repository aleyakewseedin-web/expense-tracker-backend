from fastapi import APIRouter, Depends, HTTPException, status,Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse
from app.dependencies import get_current_user
from typing import List
from uuid import UUID
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    categories = db.query(Category).filter(
        (Category.is_system == True) |
        (Category.user_id == current_user.id)
    ).all()
    return categories


@router.post("", response_model=CategoryResponse, status_code=201)
@limiter.limit("20/minute")
def create_category(
    request: Request,
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.name == category_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists"
        )

    category = Category(
        name=category_data.name,
        is_system=False,
        user_id=current_user.id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=200)
@limiter.limit("20/minute")
def delete_category(
    request: Request,
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id,
        Category.is_system == False
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or cannot delete system category"
        )

    db.delete(category)
    db.commit()
    return {"message": "Category deleted"}