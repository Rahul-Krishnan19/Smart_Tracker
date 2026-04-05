---
phase: 03-multi-bank-parsers
verified: 2026-04-05T12:00:00Z
status: human_needed
score: 6/6 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "Alembic initial migration captures existing 4-table schema (INFRA-01/INFRA-02) — upgrade() now contains full CREATE TABLE DDL for all 4 tables; alembic upgrade head succeeds on a fresh DB; both migration tests pass"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Connect a real Gmail account and trigger a sync that includes at least one ICICI credit card email and one SBI debit email"
    expected: "Both emails are parsed and appear as transactions with correct payment_source values (e.g. 'ICICI CC \u20196005', 'SBI \u20194599')"
    why_human: "Requires live Gmail OAuth token and real bank email bodies in the inbox; cannot be simulated by unit tests"
  - test: "Restart the backend server on the development machine and observe startup logs"
    expected: "Alembic logs show 'Running upgrade ... -> head' (not a crash); server starts cleanly"
    why_human: "Requires live server start; dev DB already has the schema so alembic upgrade head is a no-op — only observable by watching startup output"
---

# Phase 3: Multi-Bank Parsers Verification Report

**Phase Goal:** Support ICICI and SBI bank emails in the parser framework, fix known data bugs, and establish Alembic as the migration tool
**Verified:** 2026-04-05
**Status:** human_needed — all automated checks pass; 2 items require human testing
**Re-verification:** Yes — after gap closure (plan 03-04 fixed empty initial migration)

---

## Re-Verification Summary

Previous status: `gaps_found` (5/6 truths verified)
Current status: `human_needed` (6/6 truths verified)

**Gap closed:** The initial Alembic migration `7a9eaedc9937_initial_schema.py` was populated with `op.create_table()` DDL for all 4 tables (users, sessions, transactions, emails) in dependency order, and a corresponding `downgrade()` with reverse-order `op.drop_table()` calls. The test INSERT in `test_payment_source_column_nullable` was corrected to use actual schema column names (`username`, `password_hash`, `totp_enrolled` instead of the wrong names from a different schema).

**Regression check:** All 27 tests pass (0 failed), including the 25 tests that passed in the initial verification.

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ICICI Bank transaction emails are parsed and stored as transactions | VERIFIED | `icici_parser.py` exists (86 lines), all 8 ICICI tests pass including amount, date, merchant, payment_source, payment_method, bank_name |
| 2 | SBI transaction emails are parsed and stored as transactions | VERIFIED | `sbi_parser.py` exists (89 lines), all 11 SBI tests pass including NACH/transfer parsing and FD/TDS skip logic |
| 3 | All parsers populate payment_source (card/account identifier) | VERIFIED | `ParsedTransaction.payment_source` field present in base_parser.py; HDFC sets "HDFC UPI" / "HDFC CC '{last4}", ICICI sets "ICICI CC '{last4}", SBI sets "SBI '{last4}"; payment_source stored to DB via email_sync_service.py line 99 |
| 4 | Alembic initial migration generated; startup uses alembic upgrade head | VERIFIED | `7a9eaedc9937_initial_schema.py` now contains full CREATE TABLE DDL for all 4 tables; `main.py` calls `command.upgrade(alembic_cfg, "head")` at startup; both migration tests pass on fresh DB |
| 5 | Sync summary correctly separates parse errors from unmatched emails | VERIFIED | email_sync_service.py maintains separate `unmatched` and `parse_failed` counters; both surfaced in API response; both displayed in frontend with distinct labels; both tested |
| 6 | HDFC transactions use email received_at date as fallback (not date.today()) | VERIFIED | hdfc_parser.py: `fallback_date = received_at.date() if received_at else date.today()`; no remaining `date.today()` calls in parse paths; `test_date_fallback_uses_received_at` passes |

**Score:** 6/6 truths verified

---

## Required Artifacts

