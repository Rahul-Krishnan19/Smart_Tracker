# Architecture

_Generated: 2026-03-29_

## Summary

Personal expense tracker built as a decoupled SPA + REST API. The React frontend communicates exclusively with a FastAPI backend over `/api/*`. The backend handles all business logic: two-factor auth (password + TOTP), Gmail OAuth2 token storage, email fetching, bank-specific parsing, and transaction CRUD. All sensitive data (TOTP secrets, OAuth tokens) is encrypted at rest using Fernet symmetric encryption before being written to SQLite.

---

## Overall Pattern

```
Browser (React SPA, port 3000)
        |
        | HTTP /api/* (proxied by Vite dev server → port 8000)
        |
FastAPI (Uvicorn, port 8000)
        |
        |-- routes layer (auth / transactions / gmail)
        |-- service layer (auth_service / transaction_service / email_sync_service / gmail_service / crypto_service / totp_service)
        |-- parser layer (parser_factory → HDFCParser → categorizer)
        |-- model layer (SQLAlchemy ORM)
        |
SQLite (data/database/expense_tracker.db, WAL mode)
        |
Fernet key (data/credentials/master.key, owner-only)
```

The Vite dev server proxies all `/api` requests to `localhost:8000`, so the frontend never hard-codes the backend host during development.

---

## Layers

**Routes layer:**
- Purpose: HTTP interface — parse request, call service, serialize response
- Location: `backend/app/api/routes/`
- Files: `auth.py`, `transactions.py`, `gmail.py`
- Depends on: service layer, SQLAlchemy `Session` (injected via `Depends(get_db)`)
- Authentication guard: `get_current_user()` in `auth.py` — verifies Bearer JWT, returns `User` ORM object. Imported and reused by `transactions.py` and `gmail.py`.

**Service layer:**
- Purpose: Business logic, isolated from HTTP concerns
- Location: `backend/app/services/`
- Each service is instantiated once as a module-level singleton (e.g., `auth_service = AuthService()`).
- Files and responsibilities:
  - `auth_service.py` — password hashing (bcrypt), JWT issuance/verification, temp token flow, session management, TOTP enrollment
  - `crypto_service.py` — Fernet singleton; `encrypt(str) → str` and `decrypt(str) → str`
  - `totp_service.py` — pyotp wrapper; generates secrets, verifies codes, produces QR PNG as base64 data URI
  - `gmail_service.py` — OAuth2 flow (auth URL generation, code exchange, token refresh); Gmail API email fetch and body extraction
  - `email_sync_service.py` — orchestrates fetch → dedup → parse → save pipeline
  - `transaction_service.py` — CRUD + filtered listing + summary aggregation

**Parser layer:**
- Purpose: Convert raw email text into `ParsedTransaction` dataclass
- Location: `backend/app/parsers/`
- Pattern: `BaseEmailParser` ABC defines the interface; concrete parsers implement `can_parse()` and `parse()`; `parser_factory.py` holds the `PARSERS` list and routes emails via `parse_email()`.

**Model layer:**
- Purpose: SQLAlchemy ORM definitions; schema-of-record
- Location: `backend/app/models/`
- Tables: `users`, `transactions`, `sessions`, `emails`

**Schema layer:**
- Purpose: Pydantic request/response validation; separate from ORM models
- Location: `backend/app/schemas/`

---

## Data Models

**User (`users` table):**
- `id`, `username`, `email`, `password_hash`
- `totp_secret_encrypted` — Fernet ciphertext of base32 TOTP secret; nullable until setup
- `totp_enrolled` — boolean gate; False during setup, True after first TOTP confirmation
- `gmail_token_encrypted` — Fernet ciphertext of JSON token bundle (`{token, refresh_token, token_uri, client_id, client_secret, scopes}`); nullable when Gmail not connected
- Relationships: `transactions` (cascade delete), `sessions` (cascade delete), `emails` (cascade delete)

**Transaction (`transactions` table):**
- `user_id` FK, `transaction_date`, `amount` (Numeric 10,2), `description`, `merchant`, `category`, `payment_method`, `notes`, `source` (`manual`|`email`|`upload`), `email_message_id` (unique — dedup key)
- Categories enum: `Rent, Groceries, Shopping, Electricity, Food & Dining, Transport, Entertainment, Healthcare, Others`
- Payment methods enum: `Credit Card, UPI, Cash, Debit Card, Net Banking, Others`
- Composite index on `(user_id, transaction_date)` for time-range queries

