---
phase: 03-multi-bank-parsers
plan: 02
subsystem: api
tags: [python, fastapi, email-parsing, hdfc, payment-source, pytest]

# Dependency graph
requires:
  - phase: 03-01
    provides: "payment_source column in Transaction model, Alembic migrations, test infrastructure"

provides:
  - "parse(email: dict) unified parser interface replacing parse(body, subject)"
  - "payment_source populated on all HDFC transactions (UPI: 'HDFC UPI', CC: 'HDFC CC •{last4}')"
  - "HDFC date fallback uses email received_at instead of date.today()"
  - "Sync service separates unmatched (no parser) from parse_failed (parser crashed)"
  - "payment_source stored in Transaction row when creating from email"
  - "API route surfaces unmatched count in sync response"
  - "Frontend displays parse_failed and unmatched separately with distinct labels"

affects: [03-03, icici-parser, sbi-parser, any-new-bank-parser]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parser interface: parse(email: dict) with id/sender/subject/body/received_at keys"
    - "Parser date fallback: received_at.date() if received_at else date.today()"
    - "Sync service: parse_email(email) in try/except; None -> unmatched, exception -> parse_failed"
    - "payment_source format: 'Bank Instrument ••last4' or 'Bank Type' for no-card-number cases"

key-files:
  created: []
  modified:
    - backend/app/parsers/base_parser.py
    - backend/app/parsers/hdfc_parser.py
    - backend/app/parsers/parser_factory.py
    - backend/app/services/email_sync_service.py
    - backend/app/api/routes/gmail.py
    - frontend/src/components/gmail/GmailSync.jsx

key-decisions:
  - "Keep parse_email in email_sync_service import (tests patch it); restructure so None=unmatched, exception=parse_failed"
  - "get_parser also imported to express intent; parse_email delegates to get_parser + parser.parse(email) internally"
  - "payment_source uses right single quote (U+2019) before last4, matching test expectation"

patterns-established:
  - "All new bank parsers must implement parse(self, email: dict) and populate payment_source"
  - "Sync service unmatched vs parse_failed distinction is the canonical counter separation pattern"

requirements-completed: [PARSE-09, INFRA-05]

# Metrics
duration: 15min
completed: 2026-04-05
---

# Phase 03 Plan 02: Parser Interface Refactor + HDFC Fixes Summary

**HDFC parser updated to parse(email: dict) with payment_source and received_at fallback; sync service now tracks unmatched emails separately from parse errors**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-05T08:45:00Z
- **Completed:** 2026-04-05T09:00:53Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Changed `parse()` abstract method signature from `(body, subject)` to `(email: dict)` across base_parser and HDFCParser
- Added `payment_source` population to HDFC UPI ("HDFC UPI") and CC ("HDFC CC •{last4}") transactions
- Fixed HDFC date fallback bug: now uses `email["received_at"].date()` instead of `date.today()`
- Refactored email_sync_service to separate `unmatched` (no parser matched) from `parse_failed` (parser threw exception)
- Stored `payment_source` in Transaction when creating from parsed email
- Updated Gmail API route to surface `unmatched` count and frontend to display it distinctly

## Task Commits

Each task was committed atomically:

1. **Task 1: Update parser interface + HDFC parser fixes** - `a846993` (feat)
2. **Task 2: Sync service counter separation + API route + frontend** - `e3db443` (feat)

**Plan metadata:** (see final docs commit)

## Files Created/Modified
- `backend/app/parsers/base_parser.py` - Changed abstract parse() to accept email: dict
- `backend/app/parsers/hdfc_parser.py` - New parse(email: dict), payment_source, fallback_date
- `backend/app/parsers/parser_factory.py` - parse_email() now accepts email: dict, delegates to get_parser + parser.parse(email)
- `backend/app/services/email_sync_service.py` - Added unmatched counter, payment_source to Transaction, parse_email(email_dict) call
- `backend/app/api/routes/gmail.py` - Added unmatched field to sync response
- `frontend/src/components/gmail/GmailSync.jsx` - Displays parse_failed (amber) and unmatched separately, shows parsed_ok count

## Decisions Made
- Kept `parse_email` imported in sync service (tests patch `app.services.email_sync_service.parse_email`) while also importing `get_parser` to document intent. The restructured logic achieves the counter separation: `None` return = unmatched, exception = parse_failed.
- `payment_source` uses right single quotation mark (U+2019) before last4 digits (e.g., `HDFC CC '6054`) to match test expectations in test_hdfc_parser.py.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tests expect parse_email mock, not get_parser mock**
- **Found during:** Task 2 analysis
- **Issue:** Plan spec said to replace `parse_email` import with `get_parser`, but test_email_sync_service.py patches `app.services.email_sync_service.parse_email`. Removing the import would break both tests.
- **Fix:** Kept both `get_parser` and `parse_email` imported. Restructured logic to call `parse_email(email)` in try/except with `None` return → unmatched, exception → parse_failed. The parser_factory's `parse_email` was already updated to accept email dict (Task 1), so the full chain works.
- **Files modified:** backend/app/services/email_sync_service.py
- **Verification:** Both sync service tests pass: unmatched=1/parse_failed=0 for None return; parse_failed=1/unmatched=0 for exception
- **Committed in:** e3db443 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Required to make tests pass. No scope creep. All acceptance criteria met.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Parser interface is now standardized on `parse(email: dict)` — ICICI and SBI parsers (Plan 03) can use this contract from day one
- Sync service counter separation is complete — frontend and API already surface all 5 fields
- payment_source flows from parser through Transaction to DB — ready for ICICI and SBI parsers to populate

---
*Phase: 03-multi-bank-parsers*
*Completed: 2026-04-05*
