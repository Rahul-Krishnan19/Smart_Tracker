"""Tests for AnomalyService — 7 behavioral tests per plan 07-02 Task 1."""
from datetime import datetime, date, timedelta
import pytest

from app.models.user import User
from app.models.transaction import Transaction
from app.models.subscription import Subscription
from app.services.anomaly_service import AnomalyService
from app.services import insights_config as cfg


def make_user(db, username="testuser"):
    u = User(username=username, email=f"{username}@test.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def make_tx(db, user_id, amount, merchant="Shop", category="Food & Dining",
            tx_date=None, description="test tx"):
    if tx_date is None:
        tx_date = date.today()
    tx = Transaction(
        user_id=user_id,
        transaction_date=tx_date,
        amount=amount,
        description=description,
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
    return AnomalyService()


def test_high_value(db, svc):
    """Test 1: amount > ANOMALY_HIGH_VALUE_THRESHOLD creates high_value anomaly."""
    u = make_user(db)
    tx = make_tx(db, u.id, 6000)
    db.commit()

    anomalies = svc.detect(db, u.id)
    hv = [a for a in anomalies if a.rule_name == "high_value"]
    assert len(hv) == 1
    assert hv[0].transaction_id == tx.id
    assert hv[0].severity == cfg.ANOMALY_SEVERITY["high_value"]
    assert hv[0].status == "new"


def test_large_transaction_with_history(db, svc):
    """Test 2a: >=2 months history, amount > 3x avg triggers large_transaction."""
    u = make_user(db)
    # Create history: avg 500 in Food & Dining over 2+ months
    today = date.today()
    m2 = (today - timedelta(days=70)).replace(day=15)
    m3 = (today - timedelta(days=40)).replace(day=15)
    make_tx(db, u.id, 500, category="Food & Dining", tx_date=m2)
    make_tx(db, u.id, 500, category="Food & Dining", tx_date=m3)
    # New big transaction: 2000 > 3.0 * 500
    big_tx = make_tx(db, u.id, 2000, category="Food & Dining", tx_date=today)
    db.commit()

    now = datetime.combine(today, datetime.min.time()).replace(hour=12)
    anomalies = svc.detect(db, u.id, now=now)
    lt = [a for a in anomalies if a.rule_name == "large_transaction"]
    assert len(lt) >= 1
    assert any(a.transaction_id == big_tx.id for a in lt)
    assert lt[0].severity == cfg.ANOMALY_SEVERITY["large_transaction"]


def test_large_transaction_no_history(db, svc):
    """Test 2b: <2 months history, large_transaction does NOT fire."""
    u = make_user(db)
    today = date.today()
    # Only 1 month history
    m1 = (today - timedelta(days=20)).replace(day=15)
    make_tx(db, u.id, 500, category="Food & Dining", tx_date=m1)
    make_tx(db, u.id, 2000, category="Food & Dining", tx_date=today)
    db.commit()

    now = datetime.combine(today, datetime.min.time()).replace(hour=12)
    anomalies = svc.detect(db, u.id, now=now)
    lt = [a for a in anomalies if a.rule_name == "large_transaction"]
    assert len(lt) == 0


def test_velocity_spike_same_merchant(db, svc):
    """Test 3: 3 tx at same merchant within 24h creates exactly ONE velocity_spike anomaly."""
    u = make_user(db)
    today = date.today()
    for _ in range(3):
        make_tx(db, u.id, 100, merchant="Swiggy", tx_date=today)
    db.commit()

    now = datetime.combine(today, datetime.min.time()).replace(hour=12)
    anomalies = svc.detect(db, u.id, now=now)
    vs = [a for a in anomalies if a.rule_name == "velocity_spike"]
    assert len(vs) == 1
    assert vs[0].severity == cfg.ANOMALY_SEVERITY["velocity_spike"]


def test_duplicate_like(db, svc):
    """Test 4: Two tx with same merchant + same amount within 48h -> duplicate_like on second."""
    u = make_user(db)
    today = date.today()
    yesterday = today - timedelta(days=1)
    make_tx(db, u.id, 500, merchant="Amazon", tx_date=yesterday)
    tx2 = make_tx(db, u.id, 500, merchant="Amazon", tx_date=today)
    db.commit()

    now = datetime.combine(today, datetime.min.time()).replace(hour=12)
    anomalies = svc.detect(db, u.id, now=now)
    dl = [a for a in anomalies if a.rule_name == "duplicate_like"]
    assert len(dl) >= 1
    assert any(a.transaction_id == tx2.id for a in dl)
    assert dl[0].severity == cfg.ANOMALY_SEVERITY["duplicate_like"]


def test_idempotency(db, svc):
    """Test 5: Calling detect() twice does not duplicate anomalies."""
    u = make_user(db)
    make_tx(db, u.id, 6000)
    db.commit()

    now = datetime.utcnow()
    first = svc.detect(db, u.id, now=now)
    second = svc.detect(db, u.id, now=now)

    from app.models.anomaly import Anomaly
    count = db.query(Anomaly).filter(
        Anomaly.user_id == u.id,
        Anomaly.status == "new"
    ).count()
    # Must not have doubled
    assert count == len([a for a in first if a is not None])


def test_missing_subscription_after_trigger_day(db, svc):
    """Test 6a: Active subscription with no tx this month + day>=10 -> missing_subscription."""
    u = make_user(db)
    today = date.today()
    first_m = date(today.year - 1, today.month, 1)
    last_m = date(today.year, today.month - 1 if today.month > 1 else 12, 1)
    sub = Subscription(
        user_id=u.id, merchant="Netflix", typical_amount=499,
        status="active", first_seen_month=first_m, last_seen_month=last_m
    )
    db.add(sub)
    db.commit()

    # Mock day=15 (> MISSING_SUBSCRIPTION_TRIGGER_DAY=10)
    mocked_now = datetime(today.year, today.month, 15, 12, 0, 0)
    anomalies = svc.detect(db, u.id, now=mocked_now)
    ms = [a for a in anomalies if a.rule_name == "missing_subscription"]
    assert len(ms) == 1
    assert ms[0].transaction_id is None
    assert ms[0].severity == cfg.ANOMALY_SEVERITY["missing_subscription"]


def test_missing_subscription_before_trigger_day(db, svc):
    """Test 6b: Active subscription but day < MISSING_SUBSCRIPTION_TRIGGER_DAY -> NO anomaly."""
    u = make_user(db)
    today = date.today()
    first_m = date(today.year - 1, today.month, 1)
    last_m = date(today.year, today.month - 1 if today.month > 1 else 12, 1)
    sub = Subscription(
        user_id=u.id, merchant="Netflix", typical_amount=499,
        status="active", first_seen_month=first_m, last_seen_month=last_m
    )
    db.add(sub)
    db.commit()

    # Mock day=5 (< MISSING_SUBSCRIPTION_TRIGGER_DAY=10)
    mocked_now = datetime(today.year, today.month, 5, 12, 0, 0)
    anomalies = svc.detect(db, u.id, now=mocked_now)
    ms = [a for a in anomalies if a.rule_name == "missing_subscription"]
    assert len(ms) == 0


def test_velocity_spike_daily_spend(db, svc):
    """Test 7: Daily total > ANOMALY_DAILY_SPEND_MULTIPLIER x rolling avg fires velocity_spike."""
    u = make_user(db)
    today = date.today()

    # Create 31 days of history (enough for history_days // 2 check)
    # Each day: spend ~1000 on average
    history_days = cfg.ANOMALY_MIN_HISTORY_MONTHS * 30  # 60 days
    for i in range(history_days):
        d = today - timedelta(days=history_days - i)
        make_tx(db, u.id, 1000, category="Others", tx_date=d)
    db.commit()

    # Today's spend: 5000 > 3.0 * 1000 = 3000
    big_tx = make_tx(db, u.id, 5000, category="Others", tx_date=today)
    db.commit()

    now = datetime.combine(today, datetime.min.time()).replace(hour=12)
    anomalies = svc.detect(db, u.id, now=now)
    vs = [a for a in anomalies if a.rule_name == "velocity_spike"]
    assert len(vs) >= 1
    # At least one anchored on today's big tx
    assert any(a.transaction_id == big_tx.id for a in vs)
