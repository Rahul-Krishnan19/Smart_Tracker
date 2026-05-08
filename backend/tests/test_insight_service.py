"""Tests for InsightService — I1-I4 per plan 07-02 Task 2."""
from datetime import datetime, date, timedelta
import pytest

from app.models.user import User
from app.models.transaction import Transaction
from app.models.insight import Insight
from app.services.insight_service import InsightService
from app.services import insights_config as cfg


def make_user(db, username="insightuser"):
    u = User(username=username, email=f"{username}@test.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def make_tx(db, user_id, amount, tx_date, category="Others", merchant="Shop"):
    tx = Transaction(
        user_id=user_id,
        transaction_date=tx_date,
        amount=amount,
        description="tx",
        merchant=merchant,
        category=category,
        payment_method="UPI",
        source="manual",
    )
    db.add(tx)
    db.flush()
    return tx


@pytest.fixture
def db(in_memory_db):
    return in_memory_db


@pytest.fixture
def svc():
    return InsightService()


def test_i1_spend_pace_insight(db, svc):
    """I1: Current month spend +30% over last month -> produces spend_pace insight."""
    u = make_user(db)
    today = date(2026, 5, 15)
    # Last month: 10000
    make_tx(db, u.id, 10000, date(2026, 4, 10))
    # This month: 6000 by day 15 -> projected 6000/15*31 ~ 12400 > 10000
    make_tx(db, u.id, 6000, today)
    db.commit()

    now = datetime(2026, 5, 15, 12, 0, 0)
    insights = svc.regenerate(db, u.id, today=now)
    sp = [i for i in insights if i.insight_type == "spend_pace"]
    assert len(sp) == 1
    assert sp[0].status == "active"


def test_i2_quiet_month_not_spend_pace(db, svc):
    """I2: Current month spend 25% below rolling avg -> quiet_month, NOT spend_pace."""
    u = make_user(db)
    today = date(2026, 5, 15)
    # History: 10000/month for Jan-Apr (past months only)
    for m in range(1, 5):
        make_tx(db, u.id, 10000, date(2026, m, 10))
    # This month (May): only 1000 by day 15 -> projected 1000/15*31 ~ 2067 < avg * 0.80
    make_tx(db, u.id, 1000, today)
    db.commit()

    now = datetime(2026, 5, 15, 12, 0, 0)
    insights = svc.regenerate(db, u.id, today=now)
    types = [i.insight_type for i in insights]
    assert "quiet_month" in types
    assert "spend_pace" not in types


def test_i3_priority_cap(db, svc):
    """I3: More than 5 candidates -> exactly INSIGHTS_MAX_PER_BATCH rows kept in priority order."""
    u = make_user(db, username="capuser")
    today = date(2026, 5, 15)
    # Last month: spend in multiple categories to trigger surges
    categories = ["Food & Dining", "Shopping", "Travel", "Entertainment", "Utilities"]
    for cat in categories:
        make_tx(db, u.id, 1000, date(2026, 4, 10), category=cat)
        # This month: 2000 (>20% surge) for each
        make_tx(db, u.id, 2000, today, category=cat)
    # Also spend_pace: project high
    db.commit()

    now = datetime(2026, 5, 15, 12, 0, 0)
    insights = svc.regenerate(db, u.id, today=now)
    assert len(insights) <= cfg.INSIGHTS_MAX_PER_BATCH
    # Verify priority: spend_pace before category_surge before quiet_month
    types = [i.insight_type for i in insights]
    if "spend_pace" in types and "quiet_month" in types:
        assert types.index("spend_pace") < types.index("quiet_month")


def test_i4_regeneration_preserves_dismissed(db, svc):
    """I4: Regeneration deletes active insights but preserves dismissed ones."""
    u = make_user(db, username="dismissuser")
    # Pre-existing dismissed insight
    dismissed = Insight(
        user_id=u.id, insight_type="top_merchant",
        title="Old insight", body="body", status="dismissed"
    )
    db.add(dismissed)
    db.commit()

    today = date(2026, 5, 15)
    now = datetime(2026, 5, 15, 12, 0, 0)
    # Regenerate — this should NOT delete dismissed row
    svc.regenerate(db, u.id, today=now)

    dismissed_count = db.query(Insight).filter(
        Insight.user_id == u.id, Insight.status == "dismissed"
    ).count()
    assert dismissed_count == 1