### Plan 03-01 Artifacts (INFRA-01, INFRA-02)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/pytest.ini` | VERIFIED | Contains `testpaths = tests`; asyncio_mode = auto |
| `backend/tests/conftest.py` | VERIFIED | 132 lines; contains `sample_icici_cc_email`, `sample_sbi_nach_email`, `in_memory_db`, all fixtures |
| `backend/tests/test_hdfc_parser.py` | VERIFIED | Contains `test_payment_source_upi`, `test_date_fallback_uses_received_at`; all 4 tests pass |
| `backend/tests/test_icici_parser.py` | VERIFIED | Contains `test_can_parse_icici`, `test_payment_source`, `test_parse_amount`; all 8 tests pass |
| `backend/tests/test_sbi_parser.py` | VERIFIED | Contains `test_fd_email_skipped`, `test_tds_email_skipped`, `test_payment_source`; all 11 tests pass |
| `backend/tests/test_email_sync_service.py` | VERIFIED | Contains `test_unmatched_counter`, `test_parse_failed_counter`; both pass |
| `backend/tests/test_migrations.py` | VERIFIED | Contains `test_alembic_upgrade_head` and `test_payment_source_column_nullable`; both pass (fixed by plan 03-04) |
| `backend/alembic/versions/7a9eaedc9937_initial_schema.py` | VERIFIED | 4 `op.create_table()` calls (users, sessions, transactions, emails); 4 `op.drop_table()` calls in downgrade; no `payment_source` column in DDL (comment only); complete migration chain |
| `backend/alembic/versions/628c6541bc23_add_payment_source.py` | VERIFIED | Adds `payment_source` column via `op.add_column`; `down_revision = '7a9eaedc9937'` chains correctly |
| `backend/app/models/transaction.py` | VERIFIED | Line 26: `payment_source = Column(String(100), nullable=True)` |
| `backend/app/main.py` | VERIFIED | Contains `from alembic.config import Config`, `from alembic import command`, `command.upgrade(alembic_cfg, "head")`; `Base.metadata.create_all` is gone |

### Plan 03-02 Artifacts (PARSE-09, INFRA-05)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/parsers/base_parser.py` | VERIFIED | Line 23: `payment_source: Optional[str] = None`; line 48: `def parse(self, email: dict)` |
| `backend/app/parsers/hdfc_parser.py` | VERIFIED | Uses `parse(self, email: dict)` signature; `payment_source="HDFC UPI"` in UPI path; `payment_source=f"HDFC CC '{account_last4}"` in CC path; no `date.today()` calls in parse paths |
| `backend/app/services/email_sync_service.py` | VERIFIED | Contains `"unmatched": 0` in summary dict; `summary["unmatched"] += 1`; `payment_source=parsed.payment_source` in Transaction creation |
| `backend/app/api/routes/gmail.py` | VERIFIED | `"unmatched": summary["unmatched"]` in sync response |
| `frontend/src/components/gmail/GmailSync.jsx` | VERIFIED | Displays `parse_failed` (amber, "parse errors") and `unmatched` ("unrecognised emails") separately; `parsed_ok` also displayed |

### Plan 03-03 Artifacts (PARSE-03, PARSE-04)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/parsers/icici_parser.py` | VERIFIED | 86 lines; `class ICICIParser(BaseEmailParser)`; correct regex for amount (INR), date (Apr DD, YYYY), merchant (Info: field), card last4; `payment_source=f"ICICI CC '{last4}"` |
| `backend/app/parsers/sbi_parser.py` | VERIFIED | 89 lines; `class SBIParser(BaseEmailParser)`; FD/TDS skip logic; NACH/transfer debit_type extraction; `payment_source=f"SBI '{last4}"`; `merchant=None`; `payment_method="Net Banking"` |
| `backend/app/parsers/parser_factory.py` | VERIFIED | Imports `ICICIParser`, `SBIParser`; PARSERS list contains `HDFCParser()`, `ICICIParser()`, `SBIParser()`; no commented-out placeholders |

### Plan 03-04 Artifacts (INFRA-01, INFRA-02 — gap closure)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/alembic/versions/7a9eaedc9937_initial_schema.py` | VERIFIED | `op.create_table` count: 4; `op.drop_table` count: 4; `payment_source` not in DDL (comment only); tables in correct dependency order |
| `backend/tests/test_migrations.py` | VERIFIED | Uses correct column names (`username`, `password_hash`, `totp_enrolled`); both tests pass |

