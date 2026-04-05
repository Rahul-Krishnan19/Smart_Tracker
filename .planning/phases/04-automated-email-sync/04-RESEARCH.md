# Phase 4: Automated Email Sync - Research

**Researched:** 2026-04-05
**Domain:** APScheduler + FastAPI lifespan, SQLite WAL concurrency, Gmail token refresh, Alembic migration
**Confidence:** HIGH

## Summary

Phase 4 adds a per-user APScheduler background job that syncs Gmail automatically on a user-configured schedule. The existing manual "Sync Emails" button is kept unchanged — automation is additive. Three orthogonal concerns need careful planning: (1) the scheduler lifecycle (FastAPI lifespan, job re-registration on restart, in-memory job store); (2) the Gmail token refresh bug fix (refreshed credentials must be re-encrypted and persisted to DB by every caller that triggers a refresh); and (3) the Alembic migration adding three columns to the `users` table plus a daily cleanup job that deletes expired `EmailMetadata` rows.

The codebase already has all the pieces: `EmailSyncService.sync()` is the re-entrant sync function the scheduler will call, `SessionLocal` from `app/database.py` is the correct way to open a DB session inside the job function (not `Depends(get_db)`), and the existing Alembic migration chain (`7a9eaedc9937` → `628c6541bc23`) provides the template for the new migration. The two notable risks are (a) SQLite WAL single-writer serialisation when the scheduler job and an in-flight HTTP request both call `db.commit()` simultaneously, and (b) `_run_db_migrations()` currently runs at module-import time, which must be refactored into the lifespan context manager before adding the scheduler (otherwise the scheduler starts before migrations complete if boot order ever changes).

**Primary recommendation:** Use APScheduler 3.x `BackgroundScheduler` with `IntervalTrigger`, wired into FastAPI lifespan. All job code uses `with SessionLocal() as db:` explicitly. Token-refresh persistence is handled by making `_get_credentials()` return `(creds, new_encrypted_token_or_None)` so every call site can conditionally persist.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The existing "Sync Emails" button stays exactly as it is. Auto-sync is additive — a new settings toggle + schedule picker alongside the manual button.
- **D-02:** One APScheduler job per user. Each user who enables auto-sync gets their own scheduled job in a single shared `BackgroundScheduler` instance.
- **D-03:** APScheduler tied to FastAPI lifespan — scheduler starts on app startup, shuts down on app shutdown. Use FastAPI lifespan context manager (not `@app.on_event` which is deprecated).
- **D-04:** Scheduler stores jobs in-memory (no persistent job store). On restart, re-register jobs for all users who have `sync_enabled=True` by querying the DB at startup.
- **D-05:** Four schedule options: `hourly` (every 1h), `every_12h` (every 12h), `daily` (every 24h), `custom` (user-specified interval in hours, integer, min 1h).
- **D-06:** New columns on `User` model (via Alembic migration): `sync_enabled` (Boolean, default False), `sync_interval_hours` (Integer, nullable), `last_synced_at` (DateTime with timezone, nullable).
- **D-07:** Settings UI has a toggle (Enable Auto-Sync) + a dropdown/radio for frequency. Only visible/active when Gmail is connected.
- **D-08:** Display "Last updated at HH:MM DD MMM YYYY IST" next to the "Sync Emails" button on the GmailSync component.
- **D-09:** Value comes from `last_synced_at` in the `/api/gmail/status` response. Frontend fetches status on page load — no polling.
- **D-10:** Updated after BOTH manual and auto syncs. IST = UTC+5:30. Format the timestamp in IST on the frontend (use `toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })`).
- **D-11:** If `last_synced_at` is null (never synced), show nothing — no "Never synced" label.
- **D-12:** Keep existing failure display — the red error box in GmailSync.jsx already shows sync errors. No changes to failure UI needed.
- **D-13:** After `creds.refresh(Request())` succeeds in `gmail_service._get_credentials()`, re-encrypt the refreshed token and return it alongside the credentials so the caller can persist it back to `user.gmail_token_encrypted` in the DB.
- **D-14:** Both the sync route (`POST /api/gmail/sync`) and the scheduler job must persist the refreshed token if it changed.
- **D-15:** GMAIL-09 (sync history log) explicitly deferred — do not implement.
- **D-16:** `email_retention_days` from settings (not hardcoded). Add to `.env` + `config.py`, default 30. The cleanup job reads this value.
- **D-17:** Add a daily cleanup job (separate APScheduler job, runs at 03:00) that deletes `EmailMetadata` rows past their `delete_after` date.

