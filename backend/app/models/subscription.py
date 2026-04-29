from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant = Column(String(255), nullable=False)
    typical_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active|canceled
    first_seen_month = Column(Date, nullable=False)
    last_seen_month = Column(Date, nullable=False)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "merchant", name="uq_subscription_user_merchant"),
    )