---

## Key Link Verification

### Plan 03-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/main.py` | `backend/alembic.ini` | `alembic.config.Config + command.upgrade` | VERIFIED | `command.upgrade(alembic_cfg, "head")` present; `ini_path` constructed relative to `__file__` |
| `backend/alembic/versions/7a9eaedc9937_initial_schema.py` | `backend/alembic/versions/628c6541bc23_add_payment_source.py` | `down_revision = '7a9eaedc9937'` | VERIFIED | Chain confirmed; upgrade head creates all 4 tables then adds payment_source column; both migration tests pass on fresh DB |

### Plan 03-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/parsers/hdfc_parser.py` | `backend/app/parsers/base_parser.py` | `parse(self, email: dict)` signature | VERIFIED | hdfc_parser.py: `def parse(self, email: dict)` |
| `backend/app/services/email_sync_service.py` | `backend/app/parsers/parser_factory.py` | `get_parser()` + `parser.parse(email)` | VERIFIED | Service calls `parse_email(email)` wrapper; unmatched/parse_failed separation confirmed by tests |
| `backend/app/services/email_sync_service.py` | `backend/app/models/transaction.py` | `payment_source` stored in Transaction | VERIFIED | `payment_source=parsed.payment_source` in Transaction creation |
| `backend/app/api/routes/gmail.py` | `backend/app/services/email_sync_service.py` | `unmatched` key surfaced | VERIFIED | `"unmatched": summary["unmatched"]` in sync response |

### Plan 03-03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/parsers/icici_parser.py` | `backend/app/parsers/base_parser.py` | `class ICICIParser(BaseEmailParser)` | VERIFIED | Line 18: `class ICICIParser(BaseEmailParser)` |
| `backend/app/parsers/sbi_parser.py` | `backend/app/parsers/base_parser.py` | `class SBIParser(BaseEmailParser)` | VERIFIED | Line 19: `class SBIParser(BaseEmailParser)` |
| `backend/app/parsers/parser_factory.py` | `backend/app/parsers/icici_parser.py` | `ICICIParser()` in PARSERS list | VERIFIED | Line 12: `ICICIParser()` in PARSERS |
| `backend/app/parsers/parser_factory.py` | `backend/app/parsers/sbi_parser.py` | `SBIParser()` in PARSERS list | VERIFIED | Line 14: `SBIParser()` in PARSERS |
| `backend/app/parsers/sbi_parser.py` | `backend/app/parsers/categorizer.py` | `categorize("", description)` | VERIFIED | Line 83: `category=categorize("", description)` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `email_sync_service.py` | `payment_source` | `parsed.payment_source` from parser | Yes — parsers set from regex extraction | FLOWING |
| `gmail.py` sync endpoint | `unmatched`, `parse_failed` | `summary` dict from EmailSyncService | Yes — counters incremented in sync loop | FLOWING |
| `GmailSync.jsx` | `result.unmatched`, `result.parse_failed` | API response from `/api/gmail/sync` | Yes — API returns live summary dict | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| ICICI parser returns correct ParsedTransaction | `python -m pytest tests/test_icici_parser.py -v` | 8 passed | PASS |
| SBI parser returns correct ParsedTransaction and skips FD/TDS | `python -m pytest tests/test_sbi_parser.py -v` | 11 passed | PASS |
| HDFC parser has payment_source and received_at fallback | `python -m pytest tests/test_hdfc_parser.py -v` | 4 passed | PASS |
| Sync service separates unmatched from parse_failed | `python -m pytest tests/test_email_sync_service.py -v` | 2 passed | PASS |
| Alembic upgrade head works on fresh DB | `python -m pytest tests/test_migrations.py -v` | 2 passed | PASS (was FAIL) |
| ICICI + SBI in parser_factory | `grep -n "ICICIParser\|SBIParser" backend/app/parsers/parser_factory.py` | Both present | PASS |
| Full test suite | `python -m pytest tests/ -v --tb=short` | **27 passed, 0 failed** | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PARSE-03 | 03-03-PLAN.md | ICICI Bank alerts parsed | SATISFIED | `icici_parser.py` exists; 8 tests pass; registered in factory |
| PARSE-04 | 03-03-PLAN.md | SBI alerts parsed | SATISFIED | `sbi_parser.py` exists; 11 tests pass; registered in factory |
| PARSE-09 | 03-02-PLAN.md | All parsers extract payment_source | SATISFIED | `ParsedTransaction.payment_source` field; HDFC/ICICI/SBI all set it; stored to DB |
| INFRA-01 | 03-01-PLAN.md | Alembic initial migration generated; startup uses alembic upgrade head | SATISFIED | Initial migration now has CREATE TABLE DDL for all 4 tables; both migration tests pass on fresh DB; `main.py` uses `command.upgrade(alembic_cfg, "head")` |
| INFRA-02 | 03-01-PLAN.md | All new schema changes via Alembic migration files | SATISFIED | `add_payment_source` migration correctly chains after `initial_schema`; complete fresh-DB deployment works end-to-end via `alembic upgrade head` |
| INFRA-05 | 03-02-PLAN.md | parse_failed / unmatched counters separated in sync summary | SATISFIED | Both counters in summary dict; both surfaced in API response; both displayed in frontend with distinct labels; both tested |

