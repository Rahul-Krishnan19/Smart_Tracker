# Phase 4: Automated Email Sync - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a per-user APScheduler cron job that runs email sync automatically on a user-configured schedule. The manual "Sync Emails" button is KEPT — auto-sync is an additional capability, not a replacement. Fix the Gmail token refresh persistence bug. Show "last updated at" timestamp next to the sync button.

GMAIL-09 (sync history log in Settings) is explicitly deferred — do not implement.

</domain>

<decisions>
## Implementation Decisions

### Manual Sync Button
- **D-01:** The existing "Sync Emails" button stays exactly as it is. Auto-sync is additive — a new settings toggle + schedule picker alongside the manual button.

### Scheduler Architecture
- **D-02:** One APScheduler job per user. Each user who enables auto-sync gets their own scheduled job in a single shared `BackgroundScheduler` instance.
- **D-03:** APScheduler tied to FastAPI lifespan — scheduler starts on app startup, shuts down on app shutdown. Use FastAPI lifespan context manager (not `@app.on_event` which is deprecated).
- **D-04:** Scheduler stores jobs in-memory (no persistent job store). On restart, re-register jobs for all users who have auto-sync enabled by querying the DB at startup.

### Schedule Options & Storage
- **D-05:** Four schedule options: `hourly` (every 1h), `every_12h` (every 12h), `daily` (every 24h), `custom` (user-specified interval in hours, integer, min 1h).
- **D-06:** New columns on `User` model (via Alembic migration):
  - `sync_enabled` — Boolean, default False
  - `sync_interval_hours` — Integer, nullable (1 = hourly, 12 = every 12h, 24 = daily, custom value)
  - `last_synced_at` — DateTime with timezone, nullable — updated after every sync (manual or auto)
- **D-07:** Settings UI has a toggle (Enable Auto-Sync) + a dropdown/radio for frequency. Only visible/active when Gmail is connected.

### "Last Synced" Display
- **D-08:** Display "Last updated at HH:MM DD MMM YYYY IST" next to the "Sync Emails" button on the GmailSync component.
- **D-09:** Value comes from `last_synced_at` in the `/api/gmail/status` response. Frontend fetches status on page load — no polling.
- **D-10:** Updated after BOTH manual and auto syncs. IST = UTC+5:30. Format the timestamp in IST on the frontend (use `toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })`).
- **D-11:** If `last_synced_at` is null (never synced), show nothing — no "Never synced" label.

### Failure Alerts
- **D-12:** Keep existing failure display — the red error box in GmailSync.jsx already shows sync errors. No changes to failure UI needed.

### Gmail Token Refresh Fix (GMAIL-05)
- **D-13:** After `creds.refresh(Request())` succeeds in `gmail_service._get_credentials()`, re-encrypt the refreshed token and return it alongside the credentials so the caller can persist it back to `user.gmail_token_encrypted` in the DB.
- **D-14:** Both the sync route (`POST /api/gmail/sync`) and the scheduler job must persist the refreshed token if it changed.

### Sync History (GMAIL-09)
- **D-15:** Explicitly deferred — do not implement sync history log or Settings UI for it.

### Email Retention (INFRA-03, INFRA-04)
- **D-16:** `email_retention_days` should come from a setting (not hardcoded 30). Add `email_retention_days` to app settings (`.env` + `config.py`), default 30. The scheduler's cleanup job reads this value.
- **D-17:** Add a daily cleanup job (separate APScheduler job, runs at 03:00) that deletes `EmailMetadata` rows past their `delete_after` date.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Sync Infrastructure
- `backend/app/services/email_sync_service.py` — EmailSyncService.sync() — the core sync logic that scheduler will call
- `backend/app/services/gmail_service.py` — _get_credentials(), fetch_transaction_emails() — token refresh happens here
- `backend/app/api/routes/gmail.py` — POST /api/gmail/sync, GET /api/gmail/status — routes to update
- `frontend/src/components/gmail/GmailSync.jsx` — UI component to extend with schedule toggle + last-synced display

### Models to Extend
- `backend/app/models/user.py` — add sync_enabled, sync_interval_hours, last_synced_at columns
- `backend/app/models/email_metadata.py` — delete_after column already exists (used by cleanup job)

### App Entry Point
- `backend/app/main.py` — add APScheduler lifespan here; scheduler startup/shutdown

### Config
- `backend/app/config.py` — add email_retention_days setting
- `backend/.env.example` — document new env var

### Requirements for this phase
- `.planning/REQUIREMENTS.md` — GMAIL-05, GMAIL-06, GMAIL-07, GMAIL-08, GMAIL-10, INFRA-03, INFRA-04 (GMAIL-09 deferred)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EmailSyncService.sync(db, user_id, encrypted_token)` — scheduler calls this directly, no changes to signature needed
- `GmailSync.jsx` — already has `connected` state and error display; extend with schedule settings and last-synced timestamp
- `User.gmail_token_encrypted` — already Fernet-encrypted; same pattern for persisting refreshed token

### Established Patterns
- Fernet encryption via `crypto_service.encrypt/decrypt` — use for any token re-encryption
- Alembic migrations — new columns go in a new migration file (pattern established in Phase 3)
- FastAPI `Depends(get_db)` for DB sessions in routes — scheduler job needs its own `SessionLocal()` context manager (not a FastAPI dependency)
- `settings` from `app/config.py` (Pydantic BaseSettings) — add `email_retention_days: int = 30` here

### Integration Points
- `main.py` lifespan: scheduler starts here, queries all users with `sync_enabled=True` to re-register jobs on restart
- `POST /api/gmail/sync`: after sync, update `user.last_synced_at = datetime.now(timezone.utc)` and persist refreshed token if changed
- `GET /api/gmail/status`: add `last_synced_at` and `sync_enabled`, `sync_interval_hours` to response
- New `PUT /api/gmail/settings` route: accepts `{ sync_enabled: bool, sync_interval_hours: int }` — updates DB + re-registers/cancels APScheduler job

</code_context>

<specifics>
## Specific Implementation Notes

- **IST formatting:** Frontend uses `new Date(ts).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })` — no backend timezone conversion needed; store UTC, format in browser.
- **APScheduler job ID convention:** `f"gmail_sync_user_{user_id}"` — deterministic, used to add/remove/check jobs.
- **Custom interval:** When user selects "custom", show a number input (hours, integer, min 1). Store the raw integer in `sync_interval_hours`.
- **Scheduler job function:** Must be a standalone function (not a method) that opens its own DB session, fetches the user, runs sync, persists `last_synced_at` and refreshed token, closes DB session.
- **APScheduler version:** 3.11.2 is available and installable on Python 3.14 (confirmed — no C compilation needed).

</specifics>

<deferred>
## Deferred Ideas

- **GMAIL-09: Sync history log in Settings** — explicitly deferred by user ("don't need to show sync history")
- Sync failure push notifications / email alerts — Phase 7 (insights) or later

</deferred>

---
*Phase: 04-automated-email-sync*
*Context gathered: 2026-04-05*
