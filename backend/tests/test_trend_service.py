"""
Tests for TrendService — ANA-03, ANA-04, ANA-06 backend.
Phase 6, Plan 01 - Task 1 (TDD RED)
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.models.transaction import Transaction
from app.services.trend_service import trend_service, TrendService, GRANULARITY_FORMAT


# ---------------------------------------------------------------------------
# Helper to seed a transaction quickly
# ---------------------------------------------------------------------------

def _make_tx(db, user_id, transaction_date, amount, category="Others", payment_source=None):
    tx = Transaction(
        user_id=user_id,
        transaction_date=transaction_date,
        amount=Decimal(str(amount)),
        description="test tx",
        category=category,
        payment_method="UPI",
        source="manual",
        payment_source=payment_source,
    )
    db.add(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------

def test_granularity_format_constants():
    assert GRANULARITY_FORMAT == {
        "daily":   "%Y-%m-%d",
        "weekly":  "%Y-W%W",
        "monthly": "%Y-%m",
        "annual":  "%Y",
    }


# ---------------------------------------------------------------------------
# 2. Monthly grouping
# ---------------------------------------------------------------------------

def test_get_trend_monthly_groups_by_month(in_memory_db):
    """Two months should yield 2 trend items with correct totals."""
    _make_tx(in_memory_db, 1, date(2026, 3, 15), 100)
    _make_tx(in_memory_db, 1, date(2026, 3, 20), 200)
    _make_tx(in_memory_db, 1, date(2026, 4, 5),  500)
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2026, 3, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    trend = result["trend"]
    assert len(trend) == 2

    # Items must be ordered ascending by period_start
    assert trend[0]["period_start"] < trend[1]["period_start"]

    march = trend[0]
    april = trend[1]

    assert march["total"] == 300.0
    assert march["count"] == 2
    assert april["total"] == 500.0
    assert april["count"] == 1


# ---------------------------------------------------------------------------
# 3. Daily grouping
# ---------------------------------------------------------------------------

def test_get_trend_daily_groups_by_day(in_memory_db):
    """Three transactions across 2 days → 2 daily items."""
    _make_tx(in_memory_db, 1, date(2026, 4, 15), 100)
    _make_tx(in_memory_db, 1, date(2026, 4, 15), 200)
    _make_tx(in_memory_db, 1, date(2026, 4, 16), 50)
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="daily",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    trend = result["trend"]
    assert len(trend) == 2
    assert trend[0]["count"] == 2   # Apr 15 — two transactions
    assert trend[1]["count"] == 1   # Apr 16 — one transaction


# ---------------------------------------------------------------------------
# 4. Annual grouping
# ---------------------------------------------------------------------------

def test_get_trend_annual_groups_by_year(in_memory_db):
    """Transactions in 2025 and 2026 → 2 annual items with correct labels and boundaries."""
    _make_tx(in_memory_db, 1, date(2025, 6, 1), 100)
    _make_tx(in_memory_db, 1, date(2025, 11, 1), 200)
    _make_tx(in_memory_db, 1, date(2026, 1, 15), 300)
    _make_tx(in_memory_db, 1, date(2026, 4, 10), 400)
    _make_tx(in_memory_db, 1, date(2026, 8, 20), 500)
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="annual",
        date_from=date(2024, 1, 1),
        date_to=date(2026, 12, 31),
        payment_source=None,
    )

    trend = result["trend"]
    assert len(trend) == 2

    labels = [item["period_label"] for item in trend]
    assert "2025" in labels
    assert "2026" in labels

    item_2025 = next(i for i in trend if i["period_label"] == "2025")
    item_2026 = next(i for i in trend if i["period_label"] == "2026")

    assert item_2025["period_start"] == date(2025, 1, 1)
    assert item_2025["period_end"]   == date(2025, 12, 31)
    assert item_2026["period_start"] == date(2026, 1, 1)
    assert item_2026["period_end"]   == date(2026, 12, 31)


# ---------------------------------------------------------------------------
# 5. Weekly grouping — data-driven bounds
# ---------------------------------------------------------------------------

def test_get_trend_weekly_uses_data_bounds(in_memory_db):
    """Apr 13 (Mon) and Apr 15 (Wed) should land in the same week."""
    _make_tx(in_memory_db, 1, date(2026, 4, 13), 100)  # Monday
    _make_tx(in_memory_db, 1, date(2026, 4, 15), 200)  # Wednesday
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="weekly",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    trend = result["trend"]
    assert len(trend) >= 1

    week_item = trend[0]
    assert week_item["period_start"] <= date(2026, 4, 13)
    assert week_item["period_end"]   >= date(2026, 4, 15)
    assert (week_item["period_end"] - week_item["period_start"]) == timedelta(days=6)


# ---------------------------------------------------------------------------
# 6. Monthly period boundaries (true calendar bounds, not data bounds)
# ---------------------------------------------------------------------------

def test_get_trend_monthly_period_boundaries(in_memory_db):
    """April period should span Apr 1 – Apr 30, not just the transaction date."""
    _make_tx(in_memory_db, 1, date(2026, 4, 15), 500)
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    april = result["trend"][0]
    assert april["period_start"] == date(2026, 4, 1)
    assert april["period_end"]   == date(2026, 4, 30)


# ---------------------------------------------------------------------------
# 7. payment_source filter
# ---------------------------------------------------------------------------

def test_get_trend_payment_source_filter(in_memory_db):
    """Only transactions matching payment_source should be included."""
    _make_tx(in_memory_db, 1, date(2026, 4, 15), 1000, payment_source="HDFC CC ’6054")
    _make_tx(in_memory_db, 1, date(2026, 4, 15),  500, payment_source="ICICI ’6005")
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source="HDFC CC ’6054",
    )

    trend = result["trend"]
    assert len(trend) == 1
    assert trend[0]["total"] == 1000.0


# ---------------------------------------------------------------------------
# 8. category_totals (ANA-04)
# ---------------------------------------------------------------------------

def test_get_trend_category_totals(in_memory_db):
    """Each trend item must carry per-category totals."""
    _make_tx(in_memory_db, 1, date(2026, 4, 1),  500, category="Food & Dining")
    _make_tx(in_memory_db, 1, date(2026, 4, 2),  300, category="Food & Dining")
    _make_tx(in_memory_db, 1, date(2026, 4, 3),  400, category="Transport")
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    april = result["trend"][0]
    assert april["category_totals"] == {"Food & Dining": 800.0, "Transport": 400.0}


# ---------------------------------------------------------------------------
# 9. User isolation
# ---------------------------------------------------------------------------

def test_get_trend_user_isolation(in_memory_db):
    """User 1 query must not include user 2's transactions."""
    _make_tx(in_memory_db, 1, date(2026, 4, 10), 200)
    _make_tx(in_memory_db, 2, date(2026, 4, 10), 999)
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    trend = result["trend"]
    assert len(trend) == 1
    assert trend[0]["total"] == 200.0


