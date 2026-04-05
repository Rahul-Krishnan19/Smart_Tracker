"""
Test stubs for PUT /api/gmail/settings route — Plan 02+.

These stubs ensure the full Phase 4 test suite is declared upfront (Nyquist compliance).
All tests are skipped until Plan 02 implements the settings route.
"""
import pytest


@pytest.mark.skip(reason="Awaiting settings route in Plan 02")
def test_put_settings_enables_sync():
    """GMAIL-10: PUT /api/gmail/settings with sync_enabled=True enables auto-sync."""
    pass


@pytest.mark.skip(reason="Awaiting settings route in Plan 02")
def test_put_settings_disables_sync():
    """GMAIL-10: PUT /api/gmail/settings with sync_enabled=False disables auto-sync."""
    pass


@pytest.mark.skip(reason="Awaiting settings route in Plan 02")
def test_put_settings_rejects_invalid_interval():
    """GMAIL-10: PUT /api/gmail/settings rejects sync_interval_hours < 1."""
    pass


@pytest.mark.skip(reason="Awaiting settings route in Plan 02")
def test_status_includes_last_synced_at():
    """GMAIL-07: GET /api/gmail/status response includes last_synced_at field."""
    pass