**EmailMetadata (`emails` table):**
- `user_id` FK, `gmail_message_id` (unique), `sender`, `subject`, `received_at`, `parse_status` (`pending`|`success`|`failed`|`skipped`), `parse_error`, `bank_name`, `delete_after`
- Tracks every fetched email regardless of parse outcome; enables dedup on re-sync

**UserSession (`sessions` table):**
- `user_id` FK, `session_token` (64-char hex), `expires_at`, `ip_address`, `user_agent`
- Session table exists but is not enforced on API routes yet (JWT is the active auth mechanism; session rows are created/expired but not validated per-request)

---

## Auth Flow

### Login (existing enrolled user)

```
Frontend                          Backend
--------                          -------
POST /api/auth/login
  {username, password}
                    ──────────►  authenticate_password()
                                   bcrypt.checkpw()
                                 create_temp_token()
                                   JWT type="temp", exp=5min
                    ◄──────────  {requires_totp: true, totp_enrolled: true, temp_token}

POST /api/auth/totp/verify
  {temp_token, totp_code}
                    ──────────►  verify_temp_token()  [validates type="temp"]
                                 verify_totp()
                                   decrypt(totp_secret_encrypted)
                                   pyotp.TOTP.verify(code, valid_window=1)
                                 create_access_token()
                                   JWT type="access", exp=30min
                    ◄──────────  {access_token, user_id, username}

localStorage: access_token, user JSON
All subsequent requests: Authorization: Bearer <access_token>
```

### First Login (TOTP not yet enrolled)

```
POST /api/auth/login → temp_token (same as above)

POST /api/auth/totp/setup?temp_token=...
                    ──────────►  verify_temp_token()
                                 totp_service.generate_secret()
                                 crypto_service.encrypt(secret) → stored in user.totp_secret_encrypted
                                 generate_qr_code_base64()
                    ◄──────────  {qr_code_url, secret, temp_token}

Frontend shows QR → user scans with authenticator app

POST /api/auth/totp/verify
                    ──────────►  confirm_totp_enrollment()
                                   decrypt secret, verify code
                                   user.totp_enrolled = True
                                 create_access_token()
                    ◄──────────  {access_token, ...}
```

### Per-Request Auth Guard

```
GET/POST /api/transactions/** or /api/gmail/**
    Authorization: Bearer <JWT>
                    ──────────►  get_current_user() [FastAPI Depends]
                                   verify_access_token() → payload
                                   get_user_by_id(payload["sub"])
                                   assert user.is_active
                    returns User ORM object to route handler
```

---

## Gmail OAuth2 Flow

```
Frontend                        Backend                       Google
--------                        -------                       ------
GET /api/gmail/auth-url
                  ──────────►  gmail_service.get_auth_url()
                                 Flow.authorization_url()
                                   access_type=offline
                                   prompt=consent
                  ◄──────────  {auth_url}

window.location.href = auth_url
                                                ──────────►  Google consent screen
                                                ◄──────────  redirect to
                                                             localhost:3000/auth/gmail/callback?code=...

GmailCallbackPage mounts,
reads ?code from URL

POST /api/gmail/exchange {code}
                  ──────────►  gmail_service.exchange_code(code)
                                 Flow.fetch_token(code=code)
                                 token_data = {token, refresh_token, ...}
                                 crypto_service.encrypt(json.dumps(token_data))
                               user.gmail_token_encrypted = encrypted
                               db.commit()
                  ◄──────────  {status: "connected"}

navigate('/transactions?gmail=connected')
```

### Gmail Sync Pipeline