### Claude's Discretion

_(None stated in CONTEXT.md — all decisions are locked.)_

### Deferred Ideas (OUT OF SCOPE)

- **GMAIL-09: Sync history log in Settings** — explicitly deferred by user ("don't need to show sync history")
- Sync failure push notifications / email alerts — Phase 7 or later
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GMAIL-05 | Refreshed OAuth access tokens persisted back to DB | `_get_credentials()` must return `(creds, new_encrypted)` tuple; callers write to `user.gmail_token_encrypted` |
| GMAIL-06 | Automated sync on configurable cron schedule (default: daily) | APScheduler `BackgroundScheduler` + `IntervalTrigger`; re-register on startup from DB |
| GMAIL-07 | Sync status visible: "Last synced: …" near Sync Now button | `last_synced_at` added to `/api/gmail/status` response; formatted IST in frontend |
| GMAIL-08 | Sync failures surface as in-app alert (not silent) | Existing red error box in GmailSync.jsx covers manual syncs; scheduler job must log errors but not crash |
| GMAIL-10 | Sync schedule user-configurable (hourly / 12h / daily / custom) | `PUT /api/gmail/settings` route; `sync_interval_hours` int stored in DB |
| GMAIL-09 | ~~Sync history log accessible in Settings~~ | **DEFERRED — do not implement** |
| INFRA-03 | `email_retention_days` setting respected (not hardcoded 30) | `config.py` already has `email_retention_days: int = 30`; `email_sync_service.py` line 42 hardcodes `timedelta(days=30)` — must read from `settings.email_retention_days` |
| INFRA-04 | Expired EmailMetadata rows cleaned up by background job | APScheduler daily cleanup job at 03:00; deletes `EmailMetadata` where `delete_after <= now()` |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 | Background job scheduler | Confirmed installable on Python 3.14 (pure Python wheel, no C compilation); decision locked in D-02/D-03 |
| SQLAlchemy | 2.0.36 | ORM + session management for scheduler job | Already in project; scheduler opens `SessionLocal()` directly |
| Alembic | 1.14.0 | DB migration for new User columns | Already in project; migration chain established |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI lifespan | (built-in, FastAPI 0.115.0) | Start/stop scheduler on app boot/shutdown | Replaces deprecated `@app.on_event` |
| `contextlib.asynccontextmanager` | stdlib | Used to write async lifespan generator | Required by FastAPI lifespan API |
| `datetime.timezone.utc` | stdlib | UTC timestamps for `last_synced_at` | Always store UTC; display conversion is frontend concern |

### Installation

```bash
# From backend/ with venv active:
pip install apscheduler==3.11.2
```

Add to `requirements.txt`:
```
apscheduler==3.11.2
```

**Version verified:** `python -m pip index versions apscheduler` confirms 3.11.2 is the current latest (2026-04-05). No C extension compilation required — pure Python package.

---

## Architecture Patterns

### Recommended Project Structure (new files)

```
backend/app/
├── scheduler.py                   # NEW — BackgroundScheduler instance + job functions
├── main.py                        # MODIFY — add lifespan, remove top-level _run_db_migrations() call
├── config.py                      # MODIFY — email_retention_days already present (no change needed)
├── models/user.py                 # MODIFY — add 3 columns
├── services/gmail_service.py      # MODIFY — _get_credentials() returns (creds, new_encrypted_or_None)
├── services/email_sync_service.py # MODIFY — use settings.email_retention_days instead of hardcoded 30
├── api/routes/gmail.py            # MODIFY — update /sync, /status, add PUT /settings
backend/alembic/versions/
└── XXXXXX_add_user_sync_columns.py  # NEW migration
frontend/src/components/gmail/
└── GmailSync.jsx                  # MODIFY — add last-synced display + schedule settings UI
```

