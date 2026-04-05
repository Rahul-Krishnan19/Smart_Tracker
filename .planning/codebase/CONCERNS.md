# Concerns & Risks
_Generated: 2026-03-29_

## Summary

The codebase is well-structured for a personal tool and Phase 1 is solid. The main risk categories are:
(1) a hardcoded `localhost` URL that will break OAuth in production, (2) JWT tokens stored in `localStorage` which is XSS-accessible, (3) no TOTP brute-force protection, (4) Gmail token refresh silently drops the new token after expiry, (5) parser regex is format-brittle and only covers HDFC. Several planned phases (ICICI/SBI/Flash parsers, CSV upload, full analytics) are not yet implemented. No tests exist despite test dependencies being installed.

---

## Security

### [HIGH] JWT stored in localStorage — XSS accessible
`frontend/src/services/api.js` reads `localStorage.getItem('access_token')` on every request. `frontend/src/context/AuthContext.jsx` writes access tokens and user objects to `localStorage`. Any XSS vulnerability in the page (including from third-party npm packages) can exfiltrate the token.
**Fix:** Store the JWT in an `HttpOnly` cookie instead. Adjust the FastAPI CORS config and axios to send cookies (`withCredentials: true`). This requires backend changes to issue and read `Set-Cookie` headers.

### [HIGH] Hardcoded `localhost` redirect URL in OAuth callback
`backend/app/api/routes/gmail.py` line 76 returns `RedirectResponse(url="http://localhost:3000/transactions?gmail=connected")`. On VPS deployment this redirect will fail, breaking the entire Gmail OAuth flow.
**Fix:** Read the frontend URL from `settings` (e.g. a new `FRONTEND_URL` env var) and use it in the redirect. The `.env.example` already has `GOOGLE_REDIRECT_URI=http://localhost:3000/auth/gmail/callback` — the redirect target needs the same treatment.

### [HIGH] Default `secret_key` fallback is a known string
`backend/app/config.py` line 9: `secret_key: str = "change-this-to-a-random-secret-key-min-32-chars"`. If `.env` is absent or the var is unset, the app starts with a public default key, making all JWTs forgeable.
**Fix:** Add a startup validator that raises on the default value (or any value shorter than 32 chars) when `debug=False`. Alternatively use `pydantic.Field(min_length=32)` with no default.

### [MED] No TOTP brute-force / rate limiting on login step 2
`backend/app/api/routes/auth.py` `/totp/verify` has no per-user attempt counter. The global slowapi limiter (`200/minute` by IP) is too loose to prevent distributed TOTP guessing. TOTP codes are 6 digits (1,000,000 space) valid for ~90 seconds (window=1), so this is feasible under the current limits.
**Fix:** Track failed TOTP attempts per `temp_token` or `user_id` (in-memory or a DB counter). Lock out after 5 failures. Temp tokens expire in 5 minutes, so an in-memory dict keyed on user_id is sufficient for a single-instance deployment.

### [MED] Refresh token persisted but refreshed credentials not re-encrypted and saved
`backend/app/services/gmail_service.py` `_get_credentials()` lines 83-84: when the access token is expired it calls `creds.refresh(Request())`, which updates the in-memory `Credentials` object. The new access token is never written back to the database. On the next sync the stale encrypted token is decrypted again, resulting in a re-fresh on every call. If Google rotates the refresh token (rare but documented behavior), the original refresh token becomes invalid and the connection silently breaks.
**Fix:** After `creds.refresh()`, re-encrypt the updated token data and persist it via `user.gmail_token_encrypted = crypto_service.encrypt(...)` and `db.commit()`. This requires passing the db session and user into `_get_credentials` or returning the updated creds to the caller.

### [MED] `totp/setup` endpoint re-generates TOTP secret on every call
`backend/app/api/routes/auth.py` line 52 and `auth_service.py` `setup_totp()` always overwrite `user.totp_secret_encrypted`. If a user or attacker with a valid temp token calls `/totp/setup` multiple times, each call invalidates the previously displayed QR code. A race between two browser tabs or a replay attack can leave the user with an app showing a different secret than what is stored.
**Fix:** Only generate a new TOTP secret if `user.totp_secret_encrypted` is `None` (i.e., never enrolled). If already set but not yet enrolled, return the existing pending secret.

### [LOW] `master.key` file permissions are best-effort on Windows
`backend/app/services/crypto_service.py` line 43: `os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)` is wrapped in a bare `except: pass` because Windows does not fully honor POSIX permissions. On the dev machine (Windows 11) the key file may be world-readable by other local users.
**Fix:** For VPS deployment (Linux), chmod will work correctly. Document this limitation and note that Windows dev should not store real credentials. Consider using Windows DPAPI or simply rely on the Linux production environment.

