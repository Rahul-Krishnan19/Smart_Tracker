---
phase: 07-pattern-detection-insights
plan: "01"
subsystem: backend/models+schemas+migration
tags: [models, schemas, alembic, sqlite, insights, anomalies, subscriptions]
dependency_graph:
  requires: [06-02]
  provides: [Anomaly ORM, Subscription ORM, Insight ORM, insights_config, pydantic schemas, DB migration b1f4e7a2c901]
  affects: [07-02, 07-03]
tech_stack:
  added: []
  patterns: [SQLAlchemy ORM, Pydantic v2 ConfigDict, Alembic migration]
key_files:
  created:
    - backend/app/services/insights_config.py
    - backend/app/models/anomaly.py
    - backend/app/models/subscription.py
    - backend/app/models/insight.py
    - backend/app/schemas/insights.py
    - backend/app/schemas/__init__.py
    - backend/alembic/versions/20260429_add_insights_tables.py
  modified:
    - backend/app/models/__init__.py
decisions:
  - "transaction_id is nullable on Anomaly to support missing_subscription rule (no transaction to link)"
  - "UniqueConstraint on (user_id, merchant) prevents duplicate subscription rows per user"
  - "ANOMALY_SEVERITY dict centralizes rule-to-severity mapping so InsightService never hardcodes strings"
metrics:
  duration: 10min
  completed: "2026-04-29"
---

# Phase 7 Plan 01: Insights DB Foundation Summary

DB foundation for Phase 7 pattern detection — three new SQLite tables, ORM models, pydantic schemas, and threshold constants module.

## What Was Built

### Constants Module (insights_config.py)

13 module-level constants + ANOMALY_SEVERITY dict + INSIGHT_PRIORITY_ORDER list:

- `ANOMALY_LARGE_TX_MULTIPLIER = 3.0`
- `ANOMALY_HIGH_VALUE_THRESHOLD = Decimal("5000")`
- `ANOMALY_VELOCITY_WINDOW_HOURS = 24`
- `ANOMALY_VELOCITY_MIN_COUNT = 3`
- `ANOMALY_DAILY_SPEND_MULTIPLIER = 3.0`
- `ANOMALY_DUPLICATE_WINDOW_HOURS = 48`
- `ANOMALY_MIN_HISTORY_MONTHS = 2`
- `SUBSCRIPTION_MIN_CONSECUTIVE_MONTHS = 2`
- `SUBSCRIPTION_MAX_DISTINCT_AMOUNTS_PER_MONTH = 2`
- `MISSING_SUBSCRIPTION_TRIGGER_DAY = 10`
- `INSIGHTS_MAX_PER_BATCH = 5`
- `QUIET_MONTH_BELOW_AVG_THRESHOLD = 0.20`
- `ANOMALY_SEVERITY` dict (5 rules mapped to low/medium/high)
- `INSIGHT_PRIORITY_ORDER` list (4 insight types)

### ORM Models

| Class | Table | Key Columns |
|-------|-------|-------------|
| Anomaly | anomalies | id, user_id, transaction_id (nullable FK), rule_name, severity, status, detected_at, dismissed_at, notes |
| Subscription | subscriptions | id, user_id, merchant, typical_amount, status, first_seen_month, last_seen_month, canceled_at, created_at, updated_at; UniqueConstraint(user_id, merchant) |
| Insight | insights | id, user_id, insight_type, title, body, status, generated_at, dismissed_at |

### Pydantic Schemas (8 classes)

- `AnomalyOut` — response model for anomaly rows
- `AnomalyStatusUpdate` — PATCH body (dismissed|investigating only)
- `SubscriptionOut` — response model for subscription rows
- `SubscriptionStatusUpdate` — PATCH body (active|canceled)
- `SubscriptionsListOut` — list response with estimated_monthly_total
- `InsightOut` — response model for insight rows
- `InsightsSummaryOut` — nav badge shape (anomaly_count: int)

### Alembic Migration

- **Revision:** `b1f4e7a2c901`
- **Down revision:** `866afeee2c98`
- Creates all 3 tables with FKs, indexes, server defaults
- Applied; all 3 tables confirmed in expense_tracker.db

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- 101 tests pass (pytest -x, no regressions)
- `alembic current` shows `b1f4e7a2c901 (head)`
- All 3 tables present in SQLite DB

## Self-Check: PASSED

- `backend/app/services/insights_config.py` exists (commit 89f0c52)
- `backend/app/models/anomaly.py` exists (commit 451486d)
- `backend/app/models/subscription.py` exists (commit 451486d)
- `backend/app/models/insight.py` exists (commit 451486d)
- `backend/app/schemas/insights.py` exists (commit 2c204ea)
- `backend/alembic/versions/20260429_add_insights_tables.py` exists (commit 2c204ea)
- Migration applied: b1f4e7a2c901 confirmed as alembic head
