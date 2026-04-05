from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    totp_secret_encrypted = Column(Text, nullable=True)
    totp_enrolled = Column(Boolean, default=False, nullable=False)
    gmail_token_encrypted = Column(Text, nullable=True)
    sync_enabled = Column(Boolean, default=False, nullable=False, server_default='0')
    sync_interval_hours = Column(Integer, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    emails = relationship("EmailMetadata", back_populates="user", cascade="all, delete-orphan")