### [LOW] `DEBUG` mode exposes `/api/docs` Swagger UI
`backend/app/main.py` line 26: `docs_url="/api/docs" if settings.debug else None`. The Swagger UI is disabled in production (`DEBUG=False`), which is correct. Ensure `.env` on VPS sets `DEBUG=False` — there is no startup assertion enforcing this.

### [LOW] HTML stripped from email bodies but script content is passed to regex
`backend/app/services/gmail_service.py` `_extract_body()` strips HTML tags via `re.sub(r'<[^>]+>', ' ', html)`. This leaves script/style text content in place (e.g. `<script>alert(1)</script>` becomes `alert(1)`). The plain text is then fed only to parsers and stored as metadata; it is never rendered as HTML in the frontend. Risk is low in the current design but worth noting if email body content is ever surfaced in the UI.

---

## Reliability

### [HIGH] Gmail token refresh does not persist updated credentials
(See Security section above — also a reliability concern.) After an access token expires, every sync call re-fetches a fresh access token from Google on each request but discards it. If the refresh token is ever revoked, all subsequent syncs fail with an opaque `RuntimeError` from `gmail_service.py` line 127. The error surfaces to the user as a 502 but gives no actionable recovery path (e.g. "reconnect Gmail").
**Fix:** Persist refreshed credentials as described above. On `google.auth.exceptions.RefreshError`, catch it in `email_sync_service.py` or the route, clear `user.gmail_token_encrypted`, and return a `400` with `"Gmail token expired. Please reconnect Gmail."`.

### [HIGH] `email_retention_days` cutoff is calculated incorrectly
`backend/app/services/email_sync_service.py` line 41: `retention_cutoff = datetime.now(timezone.utc) + timedelta(days=30)`. The variable is named `delete_after` and should be a date in the *future* relative to now, which this does compute correctly. However, `email_retention_days` from settings (configurable) is not used — the value is hardcoded as `timedelta(days=30)`. Changes to `EMAIL_RETENTION_DAYS` in `.env` have no effect on the cutoff.
**Fix:** Replace `timedelta(days=30)` with `timedelta(days=settings.email_retention_days)`. Also note: there is no background job that actually deletes records past `delete_after`. The field is computed and stored but never acted upon.

### [MED] No background job enforces `delete_after` on EmailMetadata
`backend/app/models/email_metadata.py` has a `delete_after` column but nothing in the codebase queries or deletes expired records. Over time the `emails` table will grow unboundedly.
**Fix:** Add a scheduled cleanup (APScheduler or a startup task) in `main.py` that periodically deletes `EmailMetadata` rows where `delete_after < now()`. A simple route (`POST /api/admin/cleanup`) could also be acceptable for a personal tool.

### [MED] `parse_failed` summary counter is incremented both for parse errors and for unmatched emails
`backend/app/services/email_sync_service.py` lines 77-84: `summary["parse_failed"] += 1` is incremented when `parsed is None` (no parser matched) in addition to when an exception occurs. This conflates "unsupported bank email" with "parser crashed", making the sync result message misleading.
**Fix:** Use a separate `"unmatched"` key for `parsed is None` and reserve `"parse_failed"` for actual exceptions.

### [MED] HDFC UPI parser falls back to `date.today()` on unparsed dates
`backend/app/parsers/hdfc_parser.py` lines 142-143 and 199-200: if no date is found in the email, `txn_date = date.today()`. Emails imported days or weeks after they were received would be stamped with the import date, not the actual transaction date. This silently corrupts historical data.
**Fix:** Return `None` from `_parse_date` failures and propagate it as `ParsedTransaction.transaction_date = None`. Let the caller fall back to `email["received_at"]` (which is the actual Gmail `internalDate`) rather than `date.today()`.

### [MED] Whitespace normalisation in `_parse_upi_debit` can break multi-word merchant names
`backend/app/parsers/hdfc_parser.py` line 85: `body_clean = ' '.join(body.split())` collapses all whitespace. The regex on line 118-120 captures the merchant name as `([\w\s]+?)` between the VPA and the date string. In most cases this works, but merchant names with punctuation (hyphens, ampersands) or names that happen to resemble date fragments will be silently truncated or mis-parsed.
**Fix:** Test against a wider range of real HDFC email formats. Add a `tests/parsers/` test file with body fixtures covering edge cases.

