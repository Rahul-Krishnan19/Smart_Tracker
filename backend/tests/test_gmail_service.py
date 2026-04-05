"""
Tests for GmailService._get_credentials() — GMAIL-05: token refresh returns tuple.

RED phase: these tests are written to verify the fixed behaviour.
They will FAIL against the current code (which returns Credentials directly).
After Task 2 GREEN phase, all 3 tests pass.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.gmail_service import GmailService, SCOPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token_json(expired: bool = False, has_refresh: bool = True) -> str:
    return json.dumps({
        "token": "access_token_value",
        "refresh_token": "refresh_token_value" if has_refresh else None,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "client_id_value",
        "client_secret": "client_secret_value",
        "scopes": SCOPES,
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_credentials_returns_tuple():
    """
    _get_credentials() with a non-expired token returns a 2-tuple (creds, None).
    Second element is None because no refresh was needed.
    """
    service = GmailService()
    token_json = _make_token_json(expired=False)

    mock_creds = MagicMock()
    mock_creds.expired = False
    mock_creds.refresh_token = "refresh_token_value"

    with patch(
        "app.services.gmail_service.crypto_service.decrypt",
        return_value=token_json,
    ), patch(
        "app.services.gmail_service.Credentials",
        return_value=mock_creds,
    ):
        result = service._get_credentials("fake_encrypted")

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected tuple of length 2, got {len(result)}"
    creds, new_token = result
    assert new_token is None, f"Expected None for non-expired token, got {new_token!r}"


def test_get_credentials_refreshes_expired_token():
    """
    _get_credentials() with an expired token refreshes and returns (creds, new_encrypted_string).
    The second element is the re-encrypted refreshed token (non-None string).
    """
    service = GmailService()
    token_json = _make_token_json(expired=True, has_refresh=True)

    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token_value"
    mock_creds.token = "new_access_token"
    mock_creds.token_uri = "https://oauth2.googleapis.com/token"
    mock_creds.client_id = "client_id_value"
    mock_creds.client_secret = "client_secret_value"
    mock_creds.scopes = SCOPES
    # refresh() does nothing (mock success)
    mock_creds.refresh = MagicMock()

    with patch(
        "app.services.gmail_service.crypto_service.decrypt",
        return_value=token_json,
    ), patch(
        "app.services.gmail_service.Credentials",
        return_value=mock_creds,
    ), patch(
        "app.services.gmail_service.crypto_service.encrypt",
        return_value="new_encrypted_token",
    ):
        result = service._get_credentials("fake_encrypted")

    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2
    creds, new_token = result
    assert new_token is not None, "Expected non-None new_token after refresh"
    assert isinstance(new_token, str), f"Expected str, got {type(new_token)}"
    assert new_token == "new_encrypted_token"


def test_get_credentials_refresh_failure_raises():
    """
    _get_credentials() raises RuntimeError when token refresh fails.
    """
    service = GmailService()
    token_json = _make_token_json(expired=True, has_refresh=True)

    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token_value"
    mock_creds.refresh = MagicMock(side_effect=Exception("Token refresh failed"))

    with patch(
        "app.services.gmail_service.crypto_service.decrypt",
        return_value=token_json,
    ), patch(
        "app.services.gmail_service.Credentials",
        return_value=mock_creds,
    ):
        with pytest.raises(RuntimeError) as exc_info:
            service._get_credentials("fake_encrypted")

    assert "refresh failed" in str(exc_info.value).lower() or "expired" in str(exc_info.value).lower()
