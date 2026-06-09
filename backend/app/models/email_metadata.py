from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class EmailMetadata(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gmail_message_id = Column(String(255), unique=True, nullable=False)
    sender = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    received_at = Column(DateTime, nullable=True)
    parse_status = Column(String(20), nullable=False, default="pending")
    parse_error = Column(Text, nullable=True)
    bank_name = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    delete_after = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="emails")

    __table_args__ = (
        Index("ix_emails_user_received", "user_id", "received_at"),
        Index("ix_emails_parse_status", "parse_status"),
    )
