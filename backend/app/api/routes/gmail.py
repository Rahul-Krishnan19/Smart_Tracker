"""
Gmail OAuth2 + email sync routes.

Flow:
  GET  /api/gmail/auth-url   → returns Google OAuth URL
  GET  /api/gmail/callback   → handles redirect from Google, stores encrypted token
  POST /api/gmail/sync       → fetches + parses transaction emails
  GET  /api/gmail/status     → returns connection status
  PUT  /api/gmail/settings   → update auto-sync settings
  DELETE /api/gmail/disconnect → removes stored token
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.services.gmail_service import gmail_service
from app.services.email_sync_service import email_sync_service
from app.scheduler import register_sync_job, unregister_sync_job

router = APIRouter()


class CodeExchange(BaseModel):
    code: str


class SyncSettingsUpdate(BaseModel):
    sync_enabled: bool
    sync_interval_hours: Optional[int] = None


@router.post("/exchange")
def exchange_code(
    body: CodeExchange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Frontend calls this with the OAuth code after Google redirects back."""
    try:
        encrypted_token = gmail_service.exchange_code(body.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")
    current_user.gmail_token_encrypted = encrypted_token
    db.commit()
    return {"status": "connected"}


@router.get("/auth-url")
def get_auth_url(current_user: User = Depends(get_current_user)):
    """Return the Google OAuth2 authorization URL for the frontend to redirect to."""
    if not gmail_service:
        raise HTTPException(status_code=503, detail="Gmail integration not configured")
    url = gmail_service.get_auth_url()
    return {"auth_url": url}


@router.get("/callback")
def oauth_callback(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Handle the OAuth2 redirect from Google.
    Exchanges code for tokens, encrypts and stores them.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        encrypted_token = gmail_service.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")

    current_user.gmail_token_encrypted = encrypted_token
    db.commit()

    # Redirect to frontend after successful connection
    return RedirectResponse(url="http://localhost:3000/transactions?gmail=connected")


@router.get("/status")
def gmail_status(current_user: User = Depends(get_current_user)):
    """Return whether Gmail is connected for the current user."""
    return {
        "connected": current_user.gmail_token_encrypted is not None,
        "user": current_user.username,
        "last_synced_at": current_user.last_synced_at.isoformat() if current_user.last_synced_at else None,
        "sync_enabled": current_user.sync_enabled,
        "sync_interval_hours": current_user.sync_interval_hours,
    }


@router.post("/sync")
def sync_emails(
    max_emails: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch transaction emails from Gmail, parse them, and save new transactions."""
    if not current_user.gmail_token_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Gmail not connected. Please connect Gmail first."
        )

    try:
        # Check for token refresh and persist if needed (GMAIL-05)
        creds, new_token = gmail_service._get_credentials(current_user.gmail_token_encrypted)
        if new_token is not None:
            current_user.gmail_token_encrypted = new_token
            db.commit()

        summary = email_sync_service.sync(
            db=db,
            user_id=current_user.id,
            encrypted_token=current_user.gmail_token_encrypted,
            max_emails=max_emails,
        )

        # Update last_synced_at after successful sync (D-10)
        current_user.last_synced_at = datetime.now(timezone.utc)
        db.commit()

    except (RuntimeError, Exception) as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "status": "done",
        "emails_fetched": summary["fetched"],
        "skipped_duplicate": summary["skipped_duplicate"],
        "parsed_ok": summary["parsed_ok"],
        "parse_failed": summary["parse_failed"],
        "unmatched": summary["unmatched"],
        "transactions_created": summary["transactions_created"],
    }


@router.put("/settings")
def update_sync_settings(
    body: SyncSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GMAIL-10: Update auto-sync settings. Per D-05, D-07."""
    if body.sync_enabled and (not body.sync_interval_hours or body.sync_interval_hours < 1):
        raise HTTPException(
            status_code=422,
            detail="sync_interval_hours must be >= 1 when sync is enabled",
        )
    current_user.sync_enabled = body.sync_enabled
    current_user.sync_interval_hours = body.sync_interval_hours if body.sync_enabled else None
    db.commit()

    if body.sync_enabled:
        register_sync_job(current_user.id, body.sync_interval_hours)
    else:
        unregister_sync_job(current_user.id)

    return {
        "status": "ok",
        "sync_enabled": current_user.sync_enabled,
        "sync_interval_hours": current_user.sync_interval_hours,
    }


@router.delete("/disconnect")
def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove stored Gmail token (disconnect account)."""
    current_user.gmail_token_encrypted = None
    db.commit()
    return {"status": "disconnected"}
