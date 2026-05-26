import uuid
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    summary_json = Column(JSON, nullable=True)
    ai_insight = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())