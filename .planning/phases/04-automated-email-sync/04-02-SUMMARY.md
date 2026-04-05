---
phase: 04-automated-email-sync
plan: "02"
subsystem: backend
tags: [gmail, apscheduler, scheduler, lifespan, fastapi, testing]
dependency_graph:
  requires:
    - User.sync_enabled / sync_interval_hours / last_synced_at columns (04-01)
    - _get_credentials() returning tuple[Credentials, str | None] (04-01)
    - apscheduler==3.11.2 installed (04-01)
  provides:
    - backend/app/scheduler.py with BackgroundScheduler, job functions, registration helpers
    - FastAPI lifespan with scheduler start/stop and DB migrations
    - PUT /api/gmail/settings route wired to scheduler
    - All Phase 4 scheduler/settings tests active and green
  affects:
    - backend/app/main.py
    - backend/app/api/routes/gmail.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_gmail_settings.py
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN for scheduler functions and settings route
    - APScheduler BackgroundScheduler with IntervalTrigger and CronTrigger
    - FastAPI asynccontextmanager lifespan (replaces deprecated @app.on_event)
    - SQLAlchemy 2.0 context manager sessions (with SessionLocal() as db)
key_files:
  created:
    - backend/app/scheduler.py
  modified:
    - backend/app/main.py
    - backend/app/api/routes/gmail.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_gmail_settings.py
decisions:
  - "SQLAlchemy 2.0 sessionmaker supports context manager — used 'with SessionLocal() as db' pattern in scheduler"
  - "module-level _run_db_migrations() call moved into lifespan startup to avoid running on every import"
  - "scheduler.shutdown(wait=False) in lifespan shutdown avoids blocking app termination"
  - "register_startup_jobs() re-registers per-user jobs from DB on restart (in-memory job store per D-04)"
  - "cleanup_expired_emails uses delete_after <= now comparison with synchronize_session=False for efficiency"
metrics:
  duration_seconds: 360
  completed_date: "2026-04-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
---

# Phase 04 Plan 02: APScheduler Background Sync + Settings Route Summary

**One-liner:** APScheduler BackgroundScheduler wired to FastAPI lifespan, per-user sync jobs and daily 03:00 cleanup job registered at startup, PUT /api/gmail/settings route with interval validation calls register/unregister helpers — 42 tests all green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create scheduler module + lifespan integration | 91e7642 | scheduler.py (new), main.py, test_scheduler.py |
| 2 | PUT /api/gmail/settings route + settings tests | 28ed96e | gmail.py routes, test_gmail_settings.py |

## Changes Made

### Scheduler Module (GMAIL-06, GMAIL-08, INFRA-04)

New file `backend/app/scheduler.py` exports:

- `scheduler` — `BackgroundScheduler()` instance (single shared instance)
- `sync_user_emails(user_id)` — opens own DB session, fetches user, calls `gmail_service._get_credentials`, persists refreshed token if returned, calls `email_sync_service.sync`, sets `last_synced_at` to UTC now. Catches ALL exceptions and logs them without re-raising (GMAIL-08).
- `cleanup_expired_emails()` — deletes `EmailMetadata` rows where `delete_after <= now` via bulk `DELETE`. Runs daily at 03:00 (INFRA-04).
- `register_sync_job(user_id, interval_hours)` — adds `IntervalTrigger` job with ID `gmail_sync_user_{user_id}`, `replace_existing=True`, `misfire_grace_time=300`.
- `unregister_sync_job(user_id)` — checks if job exists before removing.
- `register_startup_jobs()` — queries DB for all users with `sync_enabled=True` and `sync_interval_hours IS NOT NULL`, registers their jobs, then registers the daily cleanup cron job.

### FastAPI Lifespan Integration (D-03)

`backend/app/main.py` changes:
- Added `from contextlib import asynccontextmanager`
- Added `from app.scheduler import scheduler, register_startup_jobs`
- Replaced module-level `_run_db_migrations()` call with `@asynccontextmanager async def lifespan(app)` that calls `_run_db_migrations()`, `scheduler.start()`, `register_startup_jobs()` on startup and `scheduler.shutdown(wait=False)` on shutdown
- Added `lifespan=lifespan` to `FastAPI(...)` constructor

### PUT /api/gmail/settings Route (GMAIL-10)

`backend/app/api/routes/gmail.py` additions:
- Import `from typing import Optional`
- Import `from app.scheduler import register_sync_job, unregister_sync_job`
- New Pydantic model `SyncSettingsUpdate(sync_enabled: bool, sync_interval_hours: Optional[int] = None)`
- New route `PUT /settings` at `update_sync_settings()`:
  - Validates `sync_interval_hours >= 1` when `sync_enabled=True`, raises HTTPException 422 otherwise
  - Updates `current_user.sync_enabled` and `sync_interval_hours` (sets to None when disabling)
  - Calls `register_sync_job` (enable) or `unregister_sync_job` (disable)
  - Returns `{"status": "ok", "sync_enabled": bool, "sync_interval_hours": int|null}`

### Tests Activated

`backend/tests/test_scheduler.py` — all skip decorators removed, 6 real tests:
- `TestSyncUserEmails`: calls sync service, persists refreshed token, catches exceptions
- `TestCleanupExpiredEmails`: deletes expired rows, keeps fresh rows (uses `in_memory_db` fixture with dummy User row)
- `TestJobRegistration`: `register_sync_job` uses correct job ID and `replace_existing=True`, `unregister_sync_job` calls `remove_job`

`backend/tests/test_gmail_settings.py` — all skip decorators removed, 5 real tests:
- `TestPutSyncSettings`: enables sync (calls register), disables sync (calls unregister), rejects interval=0
- `TestStatusExtended`: status includes `last_synced_at`, status returns null for never-synced user

## Test Results

```
42 passed, 2123 warnings in 1.80s
```

All 42 tests pass. No skipped tests remain for Plans 01 or 02.

## Deviations from Plan

None — plan executed exactly as written.

### Key Implementation Notes

The plan mentioned checking if `SessionLocal` supports context manager protocol. SQLAlchemy 2.0.36 is installed, which supports `with sessionmaker()() as db:` natively. The `with SessionLocal() as db:` pattern was used as specified.

The `in_memory_db` fixture from conftest.py does not insert a User row, so the cleanup test added a dummy `User(id=1, ...)` row before inserting `EmailMetadata` rows to satisfy the FK constraint.

## Known Stubs

None — all Phase 4 stubs from Plan 01 have been activated and implemented.

## Self-Check: PASSED

Files verified:
- `backend/app/scheduler.py` — EXISTS, contains `scheduler`, `sync_user_emails`, `cleanup_expired_emails`, `register_sync_job`, `unregister_sync_job`, `register_startup_jobs`
- `backend/app/main.py` — contains `async def lifespan`, `scheduler.start()`, `scheduler.shutdown(wait=False)`, `lifespan=lifespan`
- `backend/app/api/routes/gmail.py` — contains `SyncSettingsUpdate`, `update_sync_settings`, `register_sync_job`, `unregister_sync_job` imports
- `backend/tests/test_scheduler.py` — 6 active tests, no skip decorators
- `backend/tests/test_gmail_settings.py` — 5 active tests, no skip decorators

Commits verified:
- `91e7642` — feat(04-02): add APScheduler module and FastAPI lifespan integration
- `28ed96e` — feat(04-02): add PUT /api/gmail/settings route and settings tests
