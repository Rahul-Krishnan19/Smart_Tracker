"""Tests for SubscriptionService — S1-S4 per plan 07-02 Task 2."""
from datetime import date, datetime
import pytest

from app.models.user import User
from app.models.transaction import Transaction
from app.models.subscription import Subscription
from app.services.subscription_service import SubscriptionService


def make_user(db, username="subuser"):
    u = User(username=username, email=f"{username}@test.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def make_tx(db, user_id, amount, merchant, tx_date):
    tx = Transaction(
        user_id=user_id,
        transaction_date=tx_date,
        amount=amount,
        description="sub tx",
        merchant=merchant,
        category="Subscriptions",
        payment_method="Credit Card",
        source="email",
    )
    db.add(tx)
    db.flush()
    return tx


@pytest.fixture
def db(in_memory_db):
    return in_memory_db


@pytest.fixture
def svc():
    return SubscriptionService()


def test_s1_consecutive_months_creates_subscription(db, svc):
    """S1: Netflix 499 in March and April -> one active Subscription."""
    u = make_user(db)
    make_tx(db, u.id, 499, "Netflix", date(2026, 3, 15))
    make_tx(db, u.id, 499, "Netflix", date(2026, 4, 15))
    db.commit()

    results = svc.detect(db, u.id)
    netflix_subs = [s for s in results if s.merchant == "Netflix"]
    assert len(netflix_subs) == 1
    sub = netflix_subs[0]
    assert sub.status == "active"
    assert float(sub.typical_amount) == 499.0


def test_s2_too_many_distinct_amounts_per_month(db, svc):
    """S2: Swiggy with 6 distinct amounts in March alone -> NO subscription."""
    u = make_user(db)
    for amount in [100, 200, 300, 400, 500, 600]:
        make_tx(db, u.id, amount, "Swiggy", date(2026, 3, 10))
    db.commit()

    results = svc.detect(db, u.id)
    swiggy_subs = [s for s in results if s.merchant == "Swiggy"]
    assert len(swiggy_subs) == 0


def test_s3_reactivates_canceled_subscription(db, svc):
    """S3: Canceled subscription for Netflix re-activates when new charges detected in 2 consecutive months."""
    u = make_user(db)
    # Insert canceled subscription record
    existing = Subscription(
        user_id=u.id, merchant="Netflix", typical_amount=499,
        status="canceled", first_seen_month=date(2025, 1, 1),
        last_seen_month=date(2025, 6, 1),
        canceled_at=datetime(2025, 7, 1)
    )
    db.add(existing)
    # New charges in recent months
    make_tx(db, u.id, 499, "Netflix", date(2026, 3, 15))
    make_tx(db, u.id, 499, "Netflix", date(2026, 4, 15))
    db.commit()

    results = svc.detect(db, u.id)
    netflix_subs = [s for s in results if s.merchant == "Netflix"]
    assert len(netflix_subs) == 1
    sub = netflix_subs[0]
    assert sub.status == "active"
    assert sub.canceled_at is None


def test_s4_idempotent_no_duplicates(db, svc):
    """S4: Running detect() twice does not create duplicate subscriptions."""
    u = make_user(db)
    make_tx(db, u.id, 499, "Netflix", date(2026, 3, 15))
    make_tx(db, u.id, 499, "Netflix", date(2026, 4, 15))
    db.commit()

    svc.detect(db, u.id)
    svc.detect(db, u.id)

    count = db.query(Subscription).filter(
        Subscription.user_id == u.id,
        Subscription.merchant == "Netflix"
    ).count()
    assert count == 1