**Orphaned requirements check:** All six requirements claimed by plans are satisfied. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/alembic/versions/7a9eaedc9937_initial_schema.py` | 60 | `# WITHOUT payment_source` — comment only, not a code issue | INFO | Comment clarifying why payment_source is absent from initial migration; correct and intentional |
| `backend/app/parsers/icici_parser.py` | 72 | `payment_source = f"ICICI CC \u2019{last4}"` — uses RIGHT SINGLE QUOTATION MARK (`\u2019`) | WARNING | Deviates from original plan spec but is consistent across all three parsers; test fixtures match implementation; no functional impact |
| `backend/app/parsers/sbi_parser.py` | 75 | Same `\u2019` character for `SBI \u2019{last4}` | WARNING | Consistent with ICICI — all parsers use the same character; tests pass |
| `backend/app/parsers/hdfc_parser.py` | 219 | Same `\u2019` character | WARNING | All three parsers consistent; test fixtures match |

No blockers remain.

---

## Human Verification Required

### 1. Live Gmail sync with ICICI and SBI emails

**Test:** Connect a real Gmail account that has received ICICI credit card transaction emails and SBI debit alerts. Trigger the "Sync Emails" button from the frontend.
**Expected:** New transactions appear in the transaction list with correct amounts, dates, merchant names, and payment_source values. The sync result banner shows `transactions_created` count, and any unrecognized emails appear in the "unrecognised emails" count.
**Why human:** Requires a live Gmail OAuth token and real bank email bodies in the inbox; cannot be simulated by unit tests.

### 2. Server startup behavior

**Test:** Restart the FastAPI backend (`uvicorn app.main:app --reload --port 8000`) and observe the startup output.
**Expected:** Alembic prints migration context logs showing the current revision; server starts without error. No `Base.metadata.create_all` behavior should occur.
**Why human:** The dev database already has all tables so `alembic upgrade head` is a no-op and no error will appear. Only observable by watching startup logs.

---

## Gaps Summary

No gaps remain. All 6 success criteria are verified. Phase goal is achieved:

- ICICI and SBI parsers are implemented, tested, and registered in the factory (PARSE-03, PARSE-04).
- All three parsers extract payment_source from email content (PARSE-09).
- Alembic migration chain is complete and functional on fresh databases (INFRA-01, INFRA-02).
- Sync summary separates parse errors from unmatched emails with distinct counters (INFRA-05).
- HDFC date fallback uses email received_at, not date.today() (INFRA-05/PARSE-09 related fix).

The only remaining items are live integration tests requiring a real Gmail account, which cannot be automated.

---

_Verified: 2026-04-05 (re-verification after plan 03-04 gap closure)_
_Verifier: Claude (gsd-verifier)_
