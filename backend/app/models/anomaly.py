from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_name = Column(String(50), nullable=False)        # large_transaction|high_value|velocity_spike|duplicate_like|missing_subscription
    severity = Column(String(20), nullable=False)         # low|medium|high
    status = Column(String(20), nullable=False, default="new", index=True)  # new|dismissed|investigating
    detected_at = Column(DateTime, server_default=func.now(), nullable=False)
    dismissed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
