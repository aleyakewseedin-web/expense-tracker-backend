import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    payer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_amount = Column(Numeric(12, 2), nullable=False)
    currency_code = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(12, 6), nullable=False)
    amount_usd = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    settled_at = Column(DateTime(timezone=True), server_default=func.now())