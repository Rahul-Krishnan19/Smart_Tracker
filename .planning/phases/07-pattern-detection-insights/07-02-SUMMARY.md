---
phase: 07-pattern-detection-insights
plan: 02
subsystem: backend-insights
tags: [anomaly-detection, subscription-detection, insights-feed, post-sync, api-routes]
dependency_graph:
  requires: [07-01]
  provides: [anomaly_service, subscription_service, insight_service, insights_orchestrator, /api/insights]
  affects: [email_sync_service, main.py]
tech_stack:
  added: []
  patterns: [generator-registry, idempotent-detection, post-sync-hook, error-isolation]
key_files:
  created:
    - backend/app/services/anomaly_service.py
    - backend/app/services/subscription_service.py
    - backend/app/services/insight_service.py
    - backend/app/services/insights_orchestrator.py
    - backend/app/api/routes/insights.py
    - backend/tests/test_anomaly_service.py
    - backend/tests/test_subscription_service.py
    - backend/tests/test_insight_service.py
    - backend/tests/test_insights_orchestrator.py
    - backend/tests/test_insights_routes.py
  modified:
    - backend/app/services/email_sync_service.py
    - backend/app/main.py
decisions:
  - "InsightService.regenerate uses today.date()+1day as upper bound for this_month_total to include same-day transactions"
  - "email_sync_service imports insights_orchestrator as module (not function) to enable patching in tests"
metrics:
  duration: 20min
  completed: "2026-05-08"
  tasks: 4
  files: 12
---

# Phase 7 Plan 02: Detection Services + Insights API Summary

**One-liner:** Rule-based anomaly/subscription/insight detection services with idempotent post-sync orchestration and 7-endpoint REST API, backed by 26 new tests.

## What Was Built

### Service Singletons

| Service | Module | Entry Method | Notes |
|---------|--------|-------------|-------|
| `anomaly_service` | `app.services.anomaly_service` | `detect(db, user_id, now=None)` | 5 rules, idempotent |
| `subscription_service` | `app.services.subscription_service` | `detect(db, user_id)` | Consecutive-month, D-07 |
| `insight_service` | `app.services.insight_service` | `regenerate(db, user_id, today=None)` | Priority cap, D-13/D-14 |
| `run_post_sync` | `app.services.insights_orchestrator` | `run_post_sync(db, user_id)` | Chains all 3, error-isolated |

### Anomaly Rules Implemented
1. `high_value` — amount > ANOMALY_HIGH_VALUE_THRESHOLD (5000)
2. `large_transaction` — amount > 3x category rolling avg (requires ≥2 months history)
3. `velocity_spike` — 3+ txs at same merchant within 24h OR daily spend > 3x rolling avg
4. `duplicate_like` — same merchant+amount within 48h
5. `missing_subscription` — active subscription with no tx this month (triggers after day 10)

### Endpoint Table

| Method | Path | Response |
|--------|------|----------|
| GET | /api/insights/anomalies | `List[AnomalyOut]` |
| PATCH | /api/insights/anomalies/{id} | `AnomalyOut` |
| GET | /api/insights/subscriptions | `SubscriptionsListOut` |
| PATCH | /api/insights/subscriptions/{id} | `SubscriptionOut` |
| GET | /api/insights/insights | `List[InsightOut]` |
| POST | /api/insights/insights/{id}/dismiss | `InsightOut` |
| GET | /api/insights/summary | `InsightsSummaryOut` |

### Post-Sync Wiring
Location: `backend/app/services/email_sync_service.py`, end of `EmailSyncService.sync()`, before `return summary`. Adds `summary["insights"]` dict with `{subscriptions, anomalies, insights}` counts.

### Test Files Added

| File | Tests | Coverage |
|------|-------|----------|
| `test_anomaly_service.py` | 9 | All 5 rules + idempotency |
| `test_subscription_service.py` | 4 | S1-S4 (create, dedup, reactivate, idempotent) |
| `test_insight_service.py` | 4 | I1-I4 (spend_pace, quiet_month, priority cap, dismissed preservation) |
| `test_insights_orchestrator.py` | 4 | O1-O3b (counts, error isolation, sync embedding, crash survival) |
| `test_insights_routes.py` | 9 | R1-R9 (all routes, ownership, 404s) |

**Total new tests: 30 | Full suite: 131 passed**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] InsightService this_month_total excluded same-day transactions**
- **Found during:** Task 2, test I1 (spend_pace)
- **Issue:** `_sum_in_range(month_start, today.date())` uses `< today.date()` which excludes transactions dated today
- **Fix:** Changed upper bound to `today.date() + timedelta(days=1)` to include today's transactions
- **Files modified:** `backend/app/services/insight_service.py`

**2. [Rule 1 - Bug] Test I2 included current month tx in history**
- **Found during:** Task 2, test I2 (quiet_month)
- **Issue:** Test added 10000 tx in month 5 (current month) making this_month_total = 11000, triggering spend_pace
- **Fix:** Changed test loop to range(1, 5) — history months only Jan-Apr
- **Files modified:** `backend/tests/test_insight_service.py`

**3. [Rule 1 - Bug] insights_orchestrator import not patchable in tests**
- **Found during:** Task 3, test O3b
- **Issue:** `from app.services.insights_orchestrator import run_post_sync` inside `sync()` creates a local binding that can't be patched at module level
- **Fix:** Changed to `from app.services import insights_orchestrator as _orch; _orch.run_post_sync(...)` — attribute access is patchable
- **Files modified:** `backend/app/services/email_sync_service.py`

## Known Stubs

None. All detection services are fully wired. The insights feed regenerates on every sync trigger.

## Self-Check: PASSED

Files verified:
- backend/app/services/anomaly_service.py — FOUND
- backend/app/services/subscription_service.py — FOUND
- backend/app/services/insight_service.py — FOUND
- backend/app/services/insights_orchestrator.py — FOUND
- backend/app/api/routes/insights.py — FOUND
- All 5 test files — FOUND

Commits verified:
- 97cd954 — feat(07-02): AnomalyService
- 39143cd — feat(07-02): SubscriptionService + InsightService
- 3a40350 — feat(07-02): insights_orchestrator + post-sync hook
- 90952bb — feat(07-02): /api/insights routes
