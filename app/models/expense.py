import uuid
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    original_amount = Column(Numeric(12, 2), nullable=False)
    currency_code = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(12, 6), nullable=False)
    amount_usd = Column(Numeric(12, 2), nullable=False)
    expense_date = Column(Date, nullable=False)
    payment_method = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    receipt_reference = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
    group = relationship("Group", back_populates="expenses")
    splits = relationship("ExpenseSplit", back_populates="expense")


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expense_id = Column(UUID(as_uuid=True), ForeignKey("expenses.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    split_type = Column(String(20), nullable=False)  # equal, percentage, exact
    percentage = Column(Numeric(5, 2), nullable=True)
    exact_amount = Column(Numeric(12, 2), nullable=True)
    calculated_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    expense = relationship("Expense", back_populates="splits")