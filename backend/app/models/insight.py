from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Insight(Base):
    __tablename__ = "insights"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_type = Column(String(50), nullable=False)     # spend_pace|category_surge|top_merchant|quiet_month
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="active", index=True)  # active|dismissed
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
    dismissed_at = Column(DateTime, nullable=True)
