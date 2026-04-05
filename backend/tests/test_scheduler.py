"""
Test stubs for Phase 4 APScheduler jobs — Plans 02+.

These stubs ensure the full Phase 4 test suite is declared upfront (Nyquist compliance).
All tests are skipped until Plan 02 implements the scheduler.
"""
import pytest


@pytest.mark.skip(reason="Awaiting scheduler implementation in Plan 02")
def test_sync_user_emails_calls_sync_service():
    """GMAIL-06: Scheduler job calls email_sync_service.sync() for the target user."""
    pass


@pytest.mark.skip(reason="Awaiting scheduler implementation in Plan 02")
def test_sync_job_catches_exception():
    """GMAIL-08: Scheduler job catches exceptions, logs error, does not re-raise."""
    pass


@pytest.mark.skip(reason="Awaiting scheduler implementation in Plan 02")
def test_cleanup_expired_emails():
    """INFRA-04: Daily cleanup job deletes EmailMetadata rows past their delete_after date."""
    pass


@pytest.mark.skip(reason="Awaiting scheduler implementation in Plan 02")
def test_register_sync_job():
    """Scheduler registers a job for a user with sync_enabled=True on startup."""
    pass
