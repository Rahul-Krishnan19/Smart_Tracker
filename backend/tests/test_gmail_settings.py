"""Tests for PUT /api/gmail/settings and GET /api/gmail/status extensions."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestPutSyncSettings:
    """GMAIL-10: User-configurable sync schedule."""

    @patch("app.api.routes.gmail.unregister_sync_job")
    @patch("app.api.routes.gmail.register_sync_job")
    def test_put_settings_enables_sync(self, mock_reg, mock_unreg):
        from app.api.routes.gmail import update_sync_settings, SyncSettingsUpdate
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.sync_enabled = False
        mock_db = MagicMock()

        body = SyncSettingsUpdate(sync_enabled=True, sync_interval_hours=12)
        result = update_sync_settings(body=body, current_user=mock_user, db=mock_db)

        assert mock_user.sync_enabled is True
        assert mock_user.sync_interval_hours == 12
        mock_reg.assert_called_once_with(1, 12)
        mock_unreg.assert_not_called()
        mock_db.commit.assert_called()

    @patch("app.api.routes.gmail.unregister_sync_job")
    @patch("app.api.routes.gmail.register_sync_job")
    def test_put_settings_disables_sync(self, mock_reg, mock_unreg):
        from app.api.routes.gmail import update_sync_settings, SyncSettingsUpdate
        mock_user = MagicMock()
        mock_user.id = 1
        mock_db = MagicMock()

        body = SyncSettingsUpdate(sync_enabled=False)
        result = update_sync_settings(body=body, current_user=mock_user, db=mock_db)

        assert mock_user.sync_enabled is False
        mock_unreg.assert_called_once_with(1)
        mock_reg.assert_not_called()

    def test_put_settings_rejects_invalid_interval(self):
        from app.api.routes.gmail import update_sync_settings, SyncSettingsUpdate
        from fastapi import HTTPException
        mock_user = MagicMock()
        mock_user.id = 1
        mock_db = MagicMock()

        body = SyncSettingsUpdate(sync_enabled=True, sync_interval_hours=0)
        with pytest.raises(HTTPException) as exc_info:
            update_sync_settings(body=body, current_user=mock_user, db=mock_db)
        assert exc_info.value.status_code == 422


class TestStatusExtended:
    """GMAIL-07: Status endpoint includes sync fields."""

    def test_status_includes_last_synced_at(self):
        from app.api.routes.gmail import gmail_status
        mock_user = MagicMock()
        mock_user.gmail_token_encrypted = "some_token"
        mock_user.username = "testuser"
        mock_user.last_synced_at = datetime(2026, 4, 5, 10, 0, 0, tzinfo=timezone.utc)
        mock_user.sync_enabled = True
        mock_user.sync_interval_hours = 24

        result = gmail_status(current_user=mock_user)

        assert "last_synced_at" in result
        assert result["last_synced_at"] is not None
        assert result["sync_enabled"] is True
        assert result["sync_interval_hours"] == 24

    def test_status_last_synced_at_null_when_never_synced(self):
        from app.api.routes.gmail import gmail_status
        mock_user = MagicMock()
        mock_user.gmail_token_encrypted = "some_token"
        mock_user.username = "testuser"
        mock_user.last_synced_at = None
        mock_user.sync_enabled = False
        mock_user.sync_interval_hours = None

        result = gmail_status(current_user=mock_user)

        assert result["last_synced_at"] is None
