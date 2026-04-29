---
phase: 06-analytics-trends
plan: "01"
subsystem: backend
tags: [analytics, trend, aggregation, tdd, fastapi, sqlalchemy]
dependency_graph:
  requires: []
  provides:
    - GET /api/analytics/trend endpoint
    - TrendService.get_trend() and compute_pct_change()
    - TrendItem / TrendResponse Pydantic schemas
  affects:
    - backend/app/main.py (router registration)
tech_stack:
  added: []
  patterns:
    - SQLAlchemy func.strftime() for time-period grouping
    - Two-pass SQL query (periods + category totals)
    - TDD RED/GREEN cycle with in_memory_db fixture
key_files:
  created:
    - backend/app/services/trend_service.py
    - backend/app/schemas/analytics.py
    - backend/app/api/routes/analytics.py
    - backend/tests/test_trend_service.py
  modified:
    - backend/app/main.py
decisions:
  - Weekly period_start derived from Monday of min_date (data-driven) — avoids SQLite %W vs ISO week mismatch
  - category_totals computed in a second SQL pass grouped by (period_key, category) — always included in response; frontend ignores when overlay off
  - get_trend() returns plain dict (not Pydantic model) — route handler wraps in TrendResponse for serialization
  - previous_total uses equivalent prior-period SUM query (delta = date_to - date_from + 1 day), zeroed when date_from/date_to not both supplied
  - No TestClient integration tests — codebase uses direct-function-call pattern; route verified via python -c smoke check
metrics:
  duration: "4 min"
  completed_date: "2026-04-29"
  tasks_completed: 3
  files_changed: 5
---

# Phase 6 Plan 1: Trend Service Backend Summary

**One-liner:** SQLAlchemy strftime-grouped trend aggregation service with daily/weekly/monthly/annual granularity, category_totals overlay, and previous-period pct_change — all in a single `GET /api/analytics/trend` endpoint.

## What Was Built

### backend/app/services/trend_service.py
- `GRANULARITY_FORMAT` constant: `{"daily": "%Y-%m-%d", "weekly": "%Y-W%W", "monthly": "%Y-%m", "annual": "%Y"}`
- `TrendService.get_trend(db, user_id, granularity, date_from, date_to, payment_source) -> dict`
  - Main SQL pass: `func.strftime(fmt, transaction_date)` grouped by period, ordered ascending
  - Second SQL pass: `(period_key, category)` grouping for `category_totals`
  - `_period_boundaries()`: true calendar bounds for monthly/annual/daily; Monday-of-min-date bounds for weekly
  - `_period_label()`: human-readable labels (e.g. "Apr 2026", "Wk Apr 13", "Apr 15", "2026")
  - previous_total via equivalent prior-period SUM query
- `TrendService.compute_pct_change(current, previous) -> Optional[float]`: returns None when previous == 0

### backend/app/schemas/analytics.py
- `TrendItem`: period_label, period_start, period_end, total, count, category_totals
- `TrendResponse`: trend, granularity, current_total, previous_total, pct_change

### backend/app/api/routes/analytics.py
- `GET /trend` route with 422 guard on unknown granularity
- Auth via `get_current_user` Depends; DB via `get_db` Depends

### backend/app/main.py
- Added `analytics` to route imports and registered `analytics.router` under `/api/analytics`

### backend/tests/test_trend_service.py
- 13 unit tests covering all four granularities, category_totals, user isolation, payment_source filter, pct_change, and empty ranges

## Endpoint Contract

**Request:**
```
GET /api/analytics/trend
  ?granularity=monthly      # daily | weekly | monthly | annual
  &date_from=2026-04-01     # ISO date, inclusive
  &date_to=2026-04-30       # ISO date, inclusive
  &payment_source=HDFC+CC   # optional
Authorization: Bearer <jwt>
```

**Response (TrendResponse):**
```json
{
  "trend": [
    {
      "period_label": "Apr 2026",
      "period_start": "2026-04-01",
      "period_end":   "2026-04-30",
      "total":        15000.0,
      "count":        23,
      "category_totals": {
        "Food & Dining": 4500.0,
        "Shopping":      6000.0,
        "Transport":     2500.0
      }
    }
  ],
  "granularity":    "monthly",
  "current_total":  15000.0,
  "previous_total": 12000.0,
  "pct_change":     25.0
}
```

## Test Counts

| Suite | Count | Result |
|-------|-------|--------|
| test_trend_service.py | 13 | All pass |
| Full suite (tests/) | 91 | All pass |

## Decisions Made

1. **Weekly bounds — data-driven Monday:** SQLite `%W` and Python `isocalendar()` use different week-numbering systems. Using `min_date - timedelta(days=min_date.weekday())` for period_start is safe and accurate.

2. **category_totals always included:** A second SQL pass always computes per-category breakdown. Frontend uses it for ANA-04 category overlay; ignores it when overlay is off. Avoids need for a separate endpoint.

3. **No TestClient integration tests:** The codebase uses direct function-call style tests (confirmed by reading all test files). HTTP-level route correctness verified via `python -c` smoke check.

4. **get_trend returns dict, not Pydantic model:** Route handler wraps the dict in TrendResponse for FastAPI serialization — cleaner than having the service depend on Pydantic.

## Deviations from Plan

None — plan executed exactly as written. The plan correctly anticipated the weekly pitfall and prescribed the data-driven Monday approach.

## Known Stubs

None. All data flows from the database through to the API response. No hardcoded values.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/app/services/trend_service.py | FOUND |
| backend/app/schemas/analytics.py | FOUND |
| backend/app/api/routes/analytics.py | FOUND |
| backend/tests/test_trend_service.py | FOUND |
| Commit b496562 (TDD RED) | FOUND |
| Commit 3edf88a (TDD GREEN) | FOUND |
| Commit 6c7e506 (route wired) | FOUND |
