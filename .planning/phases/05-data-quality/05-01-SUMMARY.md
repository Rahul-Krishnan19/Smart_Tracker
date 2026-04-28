---
phase: 05-data-quality
plan: 01
subsystem: api, database
tags: [fastapi, sqlalchemy, alembic, sqlite, pydantic, csv-export, category-rules]

# Dependency graph
requires:
  - phase: 04-automated-email-sync
    provides: email_sync_service.py with parsed transactions, payment_source field, scheduler

provides:
  - CategoryRule SQLAlchemy model with Alembic migration
  - apply_user_rules() and upsert_rule_and_bulk_update() services
  - Extended TransactionFilters (payment_source, min_amount, max_amount)
  - TransactionOut with payment_source field
  - TransactionCategoryUpdate and BulkCategorizeRequest schemas
  - Extended CATEGORIES list (12 entries, 3 new)
  - New API routes: payment-sources, merchants, merchant-breakdown, export, bulk-categorize, /{id}/category
  - _build_filter_query() helper powering list/summary/export/merchant-breakdown
  - apply_user_rules integration in email_sync_service post-parse
  - CSV export via StreamingResponse
  - 77 total tests green (35 new + 42 existing)

affects:
  - 05-data-quality/05-02 (transaction table UI depends on new filter params and endpoints)
  - 05-data-quality/05-03 (merchant analytics UI depends on /merchant-breakdown endpoint)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - _build_filter_query() helper centralizes all filter logic, reused by list/summary/export/merchant-breakdown
    - apply_user_rules() as a post-parse override hook — categorize() stays stateless (D-04)
    - upsert_rule_and_bulk_update() uses a single db.commit() for atomicity
    - Static API routes always registered before /{tx_id} to prevent path conflicts

key-files:
  created:
    - backend/app/models/category_rule.py
    - backend/app/services/category_rule_service.py
    - backend/alembic/versions/139c02a97b09_add_category_rules.py
    - backend/tests/test_category_rules.py
    - backend/tests/test_transaction_filters.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/schemas/transaction.py
    - backend/app/services/transaction_service.py
    - backend/app/api/routes/transactions.py
    - backend/app/services/email_sync_service.py
    - backend/alembic/env.py

key-decisions:
  - "CategoryRule only supports match_type=contains in Phase 5 (exact/starts_with/regex deferred per D-03)"
  - "_build_filter_query() helper added to TransactionService to DRY up all filter conditions"
  - "get_summary() refactored to accept TransactionFilters so summary respects same filters as list"
  - "Static API routes (payment-sources, merchants, etc.) registered before /{tx_id} to avoid FastAPI path conflicts"
  - "upsert_rule_and_bulk_update stores keyword as merchant.lower() for case-insensitive matching"
  - "apply_user_rules import moved to top of email_sync_service.py (not deferred import)"

patterns-established:
  - "Post-parse category override pattern: apply_user_rules() called before Transaction creation in email_sync"
  - "Route ordering discipline: all static-path GET routes before /{tx_id} dynamic route"
  - "Filter helper pattern: _build_filter_query() returns SQLAlchemy Query, all filter methods reuse it"

requirements-completed:
  - TXN-05
  - TXN-07
  - TXN-08
  - TXN-10
  - TXN-11
  - TXN-12
  - CAT-03
  - CAT-04
  - CAT-05
  - CAT-06
  - PAY-02
  - PAY-05
  - ANA-07
  - ANA-09
  - TXN-09
  - TXN-13

# Metrics
duration: 11min
completed: 2026-04-28
---

# Phase 5 Plan 01: Data Quality Backend Summary

**CategoryRule model + migration, 6 new API endpoints (payment-sources, merchants, merchant-breakdown, export, bulk-categorize, category re-assign), extended filters, and apply_user_rules integration in email sync**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-28T05:37:26Z
- **Completed:** 2026-04-28T05:48:09Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- CategoryRule SQLAlchemy model with Alembic migration (category_rules table created in DB)
- apply_user_rules() and upsert_rule_and_bulk_update() services for DB-backed keyword rules
- CATEGORIES extended from 9 to 12 entries (Subscriptions, Utilities, Travel added before Others)
- TransactionFilters extended with payment_source, min_amount, max_amount; TransactionOut gets payment_source
- Two new schemas: TransactionCategoryUpdate (with category validator) and BulkCategorizeRequest
- _build_filter_query() helper powers list(), get_summary(), export(), get_merchant_breakdown()
- 6 new API routes all registered before /{tx_id}: payment-sources, merchants, merchant-breakdown, export, bulk-categorize, /{id}/category
- CSV export via StreamingResponse with all filter params
- apply_user_rules() integrated into email_sync_service — user rules override parser categories at import time
- 77 total tests green (35 new: 21 category_rules + 14 transaction_filters)

