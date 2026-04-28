"""
Tests for extended transaction service filters, new API helpers, export, and merchant breakdown.
Phase 5, Plan 01 - Task 2
"""
import pytest
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionFilters
from app.services.transaction_service import TransactionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db, user_id=1):
    """Create a minimal User for FK constraints."""
    user = User(
        id=user_id,
        username=f"testuser{user_id}",
        email=f"test{user_id}@example.com",
        password_hash="hashedpassword",
        totp_secret_encrypted=None,
        totp_enrolled=False,
    )
    db.add(user)
    db.flush()
    return user


def _make_transaction(
    db,
    user_id=1,
    merchant="TestMerchant",
    category="Others",
    amount=Decimal("100.00"),
    payment_source=None,
    payment_method="UPI",
    transaction_date=None,
    description=None,
):
    """Create a minimal Transaction for testing."""
    tx = Transaction(
        user_id=user_id,
        transaction_date=transaction_date or date(2026, 1, 15),
        amount=amount,
        description=description or f"Payment to {merchant}",
        merchant=merchant,
        category=category,
        payment_method=payment_method,
        payment_source=payment_source,
        source="manual",
    )
    db.add(tx)
    db.flush()
    return tx


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------

class TestListFilters:
    def test_list_filters_payment_source(self, in_memory_db):
        """TXN-05: list() filters by payment_source when set."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, payment_source="HDFC CC ••6054", merchant="Swiggy")
        _make_transaction(in_memory_db, payment_source="ICICI UPI", merchant="Amazon")
        _make_transaction(in_memory_db, payment_source=None, merchant="BigBasket")
        in_memory_db.commit()

        filters = TransactionFilters(payment_source="HDFC CC ••6054")
        result = svc.list(in_memory_db, 1, filters)

        assert result["total"] == 1
        assert result["items"][0].merchant == "Swiggy"

    def test_list_filters_min_amount(self, in_memory_db):
        """TXN-05: list() filters by min_amount."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, amount=Decimal("100.00"), merchant="Cheap")
        _make_transaction(in_memory_db, amount=Decimal("500.00"), merchant="Mid")
        _make_transaction(in_memory_db, amount=Decimal("1000.00"), merchant="Expensive")
        in_memory_db.commit()

        filters = TransactionFilters(min_amount=Decimal("400.00"))
        result = svc.list(in_memory_db, 1, filters)

        assert result["total"] == 2
        merchants = {tx.merchant for tx in result["items"]}
        assert "Mid" in merchants
        assert "Expensive" in merchants
        assert "Cheap" not in merchants

    def test_list_filters_max_amount(self, in_memory_db):
        """TXN-05: list() filters by max_amount."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, amount=Decimal("100.00"), merchant="Cheap")
        _make_transaction(in_memory_db, amount=Decimal("500.00"), merchant="Mid")
        _make_transaction(in_memory_db, amount=Decimal("1000.00"), merchant="Expensive")
        in_memory_db.commit()

        filters = TransactionFilters(max_amount=Decimal("600.00"))
        result = svc.list(in_memory_db, 1, filters)

        assert result["total"] == 2
        merchants = {tx.merchant for tx in result["items"]}
        assert "Cheap" in merchants
        assert "Mid" in merchants
        assert "Expensive" not in merchants

    def test_list_filters_amount_range(self, in_memory_db):
        """TXN-05: list() filters by min_amount and max_amount together."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, amount=Decimal("100.00"), merchant="Cheap")
        _make_transaction(in_memory_db, amount=Decimal("500.00"), merchant="Mid")
        _make_transaction(in_memory_db, amount=Decimal("1000.00"), merchant="Expensive")
        in_memory_db.commit()

        filters = TransactionFilters(min_amount=Decimal("200.00"), max_amount=Decimal("600.00"))
        result = svc.list(in_memory_db, 1, filters)

        assert result["total"] == 1
        assert result["items"][0].merchant == "Mid"


class TestGetSummaryWithFilters:
    def test_summary_with_payment_source_filter(self, in_memory_db):
        """TXN-07: get_summary() respects payment_source filter."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, payment_source="HDFC CC ••6054", amount=Decimal("200.00"))
        _make_transaction(in_memory_db, payment_source="ICICI UPI", amount=Decimal("300.00"))
        _make_transaction(in_memory_db, payment_source="HDFC CC ••6054", amount=Decimal("150.00"))
        in_memory_db.commit()

        filters = TransactionFilters(payment_source="HDFC CC ••6054")
        result = svc.get_summary(in_memory_db, 1, filters)

        assert result["transaction_count"] == 2
        assert abs(result["total_amount"] - 350.0) < 0.01

    def test_summary_with_all_filters(self, in_memory_db):
        """TXN-07: get_summary() respects all filter params."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(
            in_memory_db, payment_source="HDFC CC ••6054",
            amount=Decimal("500.00"), category="Food & Dining"
        )
        _make_transaction(
            in_memory_db, payment_source="HDFC CC ••6054",
            amount=Decimal("50.00"), category="Food & Dining"  # below min
        )
        _make_transaction(
            in_memory_db, payment_source="ICICI UPI",
            amount=Decimal("500.00"), category="Food & Dining"  # wrong source
        )
        in_memory_db.commit()

        filters = TransactionFilters(
            payment_source="HDFC CC ••6054",
            min_amount=Decimal("100.00"),
        )
        result = svc.get_summary(in_memory_db, 1, filters)

        assert result["transaction_count"] == 1
        assert abs(result["total_amount"] - 500.0) < 0.01

    def test_summary_returns_expected_structure(self, in_memory_db):
        """Summary response must include expected fields."""
        svc = TransactionService()
        _make_user(in_memory_db)
        _make_transaction(in_memory_db, amount=Decimal("100.00"))
        in_memory_db.commit()

        result = svc.get_summary(in_memory_db, 1, TransactionFilters())

        assert "total_amount" in result
        assert "transaction_count" in result
        assert "category_breakdown" in result
        assert "payment_breakdown" in result


