---
phase: "06-analytics-trends"
plan: "02"
subsystem: "backend"
tags: ["spending-limit", "sqlite", "alembic", "fastapi", "pydantic"]
dependency_graph:
  requires:
    - "06-01"  # analytics router created in Plan 01
  provides:
    - "SpendingLimit table and CRUD endpoints"
    - "GET/PUT/DELETE /api/analytics/spending-limit"
  affects:
    - "06-03"  # frontend spending-limit UI will call these endpoints
tech_stack:
  added:
    - "app/models/spending_limit.py — SpendingLimit SQLAlchemy model"
    - "app/schemas/spending_limit.py — SpendingLimitOut, SpendingLimitUpsert Pydantic schemas"
    - "app/services/spending_limit_service.py — get/upsert/delete service functions"
  patterns:
    - "upsert via get-then-update (no ON CONFLICT — SQLite-compatible)"
    - "Decimal in PUT body, float in response (JSON-safe)"
    - "Idempotent DELETE returns 204 regardless of row existence"
key_files:
  created:
    - "backend/app/models/spending_limit.py"
    - "backend/alembic/versions/866afeee2c98_add_spending_limit.py"
    - "backend/app/schemas/spending_limit.py"
    - "backend/app/services/spending_limit_service.py"
    - "backend/tests/test_spending_limit.py"
  modified:
    - "backend/app/models/__init__.py"  # registered SpendingLimit
    - "backend/alembic/env.py"          # import spending_limit for autogenerate
    - "backend/app/api/routes/analytics.py"  # appended GET/PUT/DELETE /spending-limit
decisions:
  - "Decimal in SpendingLimitUpsert body, float in SpendingLimitOut response — Pydantic Field(gt=0) validates positivity; float is JSON-safe for the frontend"
  - "Upsert via get-then-update pattern (not ON CONFLICT DO UPDATE) — SQLite-compatible and consistent with existing service patterns (category_rule_service)"
  - "Idempotent DELETE returns 204 unconditionally — service returns bool for testing but route ignores it"
  - "Granularity type alias Granularity = Literal['daily','weekly','monthly','annual'] used in both schema and route params — single source of truth for validation"
metrics:
  duration: "8min"
  completed_date: "2026-04-29"
  tasks_completed: 2
  files_created: 5
  files_modified: 3
---

# Phase 6 Plan 02: SpendingLimit Backend Storage Summary

SpendingLimit table, Alembic migration, service layer, and CRUD API endpoints — simplified per-granularity spending limit storage replacing the deferred full GOAL feature.

## What Was Built

### SpendingLimit Model (`backend/app/models/spending_limit.py`)

SQLAlchemy model with 6 columns: `id`, `user_id` (FK users.id CASCADE), `granularity` (String 20), `amount` (Numeric 12,2), `created_at`, `updated_at`. Unique constraint `uq_spending_limit_user_granularity` on `(user_id, granularity)`.

### Alembic Migration (`866afeee2c98_add_spending_limit.py`)

- `down_revision = '139c02a97b09'` (category_rules migration)
- `op.create_table('spending_limits', ...)` with all columns and unique constraint
- `ix_spending_limits_id` index on primary key
- `downgrade()` drops the table

### Schemas (`backend/app/schemas/spending_limit.py`)

```python
Granularity = Literal["daily", "weekly", "monthly", "annual"]

class SpendingLimitOut:
    granularity: str
    amount: Optional[float] = None   # None when not set

class SpendingLimitUpsert:
    granularity: Granularity          # 422 on invalid value
    amount: Decimal = Field(gt=0)    # 422 on zero/negative
```

### Service Functions (`backend/app/services/spending_limit_service.py`)

| Function | Behavior |
|---|---|
| `get_spending_limit(db, user_id, granularity)` | Returns SpendingLimit row or None |
| `upsert_spending_limit(db, user_id, granularity, amount)` | Creates or updates; always commits |
| `delete_spending_limit(db, user_id, granularity)` | Returns True if deleted, False if absent |

### Endpoint Contracts (`/api/analytics/spending-limit`)

| Method | URL | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/analytics/spending-limit?granularity=monthly` | — | `{"granularity":"monthly","amount":30000.0}` or `{"granularity":"monthly","amount":null}` | 200 |
| PUT | `/api/analytics/spending-limit` | `{"granularity":"monthly","amount":30000}` | `{"granularity":"monthly","amount":30000.0}` | 200 |
| PUT | `/api/analytics/spending-limit` | `{"granularity":"monthly","amount":0}` | 422 validation error | 422 |
| PUT | `/api/analytics/spending-limit` | `{"granularity":"fortnightly","amount":1000}` | 422 validation error | 422 |
| DELETE | `/api/analytics/spending-limit?granularity=monthly` | — | (empty body) | 204 |
| GET/PUT/DELETE | `/api/analytics/spending-limit?granularity=invalid` | — | 422 validation error | 422 |

All endpoints scoped by `current_user.id` from JWT — user_id never accepted from request body or query params.

## Test Count

**10 tests total** in `backend/tests/test_spending_limit.py`:

### Task 1 — Model tests (5)
- `test_spending_limit_table_in_metadata` — Base.metadata includes spending_limits
- `test_spending_limit_insert` — all fields round-trip correctly
- `test_spending_limit_unique_constraint` — IntegrityError on duplicate (user_id, granularity)
- `test_spending_limit_different_granularities_allowed` — same user, different granularities both succeed
- `test_spending_limit_user_isolation` — different users with same granularity both succeed; filter returns correct row

### Task 2 — Service tests (5)
- `test_get_spending_limit_returns_none_when_absent`
- `test_upsert_spending_limit_creates_new`
- `test_upsert_spending_limit_updates_existing` — single row; updated_at >= created_at
- `test_delete_spending_limit_existing` — True returned, row removed
- `test_delete_spending_limit_idempotent` — False returned, no exception

**Full suite: 101 tests green** (10 new + 91 pre-existing).

## Key Decisions

1. **Decimal in, float out** — `SpendingLimitUpsert.amount` uses `Decimal` with `Field(gt=0)` for server-side validation. `SpendingLimitOut.amount` uses `float` for clean JSON serialization that the frontend can use directly.

2. **Upsert via get-then-update** — Uses query-then-update pattern (not raw SQL `ON CONFLICT`) to stay consistent with `upsert_rule_and_bulk_update` in `category_rule_service.py` and because SQLite's ORM-level upsert support is limited in SQLAlchemy 1.x style.

3. **Idempotent DELETE returns 204 unconditionally** — The service function returns a `bool` (useful for tests), but the route ignores it and always returns 204. This matches REST conventions for idempotent deletions.

4. **`Granularity` type alias in schemas** — A single `Literal` type alias shared between `SpendingLimitUpsert` and the route `Query(...)` parameter ensures one definition for allowed granularity values.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All endpoints are fully wired to the database.

## Self-Check

### Created files exist:
- [x] `backend/app/models/spending_limit.py` — FOUND
- [x] `backend/alembic/versions/866afeee2c98_add_spending_limit.py` — FOUND
- [x] `backend/app/schemas/spending_limit.py` — FOUND
- [x] `backend/app/services/spending_limit_service.py` — FOUND
- [x] `backend/tests/test_spending_limit.py` — FOUND

### Commits exist:
- [x] `f6f0183` — feat(06-02): SpendingLimit model, Alembic migration, 5 model tests
- [x] `32d4444` — feat(06-02): schemas, service, spending-limit CRUD routes, 5 service tests

## Self-Check: PASSED
