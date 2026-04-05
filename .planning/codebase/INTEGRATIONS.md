# External Integrations

_Generated: 2026-03-29_

## Summary

The only active external integration is Google OAuth2 + Gmail API, used to pull bank transaction alert emails. Tokens are encrypted with Fernet before being stored in SQLite. All other storage is local (SQLite file, filesystem master key). No third-party monitoring, logging, or payment services are integrated.

---

## Google OAuth2 / Gmail API

### Purpose

Reads HDFC Bank transaction alert emails from the connected user's Gmail inbox, extracts transaction data, and creates expense records automatically.

### Libraries

- `google-auth==2.37.0`
- `google-auth-oauthlib==1.2.1`
- `google-auth-httplib2==0.2.0`
- `google-api-python-client==2.155.0`

### Scopes Requested

```python
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
```

Read-only access only. No write, send, or delete permissions are requested.
Defined in `backend/app/services/gmail_service.py`.

### OAuth2 Flow

**Type:** Authorization Code flow with offline access (refresh token obtained).

**Step-by-step:**

1. Frontend calls `GET /api/gmail/auth-url` (authenticated).
2. Backend calls `GmailService.get_auth_url()` which builds a `Flow` from client config and returns a Google authorization URL with `access_type=offline`, `prompt=consent`.
3. Frontend redirects user to the Google consent screen.
4. Google redirects to `GOOGLE_REDIRECT_URI` (default: `http://localhost:3000/auth/gmail/callback`).
5. Frontend page `GmailCallbackPage` (`frontend/src/pages/GmailCallbackPage.jsx`) extracts the `code` query param and POSTs it to `POST /api/gmail/exchange`.
6. Backend calls `GmailService.exchange_code(code)`, which fetches token from Google using `flow.fetch_token(code=code)`.
7. Token JSON is encrypted with `CryptoService.encrypt()` and stored in `users.gmail_token_encrypted` (SQLite `Text` column).

There is also a `GET /api/gmail/callback` route (`backend/app/api/routes/gmail.py`) that handles the redirect directly and stores the token — this is an alternative flow where Google redirects to the backend rather than the frontend.

### Token Storage

- **Where:** `users.gmail_token_encrypted` column in SQLite (`backend/app/models/user.py`)
- **Format:** Fernet-encrypted JSON string containing:
  ```json
  {
    "token": "<access_token>",
    "refresh_token": "<refresh_token>",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "<client_id>",
    "client_secret": "<client_secret>",
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"]
  }
  ```
- **Encryption:** Fernet symmetric encryption via `CryptoService` (`backend/app/services/crypto_service.py`)
- **Master key location:** `data/credentials/master.key` (auto-generated; chmod 0600 best-effort)

### Token Refresh

Handled automatically in `GmailService._get_credentials()` (`backend/app/services/gmail_service.py`):

```python
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
```

The refreshed credentials are used in-memory for the request duration. The new access token is NOT persisted back to the database — the stored token JSON retains the original access token but refresh continues to work because the refresh token remains valid.

### Gmail Query

```python
GMAIL_QUERY = (
    "from:(hdfcbank.bank.in OR hdfcbank.com OR hdfc.com) "
    "newer_than:90d"
)
```

Fetches emails from HDFC Bank domains received within the last 90 days.
Currently only HDFC is in the query. Adding other banks requires updating this constant in `backend/app/services/gmail_service.py`.

### API Calls Made

All calls use `googleapiclient.discovery.build("gmail", "v1", credentials=creds)`.

| Operation | API Call |
|---|---|
| List matching emails | `service.users().messages().list(userId="me", q=GMAIL_QUERY, maxResults=N)` |
| Fetch full message | `service.users().messages().get(userId="me", id=msg_id, format="full")` |

### Gmail API Endpoints

**Routes in `backend/app/api/routes/gmail.py`:**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/gmail/auth-url` | Returns Google OAuth2 authorization URL |
| `POST` | `/api/gmail/exchange` | Exchanges OAuth code for encrypted token |
| `GET` | `/api/gmail/callback` | Alternative: handles direct Google redirect |
| `GET` | `/api/gmail/status` | Returns `{connected: bool}` for current user |
| `POST` | `/api/gmail/sync` | Fetches emails, parses, saves transactions |
| `DELETE` | `/api/gmail/disconnect` | Nulls out `gmail_token_encrypted` |

### Email Parsing

Parsed by `backend/app/parsers/hdfc_parser.py` (`HDFCParser` class). Supports:
- **UPI debit** alerts: regex matches `Rs.X has been debited from account XXXX to VPA ...`
- **Credit card debit** alerts: regex matches `Rs.X is debited from your HDFC Bank Credit Card ending XXXX towards ...`

Parser factory: `backend/app/parsers/parser_factory.py`
Categorization: `backend/app/parsers/categorizer.py`
Sync orchestration: `backend/app/services/email_sync_service.py`

### Required Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth2 client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth2 client secret |
| `GOOGLE_REDIRECT_URI` | Callback URL; must match Google Cloud Console setting |

Default redirect URI: `http://localhost:3000/auth/gmail/callback`

### Google Cloud Console Setup Required

- Create a project and enable the Gmail API
- Create OAuth2 credentials (Web Application type)
- Add `http://localhost:3000/auth/gmail/callback` as an authorized redirect URI
- For production, also add the VPS domain redirect URI

---

## Data Storage

**Database:**
- SQLite, file at `data/database/expense_tracker.db`
- No external database service

**File Storage:**
- Local filesystem only
- Master encryption key: `data/credentials/master.key`
- No S3, GCS, or other object storage

**Caching:**
- None

---

## Authentication (Internal)

Not an external integration but documented here for completeness:
- JWT (HS256) for API authentication — `python-jose`
- TOTP 2FA — `pyotp` + `qrcode`; secrets encrypted with Fernet before storage
- TOTP secrets stored in `users.totp_secret_encrypted` (same Fernet encryption as Gmail tokens)

---

## Monitoring & Observability

**Error Tracking:** None (not integrated)
**APM:** None
**Logs:** Python standard `logging` / FastAPI default stdout logs only

---

## CI/CD & Hosting

**Hosting:** Not yet deployed (Phase 7 targets VPS)
**CI Pipeline:** None configured

---

## Gaps / Unknowns

1. **Token refresh not persisted.** After `creds.refresh(Request())`, the new access token is used in memory but the updated token is never written back to `users.gmail_token_encrypted`. This means the stored `token` field grows stale, though the `refresh_token` keeps the flow working until revoked.

2. **Single-bank query.** `GMAIL_QUERY` only covers HDFC Bank domains. ICICI, SBI, and Flash.co parsers are planned (Phase 3) but the query does not yet include them.

3. **No token expiry tracking.** There is no scheduled job or background task to detect revoked refresh tokens proactively. Failures surface only at sync time as `RuntimeError`.

4. **Dual callback routes.** Both `POST /api/gmail/exchange` and `GET /api/gmail/callback` perform code exchange. The frontend uses the POST route; the GET route is for direct-to-backend redirect. This dual path could cause confusion and should be consolidated.

5. **Google Cloud project not provisioned.** `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` default to empty strings. Gmail integration will silently fail to generate a valid auth URL until these are configured.

---

_Integration audit: 2026-03-29_