### [LOW] `_extract_body` prefers `text/plain` but does not handle `text/html`-only emails robustly
`backend/app/services/gmail_service.py` `_extract_body()` returns `None` if neither `text/plain` nor `text/html` is found. It prefers `text/plain` in multipart messages. HDFC credit card alerts are typically HTML-only. If a bank changes to plain-text-only or a new bank uses a deeply nested MIME structure, `_extract_body` returns `""` and the email is silently skipped (`if not body: return None` on line 143).
**Fix:** Add logging at DEBUG level when body extraction returns empty, to aid diagnosis.

### [LOW] `max_emails` parameter in sync is not validated beyond FastAPI's type check
`backend/app/api/routes/gmail.py` line 88: `max_emails: int = 50`. A user (or automated caller) could set `max_emails=5000`, causing a very large number of sequential Gmail API calls (one per message) in a single request, potentially timing out or exhausting the API quota.
**Fix:** Add `Query(50, ge=1, le=200)` constraint, consistent with the pagination limits used in transactions.

---

## Compatibility

### [MED] Python 3.14 — `pydantic-core` / binary-wheel gap
As noted in project memory: `pydantic==2.10.3` fails on Python 3.14 because `pydantic-core` requires Rust compilation. The workaround (`pydantic==2.12.5`) is in place. Any future dependency upgrade that pulls in `pydantic-core < 2.27` or another Rust-compiled package without a 3.14 wheel will silently fail at install time.
**Fix:** Pin `pydantic>=2.12.5` in `requirements.txt` with a comment explaining the Python 3.14 constraint. When deploying to VPS, confirm the target Python version and pre-check for binary wheel availability.

### [MED] `pandas` and `openpyxl` commented out — Phase 4 CSV upload is blocked
`backend/requirements.txt` lines 39-41: `pandas` and `openpyxl` are commented out because pandas requires build tools (meson/MSVC) not available on the dev machine. Phase 4 (CSV/Excel import) cannot be implemented until this is resolved.
**Fix:** On VPS (Linux), pandas installs via pre-built wheels. Install only on the production environment. Add a note in the Phase 4 planning doc. For local dev, consider `polars` as an alternative (pure Rust, no build tools).

### [LOW] `python-jose` is in maintenance mode
`backend/requirements.txt` line 11: `python-jose[cryptography]==3.3.0`. The `python-jose` library has not had a release since 2022 and has open CVEs related to algorithm confusion attacks when `algorithms=["HS256"]` is enforced. The current usage explicitly passes `algorithms=[ALGORITHM]` in both `jwt.encode` and `jwt.decode`, which mitigates the main CVE.
**Fix:** Monitor for a replacement. `PyJWT` is the actively maintained alternative. Migrate to `PyJWT` when implementing token refresh or blacklisting.

### [LOW] `alembic` is configured but no migration scripts exist
`backend/alembic/` exists and `alembic/env.py` is set up, but `alembic/versions/` contains no migration files. The app uses `Base.metadata.create_all()` at startup instead. This is fine for early development but means there is no schema migration path when adding columns.
**Fix:** Before adding any new columns (e.g. for Phase 2 OAuth fields), generate the initial migration with `alembic revision --autogenerate -m "initial"` and commit it. Switch startup to rely on alembic rather than `create_all`.

---

## Completeness

### [HIGH] ICICI, SBI, Flash.co parsers not implemented
`backend/app/parsers/parser_factory.py` lines 11-13: `ICICIParser`, `SBIParser`, `FlashParser` are commented out as Phase 3 stubs. All non-HDFC transaction emails will silently hit `parse_status="skipped"` with error "No parser matched".
**Status:** Phase 3 not started.

### [HIGH] CSV/Excel file upload not implemented
The `upload` source value exists in `backend/app/models/transaction.py` line 9 (`SOURCES = ["manual", "email", "upload"]`) and is referenced in the frontend UI, but there is no upload API route, no file handling logic, and `pandas`/`openpyxl` are commented out.
**Status:** Phase 4 not started.

### [MED] Analytics page is read-only summary — no trend charts over time
`frontend/src/pages/AnalyticsPage.jsx` shows category breakdown (pie) and payment method breakdown (bar) for a date range. There are no time-series charts (spending per day/week/month), no budget vs. actual comparison, and no merchant drill-down. The backend `get_summary` endpoint in `transaction_service.py` does not return time-bucketed data.
**Status:** Phase 5 partially implemented (summary only). Trend charts not started.

### [MED] No logout invalidation — JWT is stateless with no blacklist
`backend/app/api/routes/auth.py` line 93: `logout` endpoint returns a success message but performs no server-side action. The JWT remains valid until its 30-minute expiry. Sessions (`UserSession`) table exists and is populated by `create_session`, but `create_session` is never called during login. Sessions are created but unused; the access token is the sole auth mechanism.
**Fix:** Either (a) implement a token blacklist table with a TTL index, or (b) use short JWT expiry + refresh tokens (currently no refresh token endpoint exists), or (c) call `auth_service.create_session` on login and check it on each request. For a personal tool, option (a) with a simple DB table is simplest.