# ---------------------------------------------------------------------------
# 10. compute_pct_change — basic cases
# ---------------------------------------------------------------------------

def test_compute_pct_change_basic():
    assert trend_service.compute_pct_change(150.0, 100.0) == 50.0
    assert trend_service.compute_pct_change(50.0, 100.0) == -50.0


# ---------------------------------------------------------------------------
# 11. compute_pct_change — zero previous (div-by-zero guard)
# ---------------------------------------------------------------------------

def test_compute_pct_change_zero_previous():
    assert trend_service.compute_pct_change(100.0, 0.0) is None


# ---------------------------------------------------------------------------
# 12. pct_change included in response (ANA-06)
# ---------------------------------------------------------------------------

def test_get_trend_includes_pct_change(in_memory_db):
    """current_total, previous_total, and pct_change must be in the response."""
    # March 2026: total ₹100
    _make_tx(in_memory_db, 1, date(2026, 3, 10), 60)
    _make_tx(in_memory_db, 1, date(2026, 3, 20), 40)
    # April 2026: total ₹150
    _make_tx(in_memory_db, 1, date(2026, 4, 5),  80)
    _make_tx(in_memory_db, 1, date(2026, 4, 25), 70)
    in_memory_db.commit()

    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 30),
        payment_source=None,
    )

    assert result["current_total"] == 150.0
    assert result["previous_total"] == 100.0
    assert result["pct_change"] == 50.0


# ---------------------------------------------------------------------------
# 13. Empty date range → empty trend, zeros, no pct_change
# ---------------------------------------------------------------------------

def test_get_trend_empty_range_returns_empty_trend(in_memory_db):
    """No transactions in range → empty trend, zeroed totals, pct_change=None."""
    result = trend_service.get_trend(
        db=in_memory_db,
        user_id=1,
        granularity="monthly",
        date_from=date(2020, 1, 1),
        date_to=date(2020, 12, 31),
        payment_source=None,
    )

    assert result["trend"] == []
    assert result["current_total"] == 0.0
    assert result["previous_total"] == 0.0
    assert result["pct_change"] is None
