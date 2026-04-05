from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


CATEGORIES = ["Rent", "Groceries", "Shopping", "Electricity", "Food & Dining", "Transport", "Entertainment", "Healthcare", "Others"]
PAYMENT_METHODS = ["Credit Card", "UPI", "Cash", "Debit Card", "Net Banking", "Others"]
SOURCES = ["manual", "email", "upload"]


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String(500), nullable=False)
    merchant = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, default="Others")
    payment_method = Column(String(50), nullable=False, default="Others")
    notes = Column(Text, nullable=True)
    source = Column(String(20), nullable=False, default="manual")
    email_message_id = Column(String(255), nullable=True, unique=True)
    payment_source = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="transactions")

    __table_args__ = (
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_category", "category"),
        Index("ix_transactions_payment_method", "payment_method"),
    )