```
POST /api/gmail/sync
                  ──────────►  email_sync_service.sync(db, user_id, encrypted_token)
                               │
                               ├─ gmail_service.fetch_transaction_emails(encrypted_token)
                               │     _get_credentials()
                               │       crypto_service.decrypt(encrypted_token)
                               │       Credentials object; auto-refresh if expired
                               │     Gmail API: messages.list(q=GMAIL_QUERY)
                               │     Gmail API: messages.get(id) for each message
                               │     _extract_email_data() → {id, sender, subject, body, ...}
                               │
                               ├─ For each email:
                               │     Check EmailMetadata by gmail_message_id → skip if exists
                               │     INSERT EmailMetadata(parse_status="pending")
                               │
                               │     parser_factory.parse_email(sender, subject, body)
                               │       get_parser() → iterate PARSERS list → can_parse()
                               │       HDFCParser.parse()
                               │         _parse_upi_debit()  OR  _parse_credit_card_debit()
                               │         categorize(merchant, description)
                               │       → ParsedTransaction dataclass
                               │
                               │     Check Transaction by email_message_id → skip if exists
                               │     INSERT Transaction(source="email", email_message_id=gmail_id)
                               │     UPDATE EmailMetadata(parse_status="success")
                               │
                  ◄──────────  {fetched, skipped_duplicate, parsed_ok, parse_failed, transactions_created}
```

**GMAIL_QUERY** (in `gmail_service.py`): `from:(hdfcbank.bank.in OR hdfcbank.com OR hdfc.com) newer_than:90d` — currently HDFC-only.

**Token refresh:** `_get_credentials()` calls `creds.refresh(Request())` if the access token is expired. The refreshed token is NOT persisted back to the database — a future concern.

---

## Parser Architecture

```
BaseEmailParser (ABC)
  bank_name: str          (abstract property)
  sender_patterns: list   (abstract property)
  subject_patterns: list  (abstract property)
  can_parse(sender, subject, body) → bool   (abstract)
  parse(body, subject) → Optional[ParsedTransaction]  (abstract)

HDFCParser(BaseEmailParser)
  can_parse(): sender contains hdfcbank.com/hdfc.com OR body contains "hdfc"
  parse():
    _parse_upi_debit()         → matches "Rs.X has been debited ... to VPA ..."
    _parse_credit_card_debit() → matches "Rs.X is debited from your HDFC Bank Credit Card ..."
    both call categorize(merchant, description) from categorizer.py

ParsedTransaction (dataclass)
  amount, description, merchant, transaction_date,
  payment_method, category, reference_number, account_last4, bank_name

parser_factory.PARSERS = [HDFCParser()]
  # ICICIParser, SBIParser, FlashParser commented — Phase 3
```

**To add a new bank:** create `backend/app/parsers/<bank>_parser.py` subclassing `BaseEmailParser`, then add an instance to `PARSERS` in `backend/app/parsers/parser_factory.py`.

**Categorizer** (`backend/app/parsers/categorizer.py`): keyword-matching dictionary, 8 categories, falls back to `Others`. Checks `(merchant + description).lower()` against keyword lists.

---

## Frontend Component Relationships

```
main.jsx
  └─ App.jsx
       └─ BrowserRouter
            └─ AuthProvider (AuthContext)
                 └─ AppRoutes
                      ├─ /login → LoginForm
                      │           ├─ step: credentials → credential form (react-hook-form + zod)
                      │           ├─ step: totp_setup  → TOTPSetup (QR display + verify)
                      │           └─ step: totp_verify → TOTP code entry form
                      │
                      ├─ /transactions (ProtectedRoute)
                      │    └─ Layout
                      │         └─ TransactionsPage
                      │              ├─ Summary cards (total spent, tx count, top categories)
                      │              ├─ GmailSync (connect / sync / disconnect)
                      │              ├─ FilterPanel (date range, category, payment method, search)
                      │              ├─ TransactionForm (add new manual transaction)
                      │              └─ TransactionList (paginated table with edit/delete)
                      │
                      ├─ /analytics (ProtectedRoute)
                      │    └─ Layout
                      │         └─ AnalyticsPage
                      │              ├─ Date range picker
                      │              ├─ KPI cards (total, count, avg)
                      │              ├─ PieChart (category breakdown) — Recharts
                      │              ├─ BarChart (payment method breakdown) — Recharts
                      │              └─ Category detail table
                      │
                      └─ /auth/gmail/callback (ProtectedRoute)
                           └─ GmailCallbackPage
                                reads ?code from URL
                                POST /api/gmail/exchange {code}
                                navigate → /transactions
```

**AuthContext** (`frontend/src/context/AuthContext.jsx`): holds `user` state initialized from `localStorage`. Exposes `login(userData, token)`, `logout()`, `isAuthenticated`. Token stored in `localStorage.access_token`.

**ProtectedRoute** (`frontend/src/components/auth/ProtectedRoute.jsx`): redirects to `/login` when `isAuthenticated` is false.