### Pattern 1: FastAPI Lifespan with Scheduler

**What:** The scheduler is created once, started in lifespan `__aenter__`, jobs re-registered from DB, and shut down in lifespan `__aexit__`.

**When to use:** Any long-lived background resource that must be started/stopped with the application.

**Example:**
```python
# backend/app/scheduler.py
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# backend/app/main.py  (replaces current module-level _run_db_migrations() call)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.scheduler import scheduler
from app.database import SessionLocal
from app.models.user import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    _run_db_migrations()           # move migration call here from module-level
    scheduler.start()
    # Re-register jobs for all users with sync_enabled=True
    with SessionLocal() as db:
        users = db.query(User).filter(User.sync_enabled == True).all()
        for user in users:
            _register_sync_job(user.id, user.sync_interval_hours)
    yield
    # --- shutdown ---
    scheduler.shutdown(wait=False)

app = FastAPI(..., lifespan=lifespan)
```

### Pattern 2: Scheduler Job Function (standalone, own DB session)

**What:** The job function is a plain function (not a coroutine, not a method) that opens its own `SessionLocal` session because FastAPI's `Depends(get_db)` is unavailable outside request context.

**When to use:** Any APScheduler job that needs DB access.

**Critical detail:** SQLAlchemy 2.x `SessionLocal()` used as a context manager (`with SessionLocal() as db:`) handles `close()` automatically. This is the correct pattern.

**Example:**
```python
# backend/app/scheduler.py
from app.database import SessionLocal
from app.models.user import User
from app.services.email_sync_service import email_sync_service
from app.services.gmail_service import gmail_service
from datetime import datetime, timezone

def sync_user_emails(user_id: int) -> None:
    """Called by APScheduler — must open its own DB session."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.gmail_token_encrypted:
            return
        try:
            creds, new_token = gmail_service._get_credentials(user.gmail_token_encrypted)
            if new_token:
                user.gmail_token_encrypted = new_token
                db.commit()
            summary = email_sync_service.sync(
                db=db,
                user_id=user_id,
                encrypted_token=user.gmail_token_encrypted,
            )
            user.last_synced_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            # Log but do not re-raise — scheduler must not crash
            import logging
            logging.getLogger(__name__).error(f"Auto-sync failed for user {user_id}: {e}")
```

### Pattern 3: Token Refresh Fix — Return Tuple

**What:** `_get_credentials()` currently returns only `Credentials`. After the fix it returns `tuple[Credentials, str | None]` — the second element is the new encrypted token if a refresh happened, else `None`.

**Why:** The caller (route handler or scheduler job) must persist the new token to DB. The service layer should not have its own DB session — that would violate separation of concerns.

**Example:**
```python
# backend/app/services/gmail_service.py
def _get_credentials(self, encrypted_token: str) -> tuple[Credentials, str | None]:
    token_data = json.loads(crypto_service.decrypt(encrypted_token))
    creds = Credentials(...)
    new_encrypted = None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Re-serialize and re-encrypt the refreshed token
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
            raise RuntimeError(f"Gmail token expired and refresh failed: {e}.")
    return creds, new_encrypted
```

Both `_get_service()` and all callers of `_get_credentials()` must be updated to unpack the tuple.

### Pattern 4: APScheduler Job Registration / De-registration

**What:** Jobs are added and removed by deterministic job ID. `add_job` with `replace_existing=True` is safe to call on re-register.

**Example:**
```python
from apscheduler.triggers.interval import IntervalTrigger

JOB_ID_TEMPLATE = "gmail_sync_user_{user_id}"

def _register_sync_job(user_id: int, interval_hours: int) -> None:
    job_id = JOB_ID_TEMPLATE.format(user_id=user_id)
    scheduler.add_job(
        sync_user_emails,
        trigger=IntervalTrigger(hours=interval_hours),
        id=job_id,
        args=[user_id],
        replace_existing=True,
        misfire_grace_time=300,   # 5-min grace window if server was overloaded
    )

def _unregister_sync_job(user_id: int) -> None:
    job_id = JOB_ID_TEMPLATE.format(user_id=user_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
```

