from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class EmailSourceConfig(Base):
    __tablename__ = "email_source_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_name = Column(String(100), nullable=False)
    sender_pattern = Column(String(255), nullable=False)
    is_builtin = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="email_sources")

    __table_args__ = (
        UniqueConstraint("user_id", "sender_pattern", name="uq_user_sender_pattern"),
    )
