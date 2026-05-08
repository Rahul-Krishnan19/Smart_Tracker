"""Tests for insights_orchestrator and email_sync post-sync hook — O1-O3 per plan 07-02 Task 3."""
from datetime import date
from unittest.mock import patch, MagicMock
import pytest

from app.models.user import User
from app.models.transaction import Transaction
from app.services.insights_orchestrator import run_post_sync


def make_user(db, username="orchuser"):
    u = User(username=username, email=f"{username}@test.com", password_hash="x")
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def db(in_memory_db):
    return in_memory_db


def test_o1_run_post_sync_returns_counts(db):
    """O1: run_post_sync returns dict with subscriptions/anomalies/insights integer counts."""
    u = make_user(db)
    db.commit()

    result = run_post_sync(db, u.id)

    assert isinstance(result, dict)
    assert "subscriptions" in result
    assert "anomalies" in result
    assert "insights" in result
    assert isinstance(result["subscriptions"], int)
    assert isinstance(result["anomalies"], int)
    assert isinstance(result["insights"], int)


def test_o2_subscription_error_does_not_block(db):
    """O2: When subscription_service.detect raises, anomaly and insight services still run."""
    u = make_user(db)
    db.commit()

    with patch("app.services.insights_orchestrator.subscription_service.detect") as mock_sub:
        mock_sub.side_effect = RuntimeError("subscription boom")
        result = run_post_sync(db, u.id)

    # Should still complete
    assert result["subscriptions"] == 0
    # anomalies and insights keys must be present (they ran without error)
    assert "anomalies" in result
    assert "insights" in result


def test_o3_email_sync_embeds_insights_summary(db):
    """O3: email_sync_service.sync() returns summary with 'insights' key from run_post_sync."""
    from app.services.email_sync_service import EmailSyncService

    svc = EmailSyncService()

    # Mock gmail_service to return empty list (no real OAuth needed)
    with patch("app.services.email_sync_service.gmail_service.fetch_transaction_emails") as mock_fetch:
        mock_fetch.return_value = []
        u = make_user(db, username="syncuser")
        db.commit()

        summary = svc.sync(db, user_id=u.id, encrypted_token="fake-token")

    assert "insights" in summary
    insights_s = summary["insights"]
    assert isinstance(insights_s, dict)
    assert "subscriptions" in insights_s
    assert "anomalies" in insights_s
    assert "insights" in insights_s


def test_o3_sync_survives_insights_failure(db):
    """O3b: If run_post_sync raises entirely, sync() still returns successfully."""
    from app.services.email_sync_service import EmailSyncService

    svc = EmailSyncService()

    with patch("app.services.email_sync_service.gmail_service.fetch_transaction_emails") as mock_fetch, \
         patch("app.services.insights_orchestrator.run_post_sync") as mock_rps:
        mock_fetch.return_value = []
        mock_rps.side_effect = RuntimeError("orchestrator crash")
        u = make_user(db, username="survivesyncuser")
        db.commit()

        # Should not raise
        summary = svc.sync(db, user_id=u.id, encrypted_token="fake-token")

    assert "fetched" in summary
    # insights key may not be present if run_post_sync raised before assignment
    # but sync must still return a dict
    assert isinstance(summary, dict)
