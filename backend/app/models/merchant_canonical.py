from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class MerchantCanonicalMap(Base):
    """Maps a raw merchant string (as scraped from a bank email) to a single
    canonical display name, per user.

    Populated by the merchant normalization agent (Agent 3) after each sync.
    Analytics merchant breakdown LEFT JOINs this table so spend from variant
    names (e.g. "AMAZON IN", "Amazon", "AMAZON.IN") rolls up under one label.
    """

    __tablename__ = "merchant_canonical_map"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    raw_merchant = Column(String(255), nullable=False)
    canonical_merchant = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "raw_merchant", name="uq_merchant_canonical_user_raw"
        ),
    )