### Pattern 5: Daily Cleanup Job (fixed time)

**What:** A second APScheduler job (not per-user, global) runs once per day at 03:00 and deletes expired `EmailMetadata` rows.

**Example:**
```python
from apscheduler.triggers.cron import CronTrigger
from app.models.email_metadata import EmailMetadata
from datetime import datetime, timezone

def cleanup_expired_emails() -> None:
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        db.query(EmailMetadata).filter(
            EmailMetadata.delete_after <= now
        ).delete(synchronize_session=False)
        db.commit()

# Register once in lifespan startup:
scheduler.add_job(
    cleanup_expired_emails,
    trigger=CronTrigger(hour=3, minute=0),
    id="email_retention_cleanup",
    replace_existing=True,
)
```

### Pattern 6: PUT /api/gmail/settings Route

**What:** New route that accepts `{ sync_enabled: bool, sync_interval_hours: int | null }`, updates DB, and immediately registers or removes the APScheduler job.

**Example:**
```python
class SyncSettingsUpdate(BaseModel):
    sync_enabled: bool
    sync_interval_hours: Optional[int] = None

@router.put("/settings")
def update_sync_settings(
    body: SyncSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.sync_enabled and (not body.sync_interval_hours or body.sync_interval_hours < 1):
        raise HTTPException(status_code=422, detail="sync_interval_hours must be >= 1 when sync is enabled")
    current_user.sync_enabled = body.sync_enabled
    current_user.sync_interval_hours = body.sync_interval_hours
    db.commit()
    if body.sync_enabled:
        _register_sync_job(current_user.id, body.sync_interval_hours)
    else:
        _unregister_sync_job(current_user.id)
    return {"status": "ok", "sync_enabled": body.sync_enabled}
```

### Anti-Patterns to Avoid

- **Using `Depends(get_db)` in scheduler jobs:** FastAPI dependency injection is only available in request context. Scheduler jobs are invoked by a background thread — use `SessionLocal()` directly.
- **Using `@app.on_event("startup")`:** Deprecated in FastAPI 0.93+. Use `lifespan` context manager.
- **Running `_run_db_migrations()` at module import time (current state):** Currently in `main.py` at module level before `app = FastAPI(...)`. This works but must be moved inside `lifespan` startup once lifespan is added, to ensure predictable boot order (migrations before scheduler start). If left at module level alongside lifespan, migrations run twice on cold boot — once at import, once in lifespan.
- **Letting scheduler job exceptions propagate:** APScheduler catches job exceptions, but unhandled exceptions will cause the job to be silently skipped next time in some configurations. Always wrap the body in `try/except` and log errors.
- **Re-using `creds` object after `_get_credentials` returns:** After the tuple refactor, callers must use the returned `creds` from the tuple — do not re-call `_get_credentials` inside the same request.
- **Passing `encrypted_token` to `email_sync_service.sync()` after a refresh without persisting first:** If the token was refreshed, `user.gmail_token_encrypted` in-memory is stale. Persist the new token before calling `sync()`, or pass the new token explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scheduled background jobs | Custom thread + `time.sleep()` loop | APScheduler `BackgroundScheduler` | Handles missed fires, graceful shutdown, job deduplication, configurable grace periods |
| Job registration dedup | Check-then-add logic | `replace_existing=True` on `add_job` | APScheduler handles atomically |
| Cron-style daily run | Manual time calculation | `CronTrigger(hour=3, minute=0)` | Built-in, tested, DST-safe |

**Key insight:** APScheduler 3.x is a battle-tested scheduling library for this exact pattern (per-user jobs in a single process). Using raw threads would lose misfire handling, graceful shutdown, and the job registry.

---

## Common Pitfalls

### Pitfall 1: SQLite WAL write contention

**What goes wrong:** The APScheduler job commits to SQLite at the same time as an HTTP request (e.g., manual sync or settings update). SQLite WAL mode serialises writers — one of them will get `OperationalError: database is locked` if the wait times out.

