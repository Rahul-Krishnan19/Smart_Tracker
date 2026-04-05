"""Tests for backend/app/scheduler.py — scheduler job functions."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


class TestSyncUserEmails:
    """GMAIL-06, GMAIL-08: Per-user sync job function."""

    @patch("app.scheduler.email_sync_service")
    @patch("app.scheduler.gmail_service")
    @patch("app.scheduler.SessionLocal")
    def test_sync_user_emails_calls_sync_service(self, mock_session_cls, mock_gmail, mock_sync_svc):
        from app.scheduler import sync_user_emails
        # Setup mock DB session and user
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.gmail_token_encrypted = "enc_token"
        mock_user.sync_enabled = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_gmail._get_credentials.return_value = (MagicMock(), None)  # no refresh
        mock_sync_svc.sync.return_value = {"fetched": 0, "transactions_created": 0}

        sync_user_emails(1)

        mock_sync_svc.sync.assert_called_once()
        assert mock_user.last_synced_at is not None

    @patch("app.scheduler.email_sync_service")
    @patch("app.scheduler.gmail_service")
    @patch("app.scheduler.SessionLocal")
    def test_sync_user_emails_persists_refreshed_token(self, mock_session_cls, mock_gmail, mock_sync_svc):
        from app.scheduler import sync_user_emails
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.gmail_token_encrypted = "old_token"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_gmail._get_credentials.return_value = (MagicMock(), "new_encrypted_token")
        mock_sync_svc.sync.return_value = {"fetched": 0}

        sync_user_emails(1)

        assert mock_user.gmail_token_encrypted == "new_encrypted_token"
        assert mock_db.commit.call_count >= 1  # at least one commit for token persist

    @patch("app.scheduler.SessionLocal")
    def test_sync_job_catches_exception(self, mock_session_cls):
        """GMAIL-08: Job must not re-raise — scheduler must not crash."""
        from app.scheduler import sync_user_emails
        mock_db = MagicMock()
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.query.side_effect = Exception("DB connection lost")

        # Must NOT raise
        sync_user_emails(1)  # should log error but return normally


class TestCleanupExpiredEmails:
    """INFRA-04: Daily cleanup of expired EmailMetadata."""

    def test_cleanup_job(self, in_memory_db):
        from app.models.email_metadata import EmailMetadata
        from app.models.user import User
        # Insert a user to satisfy FK constraint
        user = User(id=1, username="test", email="t@t.com", password_hash="x")
        in_memory_db.add(user)
        in_memory_db.commit()

        now = datetime.now(timezone.utc)
        # Insert expired row
        expired = EmailMetadata(
            user_id=1, gmail_message_id="exp1", parse_status="success",
            delete_after=now - timedelta(days=1),
        )
        # Insert not-yet-expired row
        fresh = EmailMetadata(
            user_id=1, gmail_message_id="fresh1", parse_status="success",
            delete_after=now + timedelta(days=10),
        )
        in_memory_db.add_all([expired, fresh])
        in_memory_db.commit()

        # Need to patch SessionLocal to return the in_memory_db
        with patch("app.scheduler.SessionLocal") as mock_sl:
            mock_sl.return_value.__enter__ = MagicMock(return_value=in_memory_db)
            mock_sl.return_value.__exit__ = MagicMock(return_value=False)
            from app.scheduler import cleanup_expired_emails
            cleanup_expired_emails()

        remaining = in_memory_db.query(EmailMetadata).all()
        assert len(remaining) == 1
        assert remaining[0].gmail_message_id == "fresh1"


class TestJobRegistration:
    """Scheduler job add/remove helpers."""

    @patch("app.scheduler.scheduler")
    def test_register_sync_job(self, mock_sched):
        from app.scheduler import register_sync_job
        register_sync_job(42, 12)
        mock_sched.add_job.assert_called_once()
        call_kwargs = mock_sched.add_job.call_args
        assert call_kwargs.kwargs["id"] == "gmail_sync_user_42"
        assert call_kwargs.kwargs["replace_existing"] is True

    @patch("app.scheduler.scheduler")
    def test_unregister_sync_job(self, mock_sched):
        from app.scheduler import unregister_sync_job
        mock_sched.get_job.return_value = MagicMock()  # job exists
        unregister_sync_job(42)
        mock_sched.remove_job.assert_called_once_with("gmail_sync_user_42")