### [LOW] `UserSession` model is unused
`backend/app/models/session.py` and `auth_service.py` `create_session()` / `get_valid_session()` are implemented but never called from any route. The `sessions` table is created but stays empty.

### [LOW] No income/credit transaction support
`backend/app/parsers/hdfc_parser.py` only parses debit alerts. HDFC also sends credit alerts (salary credit, UPI received). These are silently skipped. The `amount` column has no sign convention documented.

---

## Production Readiness

### [HIGH] No HTTPS — all traffic including JWTs and OAuth codes is plaintext
`vite.config.js` proxies to `http://localhost:8000`. The Google OAuth redirect URI in `.env.example` is `http://localhost:3000`. On VPS without a TLS termination proxy, auth tokens and the OAuth code will travel in plaintext.
**Fix:** Deploy behind nginx with Let's Encrypt TLS. Update `GOOGLE_REDIRECT_URI` and `ALLOWED_ORIGINS` to `https://` URLs. Google OAuth requires `https` for production redirect URIs anyway.

### [HIGH] `GOOGLE_REDIRECT_URI` in config points to localhost
`backend/app/config.py` line 16: default `google_redirect_uri = "http://localhost:3000/auth/gmail/callback"`. For VPS deployment, this must be changed to the production domain. If forgotten, Google will reject the OAuth callback with a redirect_uri_mismatch error.
**Fix:** Remove the default value and require `GOOGLE_REDIRECT_URI` to be explicitly set. Add a startup assertion that it does not contain `localhost` when `DEBUG=False`.

### [MED] `Base.metadata.create_all()` at startup instead of migrations
`backend/app/main.py` line 17: `Base.metadata.create_all(bind=engine)` runs on every startup. This is safe for initial creation but will silently skip new columns added in future model changes. On VPS, deploying a new version with a schema change will leave the DB out of sync.
**Fix:** Switch to alembic migrations before first VPS deployment.

### [MED] No process manager or graceful shutdown configured
The run instructions use plain `uvicorn app.main:app --reload`. For VPS deployment, `--reload` should be removed, and a process manager (systemd unit or Docker) is needed for restart-on-crash and log capture.
**Fix:** Add a `systemd` service file or `Dockerfile` to the project. Document in README.

### [MED] SQLite is not safe for concurrent writes under multi-worker uvicorn
SQLite with WAL mode (the `.db-shm` / `.db-wal` files are present) handles one writer at a time. If uvicorn is run with `--workers 2+`, concurrent write requests will hit `OperationalError: database is locked`. For a single-user personal tool on one worker this is acceptable.
**Fix:** Document the single-worker constraint. If ever scaled, migrate to PostgreSQL.

### [LOW] No structured logging or log rotation
`backend/app/main.py` and all services use no explicit logging framework — errors surface only through FastAPI's default uvicorn access log and unhandled exception stacktraces. On VPS, these go to stdout with no rotation.
**Fix:** Add a `logging.config` setup in `main.py` with a JSON formatter and a rotating file handler for production.

### [LOW] No health check includes dependency status
`GET /api/health` returns `{"status": "healthy"}` unconditionally. It does not check DB connectivity or whether the encryption key is loadable.
**Fix:** Add a DB ping (e.g. `db.execute("SELECT 1")`) and a crypto service warmup check in the health endpoint.

---

## Gaps / Phase Roadmap Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Auth, manual transactions, JWT + TOTP 2FA | Complete |
| 2 | Gmail OAuth2 integration, HDFC email sync | Complete (but token refresh not persisted — see above) |
| 3 | ICICI, SBI, Flash.co parsers | Not started |
| 4 | CSV/Excel file upload (needs pandas) | Not started — blocked by pandas install on dev machine |
| 5 | Analytics dashboard (trend charts, budget tracking) | Partially complete (summary only; no time-series) |
| 6 | Security hardening (HTTPS, token blacklist, TOTP rate limit) | Not started |
| 7 | VPS deployment (nginx, TLS, systemd, alembic migrations) | Not started |

Key pre-deployment blockers (must fix before Phase 7):
- Hardcoded `localhost` in OAuth redirect (`gmail.py` line 76)
- Default `secret_key` with no enforcement (`config.py` line 9)
- JWT in localStorage (XSS risk)
- Alembic migrations not generated
- Gmail token refresh not persisted
