---
phase: 03-multi-bank-parsers
plan: 01
subsystem: infra, testing, database
tags: [alembic, sqlite, pytest, migrations, payment_source, fastapi]

# Dependency graph
requires:
  - phase: 02-gmail-hdfc
    provides: HDFCParser, BaseEmailParser, EmailSyncService, Transaction model, Alembic installed but unused

provides:
  - Alembic initial_schema migration capturing all 4 existing tables
  - add_payment_source migration adding nullable VARCHAR(100) column to transactions
  - payment_source field on ParsedTransaction dataclass (Optional[str])
  - payment_source Column on Transaction SQLAlchemy model
  - _run_db_migrations() replacing Base.metadata.create_all() in main.py
  - pytest.ini + conftest.py with 8 email fixtures + in_memory_db fixture
  - Test stubs for HDFC, ICICI, SBI parsers, email sync service, and migrations (27 tests)

affects:
  - 03-02 (HDFC parser update — test_hdfc_parser.py RED tests become GREEN)
  - 03-03 (ICICI/SBI parser creation — test_icici_parser.py and test_sbi_parser.py become GREEN)
  - 10-vps-deploy (Alembic schema management established)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Alembic stamp head to bootstrap migrations on existing DB without recreating tables"
    - "_run_db_migrations() function called at module level in main.py at startup"
    - "Conditional import + skipif pattern for parsers not yet created (ICICI, SBI)"
    - "ParsedTransaction dataclass uses Optional[str] = None default for new fields"

key-files:
  created:
    - backend/pytest.ini
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_hdfc_parser.py
    - backend/tests/test_icici_parser.py
    - backend/tests/test_sbi_parser.py
    - backend/tests/test_email_sync_service.py
    - backend/tests/test_migrations.py
    - backend/alembic/versions/7a9eaedc9937_initial_schema.py
    - backend/alembic/versions/628c6541bc23_add_payment_source.py
  modified:
    - backend/app/models/transaction.py
    - backend/app/main.py
    - backend/app/parsers/base_parser.py

key-decisions:
  - "Empty initial_schema migration is correct: autogenerate found no diff because DB already matched models"
  - "alembic stamp head marks existing DB as at initial migration without running SQL — preserves all data"
  - "payment_source added to both ParsedTransaction dataclass (as Optional with default=None) and Transaction SQLAlchemy model"
  - "Removed engine and Base imports from main.py — only alembic config/command needed at startup"

patterns-established:
  - "Test stubs: conditional import + @pytest.mark.skipif for parsers not yet created"
  - "Fixtures: email dicts with id, sender, subject, body, received_at keys"
  - "Alembic bootstrap: autogenerate initial (empty) → stamp → add column → autogenerate delta → upgrade"

requirements-completed: [INFRA-01, INFRA-02]

# Metrics
duration: 15min
completed: 2026-04-05
---

# Phase 3 Plan 01: Test Infrastructure and Alembic Migration Bootstrap Summary

**Alembic bootstrapped on existing SQLite DB with two migrations (initial_schema + add_payment_source), payment_source column live, and 27 pytest stubs covering all Phase 3 parsers and migration correctness**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-05T08:47:40Z
- **Completed:** 2026-04-05T09:02:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Bootstrapped Alembic on existing 4-table SQLite DB using stamp-then-upgrade sequence — all existing data preserved
- Added `payment_source` VARCHAR(100) nullable column to transactions table via proper migration (not create_all)
- Replaced `Base.metadata.create_all(bind=engine)` with `_run_db_migrations()` calling `alembic upgrade head` in main.py
- Created full pytest infrastructure: 27 tests across 5 modules; HDFC/sync tests are RED, ICICI/SBI are SKIP, migration tests are GREEN
- Added `payment_source: Optional[str] = None` to `ParsedTransaction` dataclass for all future parsers

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test infrastructure (Wave 0)** - `e0f107d` (feat)
2. **Task 2: Alembic initial migration + payment_source + startup switch** - `38dc97a` (feat)

**Plan metadata:** _(committed with docs commit below)_