**Why it happens:** This is a single-file SQLite limitation. WAL mode reduces (but does not eliminate) contention.

**How to avoid:** SQLAlchemy's default `NullPool` + short transactions minimise lock windows. Ensure scheduler job and route handlers both use short `commit()` calls rather than long-lived uncommitted transactions. The existing `check_same_thread=False` allows cross-thread access, which is correct for this pattern.

**Warning signs:** `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked` in backend logs during concurrent sync + manual action.

### Pitfall 2: `_run_db_migrations()` called at module import AND in lifespan

**What goes wrong:** Adding a `lifespan` while keeping the top-level `_run_db_migrations()` call in `main.py` causes migrations to run twice on every cold start. While Alembic is idempotent (it won't re-apply applied migrations), it adds unnecessary overhead and log noise.

**Why it happens:** The current `main.py` calls `_run_db_migrations()` at module level (line 29 in the read file, before `app = FastAPI(...)`). Once a lifespan is added, there is a temptation to call it again there.

**How to avoid:** Move the `_run_db_migrations()` call inside the lifespan startup block and remove it from the module level. The function is defined above the `app` object so moving the call is straightforward.

### Pitfall 3: Scheduler starts before DB is ready

**What goes wrong:** If `scheduler.start()` runs before `_run_db_migrations()`, the startup query to re-register jobs for `sync_enabled=True` users may run against an unmigrated schema (missing `sync_enabled` column), causing an `OperationalError`.

**How to avoid:** In lifespan, always call `_run_db_migrations()` before `scheduler.start()`.

### Pitfall 4: Token refresh not detected (None vs new_token confusion)

**What goes wrong:** Callers check `if new_token:` but forget that `crypto_service.encrypt(...)` always returns a bytes or str object — never falsy. The sentinel for "no refresh happened" must be explicitly `None`, not `""` or `b""`.

**How to avoid:** `_get_credentials()` returns `(creds, None)` when no refresh occurred and `(creds, <non-None string>)` when a refresh happened. Callers check `if new_token is not None:`.

### Pitfall 5: `sync_interval_hours` nullable with `sync_enabled=True`

**What goes wrong:** If a user somehow has `sync_enabled=True` but `sync_interval_hours=None` (e.g., direct DB edit or a race condition), `IntervalTrigger(hours=None)` raises a `TypeError`.

**How to avoid:** The `PUT /api/gmail/settings` route validates `sync_interval_hours >= 1` when `sync_enabled=True`. The startup job re-registration loop should also guard: `if user.sync_enabled and user.sync_interval_hours`.

### Pitfall 6: `email_sync_service.py` hardcodes `timedelta(days=30)`

**What goes wrong:** INFRA-03 requires `email_retention_days` to be configurable. The current code on line 42 of `email_sync_service.py` uses `timedelta(days=30)` literally.

**How to avoid:** Change line 42 to `timedelta(days=settings.email_retention_days)` and import `settings` at the top of the file. This is a one-line fix but easy to forget.

**Note:** `config.py` already has `email_retention_days: int = 30` — no config change needed, just fix the usage.

### Pitfall 7: Alembic `DateTime` vs `DateTime(timezone=True)` for `last_synced_at`

**What goes wrong:** SQLite stores all `DateTime` values as strings. If `timezone=True` is specified in SQLAlchemy but not handled consistently, comparisons in cleanup queries can fail or return unexpected results.

**How to avoid:** Use `sa.DateTime(timezone=True)` in the Alembic migration column definition to match the SQLAlchemy model column. Always store UTC via `datetime.now(timezone.utc)`. SQLite transparently preserves the UTC offset string.

---

## Code Examples

### Alembic migration template for new User columns

```python
# Source: established pattern from backend/alembic/versions/628c6541bc23_add_payment_source.py
"""add_user_sync_columns

Revision ID: <generated>
Revises: 628c6541bc23
Create Date: ...
"""
from alembic import op
import sqlalchemy as sa

revision = '<generated>'
down_revision = '628c6541bc23'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('sync_interval_hours', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_synced_at')
    op.drop_column('users', 'sync_interval_hours')
    op.drop_column('users', 'sync_enabled')
```

**Note:** SQLite does not support `ALTER COLUMN` or `NOT NULL` without a default for existing rows. Use `server_default='0'` (SQLite boolean is integer 0/1) so existing users get `sync_enabled=False`.

### IST timestamp display (frontend)

```javascript
// Source: D-10 in CONTEXT.md
function formatIST(isoString) {
  if (!isoString) return null
  return new Date(isoString).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })
  // Output: "5/4/2026, 11:23:45 am" (locale-dependent formatting)
}
```

The backend returns `last_synced_at` as an ISO 8601 UTC string. No backend timezone conversion is needed.

### GET /api/gmail/status extended response

```python
@router.get("/status")
def gmail_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": current_user.gmail_token_encrypted is not None,
        "user": current_user.username,
        "last_synced_at": current_user.last_synced_at.isoformat() if current_user.last_synced_at else None,
        "sync_enabled": current_user.sync_enabled,
        "sync_interval_hours": current_user.sync_interval_hours,
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | FastAPI `lifespan` context manager | FastAPI 0.93 (2023) | `on_event` still works but emits deprecation warning in 0.115.0 |
| `Base.metadata.create_all()` | `alembic upgrade head` via `_run_db_migrations()` | Phase 3 of this project | Already migrated — do not revert |
| APScheduler 4.x (async-first) | APScheduler 3.x `BackgroundScheduler` | APScheduler 4 is a rewrite (2024) | 4.x has a different API; project uses 3.11.2 (locked decision) |

**Deprecated/outdated in this project:**
- `@app.on_event("startup")` / `@app.on_event("shutdown")`: Do not use. Replaced by `lifespan` in FastAPI 0.93+.
- Module-level `_run_db_migrations()` call (current state in `main.py` line 29): Works but must be moved inside lifespan for correct boot ordering when scheduler is added.

---

## Runtime State Inventory

> This phase adds new DB columns but does not rename anything. No runtime state needs migration beyond the Alembic schema migration.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | SQLite `users` table — existing rows will gain 3 new columns | Alembic migration with `server_default='0'` for `sync_enabled`; nullable for the other two |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | `email_retention_days` env var — new, optional (already in `config.py` with default 30) | Document in `backend/.env.example`; no existing secrets need changing |
| Build artifacts | APScheduler not yet installed; not in `requirements.txt` | `pip install apscheduler==3.11.2` + add to `requirements.txt` |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All backend | Yes | 3.14.0 | — |
| APScheduler 3.11.2 | GMAIL-06, INFRA-04 | Not yet installed | — (3.11.2 available on PyPI, confirmed pure Python) | None — must install |
| FastAPI (lifespan API) | D-03 | Yes | 0.115.0 | — |
| SQLAlchemy | DB sessions in jobs | Yes | 2.0.36 | — |
| Alembic | New User columns | Yes | 1.14.0 | — |

**Missing dependencies with no fallback:**
- APScheduler 3.11.2 — must be installed in Wave 0 before any scheduler code is written. Command: `pip install apscheduler==3.11.2` from `backend/` with venv active.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && pytest tests/ -x -q` |
| Full suite command | `cd backend && pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GMAIL-05 | `_get_credentials()` returns new encrypted token after refresh | unit | `pytest tests/test_gmail_service.py -x -q` | No — Wave 0 |
| GMAIL-06 | `sync_user_emails()` job function opens own DB session + calls sync | unit (mock scheduler) | `pytest tests/test_scheduler.py -x -q` | No — Wave 0 |
| GMAIL-07 | `/api/gmail/status` response includes `last_synced_at` | unit (TestClient) | `pytest tests/test_gmail_routes.py::test_status_includes_last_synced_at -x` | No — Wave 0 |
| GMAIL-08 | Scheduler job logs error and does not re-raise on sync failure | unit | `pytest tests/test_scheduler.py::test_sync_job_catches_exception -x` | No — Wave 0 |
| GMAIL-10 | `PUT /api/gmail/settings` validates and registers job | unit (TestClient) | `pytest tests/test_gmail_routes.py::test_put_settings -x` | No — Wave 0 |
| INFRA-03 | `email_sync_service.sync()` uses `settings.email_retention_days` | unit | `pytest tests/test_email_sync_service.py::test_retention_days_from_settings -x` | No — Wave 0 |
| INFRA-04 | `cleanup_expired_emails()` deletes rows with `delete_after <= now` | unit | `pytest tests/test_scheduler.py::test_cleanup_job -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/ -x -q`
- **Per wave merge:** `cd backend && pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_gmail_service.py` — covers GMAIL-05 (token refresh return tuple)
- [ ] `tests/test_scheduler.py` — covers GMAIL-06, GMAIL-08, INFRA-04 (scheduler job functions)
- [ ] `tests/test_gmail_routes.py` — covers GMAIL-07, GMAIL-10 (updated and new routes)
- [ ] APScheduler install: `pip install apscheduler==3.11.2` + add to `requirements.txt`
- [ ] `tests/test_email_sync_service.py::test_retention_days_from_settings` — new test case within existing file (file exists)

---

## Open Questions

1. **`_get_service()` call chain after tuple refactor**
   - What we know: `_get_service()` calls `_get_credentials()` and discards the return value except for `creds`. After the refactor, `_get_service()` must also return the new encrypted token or pass it up.
   - What's unclear: `fetch_transaction_emails()` calls `_get_service()` — if we want the route handler to persist the refreshed token, `fetch_transaction_emails()` also needs to surface the new token.
   - Recommendation: Simplest fix — call `_get_credentials()` directly in the sync route and scheduler job (bypassing `_get_service()`), then build the service separately: `creds, new_token = _get_credentials(...)` followed by `service = build("gmail", "v1", credentials=creds)`. Alternatively, change `_get_service()` to also return the token. Either is valid; the plan should pick one approach and be consistent.

2. **No `conftest.py` fixtures for the scheduler tests**
   - What we know: Existing `conftest.py` has `in_memory_db` fixture for SQL tests and email sample fixtures. Scheduler tests will need a mock scheduler and mock `SessionLocal`.
   - What's unclear: Best approach for isolating scheduler jobs from a real DB in tests.
   - Recommendation: Use `pytest-mock` or `unittest.mock.patch` to mock `SessionLocal` and return the `in_memory_db` fixture session. APScheduler jobs are plain functions so they can be called directly in tests without starting the scheduler.

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection of `backend/app/main.py`, `backend/app/services/gmail_service.py`, `backend/app/services/email_sync_service.py`, `backend/app/api/routes/gmail.py`, `backend/app/models/user.py`, `backend/app/database.py`, `backend/app/config.py` — all live codebase facts
- `backend/alembic/versions/628c6541bc23_add_payment_source.py` — established migration pattern for this project
- `python -m pip index versions apscheduler` — confirmed 3.11.2 availability on PyPI from this machine (2026-04-05)
- Python 3.14.0 verified via `python --version` on the project machine
- APScheduler 3.x `BackgroundScheduler` + `IntervalTrigger` + `CronTrigger` API — stable across 3.x versions, confirmed unchanged since 3.9

### Secondary (MEDIUM confidence)

- FastAPI lifespan context manager API (FastAPI docs pattern) — confirmed in FastAPI 0.93+ changelog; deprecation of `on_event` well-documented
- SQLite WAL serialisation behaviour — documented in SQLite official docs; WAL reduces but does not eliminate write contention under concurrent access

### Tertiary (LOW confidence)

- None — all claims above are verifiable from live code or official library docs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — APScheduler 3.11.2 confirmed on PyPI from target machine; all other dependencies already in project
- Architecture: HIGH — derived from direct code inspection of entry points and established project patterns
- Pitfalls: HIGH — SQLite WAL limitation is a known documented constraint; other pitfalls are directly observable in the existing code (line 29 of main.py, line 42 of email_sync_service.py)

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable libraries; APScheduler 3.x API is not changing)
