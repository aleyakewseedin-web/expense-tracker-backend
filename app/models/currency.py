import uuid
from sqlalchemy import Column, String, Numeric, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base

class CurrencySnapshot(Base):
    __tablename__ = "currency_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_currency = Column(String(3), nullable=False)
    target_currency = Column(String(3), nullable=False)
    exchange_rate = Column(Numeric(12, 6), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())