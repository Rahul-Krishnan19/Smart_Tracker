from __future__ import annotations
"""
Gmail service — OAuth2 flow + fetching and decoding transaction emails.
Tokens are encrypted at rest using CryptoService before storing in DB.
Only reads emails (gmail.readonly scope).
"""
import base64
import json
import re
from datetime import datetime, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.services.crypto_service import crypto_service

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_FALLBACK_PATTERNS = [
    "hdfcbank.com", "hdfc.com", "hdfcbank.bank.in",
    "icicibank.com", "alerts.sbi.bank.in",
]


def build_gmail_query(sender_patterns: list[str]) -> str:
    """Build a Gmail search query from a list of sender patterns."""
    patterns = sender_patterns or _FALLBACK_PATTERNS
    from_clause = " OR ".join(patterns)
    return f"from:({from_clause}) newer_than:90d"


def _build_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


class GmailService:

    def get_auth_url(self) -> str:
        """Generate the Google OAuth2 authorization URL."""
        flow = _build_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code(self, code: str) -> str:
        """Exchange auth code for tokens. Returns encrypted token JSON string."""
        flow = _build_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }
        return crypto_service.encrypt(json.dumps(token_data))

    def _get_credentials(self, encrypted_token: str) -> tuple[Credentials, str | None]:
        """
        Decrypt stored token and return (creds, new_encrypted_or_None).
        If the token was refreshed, new_encrypted is the re-encrypted refreshed token
        that the caller must persist back to user.gmail_token_encrypted.
        If no refresh was needed, new_encrypted is None.
        """
        token_data = json.loads(crypto_service.decrypt(encrypted_token))
        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data.get("scopes", SCOPES),
        )
        new_encrypted = None
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                refreshed_data = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else SCOPES,
                }
                new_encrypted = crypto_service.encrypt(json.dumps(refreshed_data))
            except Exception as e:
                raise RuntimeError(
                    f"Gmail token expired and refresh failed: {e}. "
                    "Please disconnect and reconnect Gmail."
                )
        return creds, new_encrypted

    def _get_service(self, encrypted_token: str):
        creds, _ = self._get_credentials(encrypted_token)
        return build("gmail", "v1", credentials=creds)

    def fetch_transaction_emails(
        self,
        encrypted_token: str,
        max_results: int = 200,
        page_token: Optional[str] = None,
        sender_patterns: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Fetch transaction emails from Gmail.
        Returns list of dicts with: id, sender, subject, date, body, snippet.
        """
        service = self._get_service(encrypted_token)
        results = []
        query = build_gmail_query(sender_patterns or [])

        try:
            params = {
                "userId": "me",
                "q": query,
                "maxResults": max_results,
            }
            if page_token:
                params["pageToken"] = page_token

            response = service.users().messages().list(**params).execute()
            messages = response.get("messages", [])

            for msg_ref in messages:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="full",
                ).execute()
                parsed = self._extract_email_data(msg)
                if parsed:
                    results.append(parsed)

        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Gmail sync failed: {e}")

        return results

    def _extract_email_data(self, msg: dict) -> Optional[dict]:
        """Extract sender, subject, date, and body text from a Gmail message."""
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

        sender = headers.get("From", "")
        subject = headers.get("Subject", "")
        date_str = headers.get("Date", "")
        msg_id = msg["id"]

        body = self._extract_body(msg["payload"])
        if not body:
            return None

        # Parse email date
        received_at = None
        if msg.get("internalDate"):
            ts = int(msg["internalDate"]) / 1000
            received_at = datetime.fromtimestamp(ts, tz=timezone.utc)

        return {
            "id": msg_id,
            "sender": sender,
            "subject": subject,
            "date_str": date_str,
            "received_at": received_at,
            "body": body,
            "snippet": msg.get("snippet", ""),
        }

    def _extract_body(self, payload: dict) -> str:
        """Recursively extract plain text body from Gmail message payload."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        if mime_type == "text/html":
            data = payload.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                # Strip HTML tags for plain text
                return re.sub(r'<[^>]+>', ' ', html)

        # Multipart — recurse into parts
        for part in payload.get("parts", []):
            text = self._extract_body(part)
            if text and text.strip():
                return text

        return ""


gmail_service = GmailService()