## Task Commits

Each task was committed atomically:

1. **Task 1: Models, migration, schemas, and category rule service** - `557111a` (feat)
2. **Task 2: Extended transaction service, new API routes, and CSV export** - `7f63d24` (feat)

**Plan metadata:** (to be committed with SUMMARY.md)

_Note: TDD tasks have RED verification then GREEN implementation per task_

## Files Created/Modified

- `backend/app/models/category_rule.py` - CategoryRule ORM model (category_rules table, user_id FK, keyword, match_type, category)
- `backend/alembic/versions/139c02a97b09_add_category_rules.py` - Alembic migration creating category_rules table
- `backend/app/models/__init__.py` - Added CategoryRule import
- `backend/alembic/env.py` - Added category_rule to model imports for autogenerate
- `backend/app/schemas/transaction.py` - Extended TransactionOut, TransactionFilters; added TransactionCategoryUpdate, BulkCategorizeRequest
- `backend/app/services/category_rule_service.py` - apply_user_rules() and upsert_rule_and_bulk_update()
- `backend/app/services/transaction_service.py` - _build_filter_query() helper, extended list/get_summary, new export/get_merchant_breakdown/bulk_categorize methods
- `backend/app/api/routes/transactions.py` - 6 new routes + updated list/summary filter params
- `backend/app/services/email_sync_service.py` - apply_user_rules() call post-parse with import at top
- `backend/tests/test_category_rules.py` - 21 tests for CategoryRule, apply_user_rules, upsert, schema extensions
- `backend/tests/test_transaction_filters.py` - 14 tests for filter logic, summary, export, merchant breakdown, bulk categorize

## Decisions Made

- `_build_filter_query()` helper added to `TransactionService` to centralize all filter conditions, avoiding duplication across list/summary/export/merchant-breakdown
- `get_summary()` refactored to accept `TransactionFilters` instead of individual date params — summary now respects payment_source and amount range (TXN-07)
- `upsert_rule_and_bulk_update()` stores keyword as `merchant.lower()` and searches case-insensitively; a single `db.commit()` keeps rule + transaction update atomic
- Static API routes all placed before `/{tx_id}` in routes file to prevent FastAPI path conflict (critical for FastAPI path matching semantics)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed User field names in test helper**
- **Found during:** Task 1 (TestUpsertRuleAndBulkUpdate tests)
- **Issue:** Test's `_make_user()` helper used `hashed_password`, `totp_secret`, `totp_verified` but the actual User model uses `password_hash`, `totp_secret_encrypted`, `totp_enrolled`
- **Fix:** Updated `_make_user()` in `test_category_rules.py` to use correct field names
- **Files modified:** backend/tests/test_category_rules.py
- **Verification:** All 21 test_category_rules.py tests pass after fix
- **Committed in:** 557111a (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test fixture field names)
**Impact on plan:** Required for tests to pass. No scope creep. The User model field names `password_hash`/`totp_secret_encrypted`/`totp_enrolled` differ from what the test helper assumed.

## Issues Encountered

None beyond the test fixture field name mismatch (auto-fixed above).

## User Setup Required

None - all changes are backend-only with automated migration.

## Next Phase Readiness

- All backend APIs ready for 05-02 (transaction table UI) and 05-03 (merchant analytics UI)
- payment-sources endpoint provides dropdown data for filter UI
- merchants endpoint supports autocomplete search (ANA-09)
- merchant-breakdown endpoint provides top-10 data for chart (ANA-07)
- export endpoint provides CSV download functionality (TXN-08)
- bulk-categorize endpoint enables multi-select category update (TXN-12)
- /{id}/category endpoint enables inline re-assign with optional apply_to_merchant (TXN-11)
- apply_user_rules wired into email sync — future transactions will get user-defined categories automatically

## Self-Check: PASSED

- backend/app/models/category_rule.py: FOUND
- backend/app/services/category_rule_service.py: FOUND
- backend/alembic/versions/139c02a97b09_add_category_rules.py: FOUND
- backend/tests/test_category_rules.py: FOUND
- backend/tests/test_transaction_filters.py: FOUND
- Commit 557111a: FOUND
- Commit 7f63d24: FOUND

---
*Phase: 05-data-quality*
*Completed: 2026-04-28*
