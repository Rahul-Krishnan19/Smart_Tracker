"""
Tests for SpendingLimit model, service functions, and API endpoints.
Phase 6, Plan 02 — GOAL-02 (simplified spending limit backend storage)
"""
import pytest
from decimal import Decimal

import sqlalchemy.exc

from app.database import Base
from app.models.spending_limit import SpendingLimit


# ---------------------------------------------------------------------------
# Task 1: Model tests
# ---------------------------------------------------------------------------

class TestSpendingLimitModel:
    def test_spending_limit_table_in_metadata(self):
        """spending_limits table must be registered in Base.metadata."""
        assert "spending_limits" in Base.metadata.tables

    def test_spending_limit_insert(self, in_memory_db):
        """Insert a SpendingLimit row and verify all fields round-trip."""
        sl = SpendingLimit(
            user_id=1,
            granularity="monthly",
            amount=Decimal("30000.00"),
        )
        in_memory_db.add(sl)
        in_memory_db.commit()
        in_memory_db.refresh(sl)

        assert sl.id is not None
        assert sl.user_id == 1
        assert sl.granularity == "monthly"
        assert Decimal(str(sl.amount)) == Decimal("30000.00")
        assert sl.created_at is not None
        assert sl.updated_at is not None

    def test_spending_limit_unique_constraint(self, in_memory_db):
        """Inserting two rows with the same (user_id, granularity) raises IntegrityError."""
        sl1 = SpendingLimit(user_id=1, granularity="monthly", amount=Decimal("30000.00"))
        sl2 = SpendingLimit(user_id=1, granularity="monthly", amount=Decimal("25000.00"))
        in_memory_db.add(sl1)
        in_memory_db.commit()
        in_memory_db.add(sl2)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            in_memory_db.commit()

    def test_spending_limit_different_granularities_allowed(self, in_memory_db):
        """Same user_id with different granularities must both succeed."""
        sl_monthly = SpendingLimit(user_id=1, granularity="monthly", amount=Decimal("30000.00"))
        sl_weekly = SpendingLimit(user_id=1, granularity="weekly", amount=Decimal("8000.00"))
        in_memory_db.add(sl_monthly)
        in_memory_db.add(sl_weekly)
        in_memory_db.commit()

        rows = in_memory_db.query(SpendingLimit).filter(SpendingLimit.user_id == 1).all()
        assert len(rows) == 2

    def test_spending_limit_user_isolation(self, in_memory_db):
        """Different users can have the same granularity; query by user_id filters correctly."""
        sl_user1 = SpendingLimit(user_id=1, granularity="monthly", amount=Decimal("30000.00"))
        sl_user2 = SpendingLimit(user_id=2, granularity="monthly", amount=Decimal("50000.00"))
        in_memory_db.add(sl_user1)
        in_memory_db.add(sl_user2)
        in_memory_db.commit()

        user1_rows = in_memory_db.query(SpendingLimit).filter(SpendingLimit.user_id == 1).all()
        assert len(user1_rows) == 1
        assert Decimal(str(user1_rows[0].amount)) == Decimal("30000.00")


# ---------------------------------------------------------------------------
# Task 2: Service function tests
# ---------------------------------------------------------------------------

class TestSpendingLimitService:
    def test_get_spending_limit_returns_none_when_absent(self, in_memory_db):
        """get_spending_limit returns None when no row exists."""
        from app.services.spending_limit_service import get_spending_limit
        result = get_spending_limit(in_memory_db, user_id=1, granularity="monthly")
        assert result is None

    def test_upsert_spending_limit_creates_new(self, in_memory_db):
        """upsert_spending_limit creates a new row when none exists."""
        from app.services.spending_limit_service import upsert_spending_limit, get_spending_limit
        row = upsert_spending_limit(in_memory_db, user_id=1, granularity="monthly", amount=Decimal("30000"))
        assert row.id is not None
        assert row.user_id == 1
        assert row.granularity == "monthly"
        assert Decimal(str(row.amount)) == Decimal("30000")

        # Verify it's in the DB
        fetched = get_spending_limit(in_memory_db, user_id=1, granularity="monthly")
        assert fetched is not None
        assert Decimal(str(fetched.amount)) == Decimal("30000")

    def test_upsert_spending_limit_updates_existing(self, in_memory_db):
        """upsert_spending_limit updates amount when a row already exists; only one row remains."""
        from app.services.spending_limit_service import upsert_spending_limit
        # First upsert — creates
        row1 = upsert_spending_limit(in_memory_db, user_id=1, granularity="monthly", amount=Decimal("30000"))
        created_at = row1.created_at

        # Second upsert — updates
        row2 = upsert_spending_limit(in_memory_db, user_id=1, granularity="monthly", amount=Decimal("40000"))
        assert Decimal(str(row2.amount)) == Decimal("40000")

        # Exactly one row in the table for this (user, granularity)
        count = in_memory_db.query(SpendingLimit).filter(
            SpendingLimit.user_id == 1,
            SpendingLimit.granularity == "monthly",
        ).count()
        assert count == 1

        # updated_at should be >= created_at
        assert row2.updated_at >= created_at

    def test_delete_spending_limit_existing(self, in_memory_db):
        """delete_spending_limit returns True when row existed and removes it."""
        from app.services.spending_limit_service import upsert_spending_limit, delete_spending_limit, get_spending_limit
        upsert_spending_limit(in_memory_db, user_id=1, granularity="monthly", amount=Decimal("30000"))
        result = delete_spending_limit(in_memory_db, user_id=1, granularity="monthly")
        assert result is True
        assert get_spending_limit(in_memory_db, user_id=1, granularity="monthly") is None

    def test_delete_spending_limit_idempotent(self, in_memory_db):
        """delete_spending_limit returns False (no exception) when row does not exist."""
        from app.services.spending_limit_service import delete_spending_limit
        result = delete_spending_limit(in_memory_db, user_id=1, granularity="monthly")
        assert result is False
