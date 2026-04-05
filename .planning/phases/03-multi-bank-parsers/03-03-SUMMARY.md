---
phase: 03-multi-bank-parsers
plan: 03
subsystem: api
tags: [python, fastapi, email-parsing, icici, sbi, pytest]

# Dependency graph
requires:
  - phase: 03-02
    provides: "parse(email: dict) unified parser interface, payment_source on ParsedTransaction, HDFC parser updated"

provides:
  - "ICICIParser: parses credit card alerts from credit_cards@icicibank.com"
  - "SBIParser: parses debit alerts from cbsalerts.sbi@alerts.sbi.bank.in; skips FD and TDS emails"
  - "Both parsers registered in PARSERS list in parser_factory.py"
  - "payment_source populated for ICICI ('ICICI CC \u2019{last4}') and SBI ('SBI \u2019{last4}')"
  - "All three banks (HDFC, ICICI, SBI) discoverable via get_parser()"

affects: [04-auto-sync, 05-analytics, any-new-bank-parser]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ICICI parser: INR amount with commas, 'Apr DD, YYYY' date, 'Info: merchant.' merchant extraction"
    - "SBI parser: Rs amount with commas, DD/MM/YY date, 'debit by TYPE' debit type extraction"
    - "SBI skip pattern: check body for 'Multi Option Dep' and 'TDS of' before parsing"
    - "payment_source format: 'Bank Instrument \u2019last4' (U+2019 right single quotation mark)"
    - "categorize(merchant or '', description) — always pass empty string not None for merchant"

key-files:
  created:
    - backend/app/parsers/icici_parser.py
    - backend/app/parsers/sbi_parser.py
  modified:
    - backend/app/parsers/parser_factory.py

key-decisions:
  - "payment_source uses U+2019 right single quotation mark before last4 (matches test expectation set in 03-02)"
  - "SBI merchant=None and category='Others' — SBI debit alerts don't include merchant name"
  - "SBI can_parse checks body for 'has a debit by' (not sender) since sender domain is reliable but body check is explicit"

patterns-established:
  - "All bank parsers follow: can_parse(sender, subject, body) + parse(email: dict) + payment_source populated"
  - "New parser registration: add import + instantiation to PARSERS list in parser_factory.py"
  - "Skip non-spending emails at top of parse() before any extraction (return None early)"

requirements-completed: [PARSE-03, PARSE-04]

# Metrics
duration: 20min
completed: 2026-04-05
---

# Phase 03 Plan 03: ICICI + SBI Bank Email Parsers Summary

**ICICI credit card parser and SBI debit parser created and registered; all three banks now supported via unified parse(email: dict) interface with payment_source populated**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-05T09:05:00Z
- **Completed:** 2026-04-05T09:25:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created ICICIParser parsing credit card transaction alerts from credit_cards@icicibank.com: extracts INR amount (with commas), date (Apr DD, YYYY format), card last4 from XX prefix, merchant from Info: field
- Created SBIParser parsing debit alerts (NACH + transfer) from cbsalerts.sbi@alerts.sbi.bank.in: extracts Rs amount, DD/MM/YY date, account last4, debit type; skips FD and TDS emails
- Registered both parsers in PARSERS list alongside HDFCParser; removed Phase 3 placeholder comments
- All 25 parser/sync tests pass (8 ICICI, 11 SBI, 4 HDFC, 2 sync service); no ICICI/SBI skips remain

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ICICI credit card parser** - `968551e` (feat)
2. **Task 2: Create SBI parser + register both in factory** - `d219677` (feat)

**Plan metadata:** (see final docs commit)

## Files Created/Modified
- `backend/app/parsers/icici_parser.py` - ICICI Bank Credit Card parser; parses INR amounts, Apr DD YYYY dates, Info: merchant, payment_source "ICICI CC \u2019{last4}"
- `backend/app/parsers/sbi_parser.py` - SBI debit parser; handles NACH/transfer, skips FD/TDS, merchant=None, payment_source "SBI \u2019{last4}"
- `backend/app/parsers/parser_factory.py` - Added ICICIParser and SBIParser imports and instantiations to PARSERS list

## Decisions Made
- Used U+2019 right single quotation mark before last4 in payment_source (matches test expectations established in Plan 03-02 for HDFC CC)
- SBI sets `merchant=None` and `category="Others"` since SBI debit alerts contain no merchant information
- SBI `can_parse()` checks `body.lower()` for "has a debit by" — explicit and covers both NACH and transfer variants
- `categorize(merchant or "", description)` pattern used consistently (prevents TypeError from None concatenation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tests run from main project (worktree missing full app module tree)**
- **Found during:** Task 1 verification
- **Issue:** The git worktree only contains files created in Phase 3 plans. Missing `app/database.py`, `app/config.py`, `app/models/email_metadata.py`, etc. (Phase 1/2 files). Running pytest from the worktree fails with `ModuleNotFoundError: No module named 'app.database'` when loading conftest.py.
- **Fix:** Copied new parser files to the main project (`C:/Users/rahul/projects/expense-tracker/backend/`) and ran tests from there against the full codebase. Worktree commits contain the canonical source of truth.
- **Files modified:** (copies only — main project not tracked in worktree branch)
- **Verification:** 25 tests pass in main project: ICICI (8), SBI (11), HDFC (4), sync service (2)
- **Committed in:** 968551e and d219677 (worktree commits)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking)
**Impact on plan:** Tests verified correct; worktree branch structure is intentional (Phase 3 only tracks Phase 3 files). No scope creep.

## Issues Encountered

**Pre-existing migration test failures (out of scope):** `tests/test_migrations.py` fails with `OperationalError: no such table: transactions` when run against the main project. Root cause: the initial Alembic migration (7a9eaedc9937) is intentionally empty (the live DB already existed when it was generated), so running it on a fresh temp DB skips table creation. The add_payment_source migration then fails because `transactions` table doesn't exist. This is a pre-existing issue documented in 03-01 SUMMARY and unrelated to Plan 03-03 (parsers only). Logged to deferred-items.

## Known Stubs
None — all parsers produce real data from real email bodies. No placeholder values or hardcoded responses.

## User Setup Required
None - no external service configuration required. All changes are parser code and factory registration.

## Next Phase Readiness
- Three banks fully supported: HDFC (UPI + CC), ICICI (CC), SBI (NACH + transfer)
- Phase 3 parser objectives complete: all three bank parsers implemented, payment_source populated, factory updated
- Phase 4 (automated sync) can begin: parser infrastructure is complete and tested
- Deferred: Alembic migration test fix (empty initial_schema issue) should be addressed in Phase 10 (VPS deploy) when proper migration strategy is implemented

---
*Phase: 03-multi-bank-parsers*
*Completed: 2026-04-05*
