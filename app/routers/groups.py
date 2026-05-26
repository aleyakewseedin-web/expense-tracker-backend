from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.group import Group, GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.user import User
from app.models.category import Category
from app.schemas.group import (
    GroupCreate, GroupResponse, MemberAdd,
    MemberResponse, GroupExpenseCreate, GroupExpenseResponse
)
from app.services.currency import get_exchange_rate
from typing import List,Optional
from uuid import UUID
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/groups", tags=["Groups"])


# ── Helper: check if user is a member of a group
def require_group_member(group_id: UUID, user_id: UUID, db: Session):
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this group"
        )
    return member


# ── Helper: check if user is the group creator
def require_group_creator(group_id: UUID, user_id: UUID, db: Session):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.created_by != user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the group creator can perform this action"
        )
    return group


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(
    user_id: UUID,
    group_data: GroupCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if this user already has a group with this name
    existing = db.query(Group).filter(
        Group.name == group_data.name,
        Group.created_by == user_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already have a group with this name"
        )

    group = Group(name=group_data.name, created_by=user_id)
    db.add(group)
    db.flush()
    member = GroupMember(group_id=group.id, user_id=user_id)
    db.add(member)
    db.commit()
    db.refresh(group)
    return group


@router.get("", response_model=List[GroupResponse])
def get_groups(user_id: UUID, db: Session = Depends(get_db)):
    # Get all groups this user belongs to
    memberships = db.query(GroupMember).filter(
        GroupMember.user_id == user_id
    ).all()
    group_ids = [m.group_id for m in memberships]
    return db.query(Group).filter(Group.id.in_(group_ids)).all()


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    require_group_member(group_id, user_id, db)
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get("/{group_id}/members", response_model=List[MemberResponse])
def get_members(group_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    require_group_member(group_id, user_id, db)
    memberships = db.query(GroupMember).filter(
        GroupMember.group_id == group_id
    ).all()
    member_ids = [m.user_id for m in memberships]
    return db.query(User).filter(User.id.in_(member_ids)).all()


@router.post("/{group_id}/members", status_code=201)
def add_member(
    group_id: UUID,
    user_id: UUID,
    member_data: MemberAdd,
    db: Session = Depends(get_db)
):
    # Only creator can add members
    require_group_creator(group_id, user_id, db)

    # Check user to add exists
    new_user = db.query(User).filter(User.id == member_data.user_id).first()
    if not new_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check not already a member
    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member_data.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    member = GroupMember(group_id=group_id, user_id=member_data.user_id)
    db.add(member)
    db.commit()
    return {"message": "Member added"}


@router.delete("/{group_id}/members/{member_user_id}")
def remove_member(
    group_id: UUID,
    member_user_id: UUID,
    user_id: UUID,
    new_admin_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    group = require_group_creator(group_id, user_id, db)

    # Cannot remove yourself via this endpoint — use /leave instead
    if member_user_id == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot remove yourself. Use DELETE /groups/{id}/leave instead"
        )

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member_user_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # If removing the current admin, new_admin_id is required
    if member_user_id == group.admin_id:
        if not new_admin_id:
            raise HTTPException(
                status_code=400,
                detail="This member is the admin. Provide new_admin_id to reassign admin before removing"
            )
        # Verify new admin is a member
        new_admin_member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == new_admin_id
        ).first()
        if not new_admin_member:
            raise HTTPException(
                status_code=400,
                detail="new_admin_id must be an existing group member"
            )
        group.admin_id = new_admin_id

    db.delete(member)
    db.commit()
    return {"message": "Member removed"}


@router.post("/{group_id}/expenses", response_model=GroupExpenseResponse, status_code=201)
async def create_group_expense(
    group_id: UUID,
    user_id: UUID,
    expense_data: GroupExpenseCreate,
    db: Session = Depends(get_db)
):
    # Must be a group member to add expenses
    require_group_member(group_id, user_id, db)

    # Validate category
    category = db.query(Category).filter(
        Category.id == expense_data.category_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Parse and validate date
    try:
        expense_date = date.fromisoformat(expense_data.expense_date)
        if expense_date > date.today():
            raise HTTPException(
                status_code=400,
                detail="Expense date cannot be in the future"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Get exchange rate
    rate = await get_exchange_rate(
        base_currency=expense_data.currency_code,
        target_currency="USD",
        db=db,
        expense_date=expense_date
    )
    amount_usd = round(float(expense_data.original_amount) * rate, 2)

    # Create the expense
    expense = Expense(
        user_id=user_id,
        group_id=group_id,
        category_id=expense_data.category_id,
        original_amount=expense_data.original_amount,
        currency_code=expense_data.currency_code.upper(),
        exchange_rate=rate,
        amount_usd=amount_usd,
        expense_date=expense_date,
        description=expense_data.description,
        payment_method=expense_data.payment_method
    )
    db.add(expense)
    db.flush()

    # Calculate and store splits
    members = expense_data.splits
    num_members = len(members)

    if expense_data.split_type == "equal":
        per_person = round(amount_usd / num_members, 2)
        for split in members:
            db.add(ExpenseSplit(
                expense_id=expense.id,
                user_id=split.user_id,
                split_type="equal",
                calculated_amount=per_person
            ))

    elif expense_data.split_type == "percentage":
        total_pct = sum(s.percentage or Decimal("0") for s in members)
        if total_pct != 100:
            raise HTTPException(
                status_code=400,
                detail=f"Percentages must sum to 100. Got {total_pct}"
            )
        for split in members:
            calc = round(amount_usd * float(split.percentage) / 100, 2)
            db.add(ExpenseSplit(
                expense_id=expense.id,
                user_id=split.user_id,
                split_type="percentage",
                percentage=split.percentage,
                calculated_amount=calc
            ))

    elif expense_data.split_type == "exact":
        total_exact = sum(s.exact_amount or Decimal("0") for s in members)
        if round(total_exact, 2) != round(expense_data.original_amount, 2):
            raise HTTPException(
                status_code=400,
                detail=f"Exact amounts must sum to {expense_data.original_amount}. Got {total_exact}"
            )
        for split in members:
            db.add(ExpenseSplit(
                expense_id=expense.id,
                user_id=split.user_id,
                split_type="exact",
                exact_amount=split.exact_amount,
                calculated_amount=float(split.exact_amount)
            ))

    db.commit()
    db.refresh(expense)
    return expense


@router.get("/{group_id}/expenses", response_model=List[GroupExpenseResponse])
def get_group_expenses(
    group_id: UUID,
    user_id: UUID,
    month: str = None,
    db: Session = Depends(get_db)
):
    require_group_member(group_id, user_id, db)

    query = db.query(Expense).filter(Expense.group_id == group_id)

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
        from sqlalchemy import extract
        query = query.filter(
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == mon
        )

    return query.order_by(Expense.expense_date.desc()).all()

@router.delete("/{group_id}/leave")
def leave_group(
    group_id: UUID,
    user_id: UUID,
    new_admin_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    # Check user is a member
    require_group_member(group_id, user_id, db)

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Get remaining members excluding this user
    remaining = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id != user_id
    ).all()

    # Check if user is the admin
    is_admin = str(group.admin_id) == str(user_id)

    if is_admin:
        # If there are other members, new_admin_id is mandatory
        if remaining:
            if not new_admin_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"You are the admin and there are {len(remaining)} other members. You must assign a new admin before leaving. Provide new_admin_id."
                )

            # Cannot assign yourself as new admin
            if str(new_admin_id) == str(user_id):
                raise HTTPException(
                    status_code=400,
                    detail="You cannot assign yourself as the new admin while leaving"
                )

            # Verify new admin is actually a remaining member
            new_admin_is_member = any(
                str(m.user_id) == str(new_admin_id) for m in remaining
            )
            if not new_admin_is_member:
                raise HTTPException(
                    status_code=400,
                    detail="new_admin_id must be an existing group member"
                )

            group.admin_id = new_admin_id

        else:
            # Admin is last member — delete the group entirely
            db.query(ExpenseSplit).filter(
                ExpenseSplit.expense_id.in_(
                    db.query(Expense.id).filter(Expense.group_id == group_id)
                )
            ).delete(synchronize_session=False)
            db.query(Expense).filter(Expense.group_id == group_id).delete()
            db.query(GroupMember).filter(GroupMember.group_id == group_id).delete()
            db.delete(group)
            db.commit()
            return {"message": "Group deleted as you were the last member"}

    # Remove the leaving user
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    db.delete(member)
    db.commit()
    return {"message": "You have left the group"}