class TestExport:
    def test_export_returns_all_no_pagination(self, in_memory_db):
        """TXN-08: export() returns all matching transactions without pagination."""
        svc = TransactionService()
        _make_user(in_memory_db)

        for i in range(60):
            _make_transaction(
                in_memory_db,
                merchant=f"Merchant{i}",
                amount=Decimal(str(100 + i)),
            )
        in_memory_db.commit()

        filters = TransactionFilters()
        rows = svc.export(in_memory_db, 1, filters)

        assert len(rows) == 60

    def test_export_respects_filters(self, in_memory_db):
        """export() applies filters before returning all rows."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, payment_source="HDFC CC ••6054", merchant="A")
        _make_transaction(in_memory_db, payment_source="ICICI UPI", merchant="B")
        in_memory_db.commit()

        filters = TransactionFilters(payment_source="HDFC CC ••6054")
        rows = svc.export(in_memory_db, 1, filters)

        assert len(rows) == 1
        assert rows[0].merchant == "A"


class TestMerchantBreakdown:
    def test_merchant_breakdown_returns_top_10(self, in_memory_db):
        """ANA-07: get_merchant_breakdown() returns top 10 merchants by total spend."""
        svc = TransactionService()
        _make_user(in_memory_db)

        # Create 12 distinct merchants
        for i in range(12):
            _make_transaction(
                in_memory_db,
                merchant=f"Merchant{i:02d}",
                amount=Decimal(str((i + 1) * 100)),  # Different amounts
            )
        in_memory_db.commit()

        filters = TransactionFilters()
        result = svc.get_merchant_breakdown(in_memory_db, 1, filters)

        assert len(result["merchants"]) == 10
        # Verify sorted by total descending
        totals = [m["total"] for m in result["merchants"]]
        assert totals == sorted(totals, reverse=True)

    def test_merchant_breakdown_has_pct_of_total(self, in_memory_db):
        """ANA-07: merchant breakdown includes pct_of_total."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, merchant="A", amount=Decimal("300.00"))
        _make_transaction(in_memory_db, merchant="B", amount=Decimal("700.00"))
        in_memory_db.commit()

        filters = TransactionFilters()
        result = svc.get_merchant_breakdown(in_memory_db, 1, filters)

        assert len(result["merchants"]) == 2
        b_entry = next(m for m in result["merchants"] if m["merchant"] == "B")
        a_entry = next(m for m in result["merchants"] if m["merchant"] == "A")
        assert abs(b_entry["pct_of_total"] - 70.0) < 0.5
        assert abs(a_entry["pct_of_total"] - 30.0) < 0.5

    def test_merchant_breakdown_has_count_and_avg(self, in_memory_db):
        """ANA-07: merchant breakdown includes count and avg per merchant."""
        svc = TransactionService()
        _make_user(in_memory_db)

        _make_transaction(in_memory_db, merchant="Swiggy", amount=Decimal("100.00"))
        _make_transaction(in_memory_db, merchant="Swiggy", amount=Decimal("200.00"))
        in_memory_db.commit()

        filters = TransactionFilters()
        result = svc.get_merchant_breakdown(in_memory_db, 1, filters)

        swiggy = result["merchants"][0]
        assert swiggy["count"] == 2
        assert abs(swiggy["avg"] - 150.0) < 0.01
        assert abs(swiggy["total"] - 300.0) < 0.01


class TestBulkCategorize:
    def test_bulk_categorize_scoped_to_user(self, in_memory_db):
        """TXN-12: bulk_categorize updates only current user's transactions."""
        svc = TransactionService()
        _make_user(in_memory_db, user_id=1)
        _make_user(in_memory_db, user_id=2)

        tx_user1 = _make_transaction(in_memory_db, user_id=1, category="Others")
        tx_user2 = _make_transaction(in_memory_db, user_id=2, category="Others")
        in_memory_db.commit()

        # bulk categorize transaction belonging to user 2, but as user 1 — should be rejected
        updated = svc.bulk_categorize(
            in_memory_db,
            user_id=1,
            transaction_ids=[tx_user2.id],
            category="Shopping",
        )
        in_memory_db.refresh(tx_user2)

        assert updated == 0
        assert tx_user2.category == "Others"

    def test_bulk_categorize_updates_own_transactions(self, in_memory_db):
        """TXN-12: bulk_categorize updates all specified transactions for user."""
        svc = TransactionService()
        _make_user(in_memory_db)

        tx1 = _make_transaction(in_memory_db, category="Others")
        tx2 = _make_transaction(in_memory_db, category="Others")
        in_memory_db.commit()

        updated = svc.bulk_categorize(
            in_memory_db,
            user_id=1,
            transaction_ids=[tx1.id, tx2.id],
            category="Groceries",
        )
        in_memory_db.refresh(tx1)
        in_memory_db.refresh(tx2)

        assert updated == 2
        assert tx1.category == "Groceries"
        assert tx2.category == "Groceries"
