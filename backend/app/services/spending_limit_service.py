"""
Spending limit service — get/upsert/delete per-granularity spending limits per user.
Phase 6, Plan 02 — GOAL-02 simplified spending limit backend storage.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.spending_limit import SpendingLimit


def get_spending_limit(db: Session, user_id: int, granularity: str) -> Optional[SpendingLimit]:
    """Return the SpendingLimit row for (user_id, granularity) or None if absent."""
    return (
        db.query(SpendingLimit)
        .filter(SpendingLimit.user_id == user_id, SpendingLimit.granularity == granularity)
        .first()
    )


def upsert_spending_limit(
    db: Session, user_id: int, granularity: str, amount: Decimal
) -> SpendingLimit:
    """Create a new SpendingLimit row or update amount if one already exists."""
    existing = get_spending_limit(db, user_id, granularity)
    if existing:
        existing.amount = amount
        db.commit()
        db.refresh(existing)
        return existing
    new_row = SpendingLimit(user_id=user_id, granularity=granularity, amount=amount)
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row


def delete_spending_limit(db: Session, user_id: int, granularity: str) -> bool:
    """Delete the SpendingLimit row for (user_id, granularity).

    Returns True if a row was deleted, False if no row existed (idempotent).
    """
    existing = get_spending_limit(db, user_id, granularity)
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True
