"""
Tests for EmailSyncService.

These tests verify refactored sync service behaviour from Plan 02:
  - unmatched counter in summary dict (emails with no matching parser)
  - parse_failed counter tracks only actual parse errors, not unmatched

Tests will FAIL (RED) until Plan 02 refactors the sync service.
"""
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest

from app.services.email_sync_service import EmailSyncService


def _make_email(msg_id="test_id"):
    return {
        "id": msg_id,
        "sender": "unknown@unknown.com",
        "subject": "Unknown",
        "body": "Some email body",
        "received_at": datetime(2026, 4, 1, 12, 0, 0),
    }


def test_unmatched_counter(in_memory_db):
    """
    When no parser matches an email, summary['unmatched'] increments
    and summary['parse_failed'] stays 0.
    """
    service = EmailSyncService()

    # The current sync service calls parse_email() from parser_factory.
    # After Plan 02 refactor, it calls get_parser() internally and tracks unmatched separately.
    # Mock: gmail returns 1 email, no parser matches (parse_email returns None)
    with patch(
        "app.services.email_sync_service.gmail_service.fetch_transaction_emails",
        return_value=[_make_email("msg_unmatched_1")],
    ), patch(
        "app.services.email_sync_service.parse_email",
        return_value=None,
    ):
        summary = service.sync(
            db=in_memory_db,
            user_id=1,
            encrypted_token="fake_token",
            max_emails=1,
        )

    assert summary.get("unmatched", None) is not None, (
        "Expected 'unmatched' key in summary dict — Plan 02 adds this counter"
    )
    assert summary["unmatched"] == 1, f"Expected unmatched=1, got {summary['unmatched']}"
    assert summary["parse_failed"] == 0, (
        f"Expected parse_failed=0 for unmatched (no parse error occurred), "
        f"got {summary['parse_failed']}"
    )


def test_parse_failed_counter(in_memory_db):
    """
    When parse_email raises an exception, summary['parse_failed'] increments
    and summary['unmatched'] stays 0.
    """
    service = EmailSyncService()

    def _raise(*args, **kwargs):
        raise ValueError("Malformed email body")

    with patch(
        "app.services.email_sync_service.gmail_service.fetch_transaction_emails",
        return_value=[_make_email("msg_fail_1")],
    ), patch(
        "app.services.email_sync_service.parse_email",
        side_effect=_raise,
    ):
        summary = service.sync(
            db=in_memory_db,
            user_id=1,
            encrypted_token="fake_token",
            max_emails=1,
        )

    assert summary["parse_failed"] == 1, f"Expected parse_failed=1, got {summary['parse_failed']}"
    assert summary.get("unmatched", 0) == 0, (
        f"Expected unmatched=0 for a parse exception (not an unmatched email), "
        f"got {summary.get('unmatched')}"
    )


@pytest.mark.skip(reason="Awaiting INFRA-03 fix in Plan 01 Task 2")
def test_retention_days_from_settings(in_memory_db):
    """
    INFRA-03: email_sync_service uses settings.email_retention_days, not hardcoded 30.
    Patch settings.email_retention_days to 60 and assert delete_after is ~60 days from now.
    """
    pass