## Files Created/Modified

- `backend/pytest.ini` — pytest config with testpaths=tests, asyncio_mode=auto
- `backend/tests/__init__.py` — empty package marker
- `backend/tests/conftest.py` — 8 sample email dict fixtures + in_memory_db fixture
- `backend/tests/test_hdfc_parser.py` — 4 RED tests (payment_source UPI/CC, dict signature, date fallback)
- `backend/tests/test_icici_parser.py` — 8 SKIP tests (ICICIParser not yet created)
- `backend/tests/test_sbi_parser.py` — 11 SKIP tests (SBIParser not yet created)
- `backend/tests/test_email_sync_service.py` — 2 RED tests (unmatched/parse_failed counter split)
- `backend/tests/test_migrations.py` — 2 GREEN tests (upgrade head, nullable payment_source)
- `backend/alembic/versions/7a9eaedc9937_initial_schema.py` — initial migration (empty upgrade, DB already existed)
- `backend/alembic/versions/628c6541bc23_add_payment_source.py` — adds payment_source column
- `backend/app/models/transaction.py` — added payment_source = Column(String(100), nullable=True)
- `backend/app/main.py` — replaced create_all with _run_db_migrations() via alembic command.upgrade
- `backend/app/parsers/base_parser.py` — added payment_source: Optional[str] = None to ParsedTransaction

## Decisions Made

- **Empty initial_schema migration is correct:** autogenerate ran against the live DB and found zero differences (DB already matched all SQLAlchemy models). The empty `upgrade()` is intentional — it represents "DB is at this baseline."
- **stamp before upgrade:** Without `alembic stamp head` after generating initial migration, running `upgrade head` would attempt to execute the initial migration (which is empty, but would create the `alembic_version` row correctly). The stamp was safe and explicit.
- **payment_source on ParsedTransaction:** Added as `Optional[str] = None` default so all existing `ParsedTransaction(...)` call sites in HDFCParser don't break — they simply get `payment_source=None` until Plan 02 updates them.
- **Removed engine/Base from main.py imports:** The `_run_db_migrations()` function uses alembic's own engine creation via `alembic.ini`, so the SQLAlchemy engine import in main.py was no longer needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added payment_source to ParsedTransaction dataclass**
- **Found during:** Task 2 (adding payment_source column to Transaction model)
- **Issue:** The critical_context specified adding `payment_source: Optional[str] = None` to `ParsedTransaction` in `base_parser.py`, but the plan's task description only mentioned the SQLAlchemy model column
- **Fix:** Added `payment_source: Optional[str] = None` as a default-valued field to the `ParsedTransaction` dataclass
- **Files modified:** `backend/app/parsers/base_parser.py`
- **Verification:** Existing HDFCParser instantiations remain valid (default=None); test_hdfc_parser.py tests reference this field
- **Committed in:** `38dc97a` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for test_hdfc_parser.py and future parser tests to reference `parsed.payment_source`. No scope creep.

## Issues Encountered

None — the Alembic bootstrap sequence (autogenerate → stamp → add column → autogenerate → upgrade) worked cleanly as documented in critical_context.

## Known Stubs

None — all test stub files contain real assertion logic. The ICICI/SBI tests are marked SKIP (not stub), and will become GREEN when parsers are created in Plan 03.

## User Setup Required

None — no external service configuration required. All changes are local DB schema and test infrastructure.

## Next Phase Readiness

- Plan 03-02 can begin immediately: test_hdfc_parser.py has 4 RED tests waiting for HDFC parser dict-signature refactor and payment_source population
- Plan 03-03 can begin after 03-02: test_icici_parser.py (8 tests) and test_sbi_parser.py (11 tests) will become GREEN when parsers are created
- Migration tests (test_migrations.py) are already GREEN — they run alembic upgrade on a fresh temp DB and verify payment_source column exists
- `alembic current` returns `628c6541bc23 (head)` — DB fully migrated

---
*Phase: 03-multi-bank-parsers*
*Completed: 2026-04-05*
