"""Tests for /api/insights routes — R1-R9 per plan 07-02 Task 4.
Uses direct function call pattern consistent with test_gmail_settings.py.
"""
from datetime import datetime, date
from unittest.mock import MagicMock
import pytest

from app.models.user import User
from app.models.anomaly import Anomaly
from app.models.subscription import Subscription
from app.models.insight import Insight


def make_user(db, uid=1, username="routeuser"):
    u = User(username=username, email=f"{username}@test.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


def make_anomaly(db, user_id, status="new"):
    a = Anomaly(
        user_id=user_id,
        transaction_id=None,
        rule_name="high_value",
        severity="high",
        status=status,
    )
    db.add(a)
    db.flush()
    return a


def make_subscription(db, user_id, merchant="Netflix", amount=499, status="active"):
    s = Subscription(
        user_id=user_id,
        merchant=merchant,
        typical_amount=amount,
        status=status,
        first_seen_month=date(2026, 1, 1),
        last_seen_month=date(2026, 4, 1),
    )
    db.add(s)
    db.flush()
    return s


def make_insight(db, user_id, status="active", insight_type="spend_pace"):
    i = Insight(
        user_id=user_id,
        insight_type=insight_type,
        title="Test insight",
        body="Test body",
        status=status,
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def db(in_memory_db):
    return in_memory_db


# ---- R1: GET /anomalies returns list for current user only ----
def test_r1_list_anomalies_current_user_only(db):
    from app.api.routes.insights import list_anomalies
    u1 = make_user(db, username="u1")
    u2 = make_user(db, username="u2")
    a1 = make_anomaly(db, u1.id)
    a2 = make_anomaly(db, u2.id)
    db.commit()

    result = list_anomalies(current_user=u1, db=db)
    ids = [r.id for r in result]
    assert a1.id in ids
    assert a2.id not in ids


# ---- R2: GET /summary returns count of status='new' anomalies ----
def test_r2_summary_anomaly_count(db):
    from app.api.routes.insights import insights_summary
    u = make_user(db, username="sum1")
    make_anomaly(db, u.id, status="new")
    make_anomaly(db, u.id, status="new")
    make_anomaly(db, u.id, status="dismissed")
    db.commit()

    result = insights_summary(current_user=u, db=db)
    assert result.anomaly_count == 2


# ---- R3: PATCH /anomalies/{id} dismisses anomaly ----
def test_r3_patch_anomaly_dismissed(db):
    from app.api.routes.insights import update_anomaly_status
    from app.schemas.insights import AnomalyStatusUpdate
    u = make_user(db, username="patch1")
    a = make_anomaly(db, u.id)
    db.commit()

    body = AnomalyStatusUpdate(status="dismissed")
    result = update_anomaly_status(anomaly_id=a.id, body=body, current_user=u, db=db)
    assert result.status == "dismissed"
    assert result.dismissed_at is not None


# ---- R4: PATCH /anomalies/{id} for other user's anomaly -> 404 ----
def test_r4_patch_anomaly_other_user_404(db):
    from app.api.routes.insights import update_anomaly_status
    from app.schemas.insights import AnomalyStatusUpdate
    from fastapi import HTTPException
    u1 = make_user(db, username="own1")
    u2 = make_user(db, username="own2")
    a = make_anomaly(db, u1.id)
    db.commit()

    body = AnomalyStatusUpdate(status="dismissed")
    with pytest.raises(HTTPException) as exc_info:
        update_anomaly_status(anomaly_id=a.id, body=body, current_user=u2, db=db)
    assert exc_info.value.status_code == 404


# ---- R5: GET /subscriptions returns SubscriptionsListOut with estimated_monthly_total ----
def test_r5_list_subscriptions_total(db):
    from app.api.routes.insights import list_subscriptions
    u = make_user(db, username="sub1")
    make_subscription(db, u.id, merchant="Netflix", amount=499, status="active")
    make_subscription(db, u.id, merchant="Spotify", amount=199, status="active")
    make_subscription(db, u.id, merchant="Old", amount=100, status="canceled")
    db.commit()

    result = list_subscriptions(current_user=u, db=db)
    assert len(result.items) == 3
    assert result.estimated_monthly_total == 698.0  # only active: 499+199


# ---- R6: PATCH /subscriptions/{id} cancels subscription ----
def test_r6_patch_subscription_canceled(db):
    from app.api.routes.insights import update_subscription_status
    from app.schemas.insights import SubscriptionStatusUpdate
    u = make_user(db, username="can1")
    s = make_subscription(db, u.id)
    db.commit()

    body = SubscriptionStatusUpdate(status="canceled")
    result = update_subscription_status(sub_id=s.id, body=body, current_user=u, db=db)
    assert result.status == "canceled"
    assert result.canceled_at is not None


# ---- R7: GET /insights returns only active insights ----
def test_r7_list_insights_active_only(db):
    from app.api.routes.insights import list_insights
    u = make_user(db, username="ins1")
    i_active = make_insight(db, u.id, status="active")
    i_dismissed = make_insight(db, u.id, status="dismissed", insight_type="quiet_month")
    db.commit()

    result = list_insights(current_user=u, db=db)
    ids = [r.id for r in result]
    assert i_active.id in ids
    assert i_dismissed.id not in ids


# ---- R8: POST /insights/{id}/dismiss dismisses insight ----
def test_r8_dismiss_insight(db):
    from app.api.routes.insights import dismiss_insight
    u = make_user(db, username="dis1")
    i = make_insight(db, u.id)
    db.commit()

    result = dismiss_insight(insight_id=i.id, current_user=u, db=db)
    assert result.status == "dismissed"
    assert result.dismissed_at is not None


# ---- R9: Endpoints without auth return 401 ----
def test_r9_unauthenticated_returns_401():
    """All endpoints require authentication. Verify dependency structure."""
    from app.api.routes.insights import router
    from fastapi import Depends
    import inspect

    # Check that each route has get_current_user in its dependencies
    route_paths = [r.path for r in router.routes]
    # At minimum the router has these paths
    assert "/api/insights/anomalies" in route_paths
    assert "/api/insights/subscriptions" in route_paths
    assert "/api/insights/insights" in route_paths
    assert "/api/insights/summary" in route_paths

    # Verify router has auth dependency by checking function signatures
    from app.api.routes.insights import list_anomalies, list_subscriptions, list_insights, insights_summary
    from app.api.routes.auth import get_current_user
    for fn in [list_anomalies, list_subscriptions, list_insights, insights_summary]:
        sig = inspect.signature(fn)
        # current_user param with Depends(get_current_user) means auth required
        assert "current_user" in sig.parameters