**API service** (`frontend/src/services/api.js`): Axios instance with `baseURL: '/api'`. Request interceptor attaches Bearer token. Response interceptor on 401: clears localStorage and redirects to `/login`.

---

## Key Design Decisions

1. **Two-token auth flow:** A short-lived (5 min) `type="temp"` JWT is issued after password verification, before TOTP. This prevents a leaked password from granting access without TOTP. The final `type="access"` JWT is 30 minutes.

2. **Fernet for sensitive fields:** TOTP secrets and OAuth tokens are encrypted per-field in the database using a single master Fernet key stored outside the database (`data/credentials/master.key`). Losing the key makes all tokens unrecoverable.

3. **Dedup by gmail_message_id:** Both `EmailMetadata.gmail_message_id` and `Transaction.email_message_id` are unique-constrained. Re-running sync is safe — already-processed emails are skipped at the metadata check stage before parsing.

4. **Email metadata separate from transactions:** Even emails that fail parsing (or produce no transaction) are recorded in `EmailMetadata` with a `parse_status`. This enables future re-processing and audit without re-fetching from Gmail.

5. **Extensible parser registry:** `parser_factory.PARSERS` is a plain list. Adding a new bank requires only creating a new subclass and appending an instance to the list.

6. **Token refresh not persisted:** `GmailService._get_credentials()` refreshes expired access tokens in-memory but does not write the updated token back to `user.gmail_token_encrypted`. After a token refresh, the persisted token becomes stale — future requests will keep re-refreshing.

7. **SQLite WAL mode:** Enabled via `PRAGMA journal_mode=WAL` on connect. Allows concurrent reads while a write is in progress, reducing lock contention during sync.

8. **Rate limiting:** Global 200 req/min via `slowapi` keyed on remote IP. Auth routes do not have stricter per-endpoint limits yet.

---

## API Endpoints Summary

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/auth/register` | None | Create user |
| POST | `/api/auth/login` | None | Password verify → temp token |
| POST | `/api/auth/totp/setup` | temp token (query param) | Generate TOTP secret + QR |
| POST | `/api/auth/totp/verify` | temp token (body) | Verify TOTP → access token |
| POST | `/api/auth/logout` | Bearer | (Stateless; clears client state) |
| GET | `/api/auth/me` | Bearer | Current user info |
| GET | `/api/transactions` | Bearer | List with filters + pagination |
| POST | `/api/transactions` | Bearer | Create manual transaction |
| GET | `/api/transactions/summary` | Bearer | Aggregate totals + breakdowns |
| GET | `/api/transactions/{id}` | Bearer | Single transaction |
| PUT | `/api/transactions/{id}` | Bearer | Update transaction |
| DELETE | `/api/transactions/{id}` | Bearer | Delete transaction |
| GET | `/api/gmail/auth-url` | Bearer | Get Google OAuth2 URL |
| GET | `/api/gmail/callback` | Bearer | OAuth redirect handler (server-side) |
| POST | `/api/gmail/exchange` | Bearer | Exchange OAuth code → store token |
| GET | `/api/gmail/status` | Bearer | Check if Gmail connected |
| POST | `/api/gmail/sync` | Bearer | Fetch + parse + save emails |
| DELETE | `/api/gmail/disconnect` | Bearer | Remove stored token |
| GET | `/api/health` | None | Health check |

---

## Gaps / Unknowns

- **Token refresh not persisted** (`gmail_service.py` line 83–84): after `creds.refresh()`, the new access token is never written back to the database. Long-running deployments will re-refresh on every sync call until the refresh token itself expires.
- **Session table not enforced:** `UserSession` rows are created on TOTP verify but never validated per-request. The `get_current_user()` guard only checks the JWT — sessions are effectively unused.
- **Logout is stateless:** No token blacklisting. A stolen JWT remains valid until its 30-minute expiry even after logout.
- **GMAIL_QUERY is HDFC-only:** The search query in `gmail_service.py` filters only HDFC sender domains. Adding new banks requires updating this query alongside creating new parsers.
- **No background sync:** Email sync is triggered manually via the UI. There is no scheduled/periodic sync.
- **No tests directory content:** `backend/tests/` and `backend/tests/fixtures/` directories exist but no test files were found.
- **Alembic migrations:** `backend/alembic/versions/` directory is empty. Schema is managed via `Base.metadata.create_all()` at startup — no migration history.
