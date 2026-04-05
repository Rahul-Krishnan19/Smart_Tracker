---
phase: 04-automated-email-sync
plan: "01"
subsystem: backend
tags: [gmail, oauth, apscheduler, alembic, testing, token-refresh]
dependency_graph:
  requires: []
  provides:
    - User.sync_enabled / sync_interval_hours / last_synced_at columns (schema)
    - _get_credentials() returning tuple[Credentials, str | None]
    - POST /api/gmail/sync persisting refreshed tokens and setting last_synced_at
    - GET /api/gmail/status returning sync fields
    - apscheduler==3.11.2 installed
    - Test stubs for all Phase 4 requirements
  affects:
    - backend/app/services/gmail_service.py
    - backend/app/services/email_sync_service.py
    - backend/app/api/routes/gmail.py
    - backend/app/models/user.py
tech_stack:
  added:
    - apscheduler==3.11.2 (tzlocal, tzdata dependencies)
  patterns:
    - TDD RED/GREEN for _get_credentials tuple and retention days
    - Alembic migration chaining (down_revision=628c6541bc23)
    - pytest.mark.skip stubs for future plans
key_files:
  created:
    - backend/alembic/versions/a3f7c92d1b45_add_user_sync_columns.py
    - backend/tests/test_gmail_service.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_gmail_settings.py
  modified:
    - backend/requirements.txt
    - backend/app/models/user.py
    - backend/app/services/gmail_service.py
    - backend/app/services/email_sync_service.py
    - backend/app/api/routes/gmail.py
    - backend/tests/test_email_sync_service.py
decisions:
  - "APScheduler 3.11.2 installed; no C compilation needed on Python 3.14"
  - "_get_credentials returns (Credentials, str | None) — callers must unpack and persist new_token if non-None"
  - "sync route persists refreshed token before calling email_sync_service.sync() to avoid using stale token"
  - "last_synced_at set after successful sync (both manual and later auto-sync)"
  - "Alembic migration a3f7c92d1b45 chains from 628c6541bc23; applied cleanly on existing SQLite DB"
metrics:
  duration_seconds: 295
  completed_date: "2026-04-05"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 6
---

# Phase 04 Plan 01: Schema Foundation + Token Refresh Fix Summary

**One-liner:** APScheduler installed, User sync columns added via Alembic, `_get_credentials` returns `(Credentials, new_encrypted_or_None)` tuple, hardcoded 30-day retention replaced with `settings.email_retention_days`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install APScheduler + User model columns + Alembic migration + test stubs | 79725b1 | requirements.txt, user.py, a3f7c92d1b45 migration, 3 new test files, test_email_sync_service.py |
| 2 | Fix token refresh tuple + fix hardcoded retention days (TDD GREEN) | 173afa7 | gmail_service.py, email_sync_service.py, gmail.py routes, test files |

## Changes Made

### APScheduler Installation
- `apscheduler==3.11.2` added to `backend/requirements.txt` under Gmail API group
- Installed with `pip install` (also installs `tzlocal` and `tzdata` dependencies)
- Confirmed importable: `python -c "import apscheduler; print(apscheduler.__version__)"` → `3.11.2`

### User Model (GMAIL-06, D-06)
Three new columns added to `backend/app/models/user.py` after `gmail_token_encrypted`:
- `sync_enabled = Column(Boolean, default=False, nullable=False, server_default='0')`
- `sync_interval_hours = Column(Integer, nullable=True)`
- `last_synced_at = Column(DateTime(timezone=True), nullable=True)`

### Alembic Migration
- File: `backend/alembic/versions/a3f7c92d1b45_add_user_sync_columns.py`
- `down_revision = '628c6541bc23'` (chains from add_payment_source migration)
- Three `op.add_column` calls in upgrade, three `op.drop_column` in downgrade
- Applied cleanly: `alembic upgrade head` succeeded on existing SQLite DB

### Gmail Token Refresh Fix (GMAIL-05, D-13, D-14)
`backend/app/services/gmail_service.py`:
- `_get_credentials` return type changed from `Credentials` to `tuple[Credentials, str | None]`
- After `creds.refresh(Request())` succeeds, re-encrypts refreshed token and returns as second element
- Returns `(creds, None)` when no refresh needed
- `_get_service` updated to unpack: `creds, _ = self._get_credentials(encrypted_token)`

`backend/app/api/routes/gmail.py`:
- `POST /api/gmail/sync`: calls `_get_credentials` before sync, persists `new_token` if non-None, sets `last_synced_at` after successful sync
- `GET /api/gmail/status`: now returns `last_synced_at`, `sync_enabled`, `sync_interval_hours`
- Added `from datetime import datetime, timezone` import

### Email Retention Fix (INFRA-03, D-16)
`backend/app/services/email_sync_service.py`:
- Added `from app.config import settings` import
- Line 42: `timedelta(days=30)` → `timedelta(days=settings.email_retention_days)`
- `settings.email_retention_days` defaults to `30`, configurable via `.env`

### Test Stubs (Phase 4 Nyquist Compliance)
- `backend/tests/test_gmail_service.py` — 3 active tests (all GREEN after Task 2)
- `backend/tests/test_scheduler.py` — 4 stubs marked `@pytest.mark.skip(reason="Awaiting scheduler implementation in Plan 02")`
- `backend/tests/test_gmail_settings.py` — 4 stubs marked `@pytest.mark.skip(reason="Awaiting settings route in Plan 02")`
- `backend/tests/test_email_sync_service.py` — `test_retention_days_from_settings` added and now active (GREEN)

## Test Results

```
31 passed, 8 skipped, 1868 warnings in 1.08s
```

- 3 new gmail_service tests PASS (token refresh tuple)
- 1 new retention test PASSES (settings.email_retention_days)
- 8 plan 02/03 stubs SKIPPED (not FAILED)
- All 27 existing tests continue to PASS

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following stubs are intentional and tracked for Plan 02 implementation:

| File | Test | Reason |
|------|------|--------|
| `tests/test_scheduler.py` | 4 tests | APScheduler jobs implemented in Plan 02 |
| `tests/test_gmail_settings.py` | 4 tests | `PUT /api/gmail/settings` route implemented in Plan 02 |

## Self-Check: PASSED

Files verified:
- `backend/alembic/versions/a3f7c92d1b45_add_user_sync_columns.py` — EXISTS
- `backend/app/models/user.py` contains `sync_enabled` — CONFIRMED
- `backend/app/services/gmail_service.py` contains `tuple` return — CONFIRMED
- `backend/tests/test_gmail_service.py` contains `test_get_credentials` — CONFIRMED
- `backend/tests/test_scheduler.py` contains `test_sync` — CONFIRMED
- `backend/tests/test_gmail_settings.py` contains `test_put_settings` — CONFIRMED

Commits verified:
- `79725b1` — feat(04-01): install APScheduler, add User sync columns, create test stubs
- `307162e` — test(04-01): add failing tests for _get_credentials tuple return (RED)
- `173afa7` — feat(04-01): fix token refresh tuple return + fix hardcoded retention days
