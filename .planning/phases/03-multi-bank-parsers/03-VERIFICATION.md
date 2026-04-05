---
phase: 03-multi-bank-parsers
verified: 2026-04-05T00:00:00Z
status: gaps_found
score: 5/6 must-haves verified
gaps:
  - truth: "Alembic initial migration captures existing 4-table schema (INFRA-01/INFRA-02)"
    status: failed
    reason: "Initial migration (7a9eaedc9937_initial_schema.py) has an empty upgrade() body — it only runs 'pass'. On a fresh database, alembic upgrade head fails with 'no such table: transactions' when the add_payment_source migration tries to ALTER a table that was never created. Two migration tests confirm this: test_alembic_upgrade_head and test_payment_source_column_nullable both fail."
    artifacts:
      - path: "backend/alembic/versions/7a9eaedc9937_initial_schema.py"
        issue: "upgrade() contains only 'pass' — no CREATE TABLE statements for users, sessions, transactions, or email_metadata tables. Was generated against an existing DB (stamped, not run), so autogenerate produced no-op."
    missing:
      - "Add CREATE TABLE statements for all 4 tables (users, sessions, transactions, email_metadata) to the initial_schema migration upgrade() function, so a fresh DB deployment works end-to-end via alembic upgrade head alone."
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
**Status:** gaps_found — 1 gap blocking INFRA-01/INFRA-02 goal achievement
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ICICI Bank transaction emails are parsed and stored as transactions | VERIFIED | `icici_parser.py` exists (86 lines), all 8 ICICI tests pass including amount, date, merchant, payment_source, payment_method, bank_name |
| 2 | SBI transaction emails are parsed and stored as transactions | VERIFIED | `sbi_parser.py` exists (89 lines), all 11 SBI tests pass including NACH/transfer parsing and FD/TDS skip logic |
| 3 | All parsers populate payment_source (card/account identifier) | VERIFIED | `ParsedTransaction.payment_source` field present in base_parser.py; HDFC sets "HDFC UPI" / "HDFC CC \u2019{last4}", ICICI sets "ICICI CC \u2019{last4}", SBI sets "SBI \u2019{last4}"; payment_source stored to DB via email_sync_service.py line 99 |
| 4 | Alembic initial migration generated; startup uses alembic upgrade head | FAILED | Two migration files exist and main.py calls `command.upgrade(alembic_cfg, "head")` at startup (VERIFIED). BUT the initial_schema migration has an empty `upgrade()` — tests `test_alembic_upgrade_head` and `test_payment_source_column_nullable` both FAIL with `sqlite3.OperationalError: no such table: transactions`. Fresh DB deployment is broken. |
| 5 | Sync summary correctly separates parse errors from unmatched emails | VERIFIED | email_sync_service.py maintains separate `unmatched` and `parse_failed` counters; try/except around `parse_email()` catches parser exceptions into `parse_failed`; `None` return from `parse_email` (no parser matched) goes to `unmatched`; gmail.py route exposes both; GmailSync.jsx displays both with distinct labels |
| 6 | HDFC transactions use email received_at date as fallback (not date.today()) | VERIFIED | hdfc_parser.py line 87: `fallback_date = received_at.date() if received_at else date.today()`; no remaining `date.today()` calls in parse paths; `test_date_fallback_uses_received_at` passes |

**Score:** 5/6 truths verified

---

## Required Artifacts

### Plan 03-01 Artifacts (INFRA-01, INFRA-02)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/pytest.ini` | VERIFIED | Contains `testpaths = tests`; asyncio_mode = auto |
| `backend/tests/conftest.py` | VERIFIED | 132 lines; contains `sample_icici_cc_email`, `sample_sbi_nach_email`, `in_memory_db`, all 7 fixtures |
| `backend/tests/test_hdfc_parser.py` | VERIFIED | Contains `test_payment_source_upi`, `test_date_fallback_uses_received_at`; all 4 tests pass |
| `backend/tests/test_icici_parser.py` | VERIFIED | Contains `test_can_parse_icici`, `test_payment_source`, `test_parse_amount`; all 8 tests pass |
| `backend/tests/test_sbi_parser.py` | VERIFIED | Contains `test_fd_email_skipped`, `test_tds_email_skipped`, `test_payment_source`; all 11 tests pass |
| `backend/tests/test_email_sync_service.py` | VERIFIED | Contains `test_unmatched_counter`, `test_parse_failed_counter`; both pass |
| `backend/tests/test_migrations.py` | VERIFIED (exists, substantive) / ORPHANED (tests fail) | Contains `test_alembic_upgrade_head`; tests exist and are wired, but FAIL due to empty initial_schema migration |
| `backend/alembic/versions/` | STUB (initial) | Two .py files exist: `7a9eaedc9937_initial_schema.py` (empty upgrade) and `628c6541bc23_add_payment_source.py` (correct); initial migration is a no-op |
| `backend/app/models/transaction.py` | VERIFIED | Line 26: `payment_source = Column(String(100), nullable=True)` |
| `backend/app/main.py` | VERIFIED | Contains `from alembic.config import Config`, `from alembic import command`, `command.upgrade(alembic_cfg, "head")`; `Base.metadata.create_all` is gone |

### Plan 03-02 Artifacts (PARSE-09, INFRA-05)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/parsers/base_parser.py` | VERIFIED | Line 23: `payment_source: Optional[str] = None`; line 48: `def parse(self, email: dict)` |
| `backend/app/parsers/hdfc_parser.py` | VERIFIED | Uses `parse(self, email: dict)` signature; `payment_source="HDFC UPI"` in UPI path; `payment_source=f"HDFC CC \u2019{account_last4}"` in CC path; no `date.today()` calls in parse paths |
| `backend/app/services/email_sync_service.py` | VERIFIED | Contains `"unmatched": 0` in summary dict; `summary["unmatched"] += 1`; `payment_source=parsed.payment_source` in Transaction creation |
| `backend/app/api/routes/gmail.py` | VERIFIED | Line 117: `"unmatched": summary["unmatched"]` in sync response |
| `frontend/src/components/gmail/GmailSync.jsx` | VERIFIED | Lines 115-118 display `parse_failed` (amber, "parse errors") and `unmatched` ("unrecognised emails") separately; `parsed_ok` also displayed |

### Plan 03-03 Artifacts (PARSE-03, PARSE-04)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/parsers/icici_parser.py` | VERIFIED | 86 lines; `class ICICIParser(BaseEmailParser)`; correct regex for amount (INR), date (Apr DD, YYYY), merchant (Info: field), card last4; `payment_source=f"ICICI CC \u2019{last4}"` |
| `backend/app/parsers/sbi_parser.py` | VERIFIED | 89 lines; `class SBIParser(BaseEmailParser)`; FD/TDS skip logic; NACH/transfer debit_type extraction; `payment_source=f"SBI \u2019{last4}"`; `merchant=None`; `payment_method="Net Banking"` |
| `backend/app/parsers/parser_factory.py` | VERIFIED | Imports `ICICIParser`, `SBIParser`; PARSERS list contains `HDFCParser()`, `ICICIParser()`, `SBIParser()`; no commented-out placeholders |

---

## Key Link Verification

### Plan 03-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/main.py` | `backend/alembic.ini` | `alembic.config.Config + command.upgrade` | VERIFIED | `command.upgrade(alembic_cfg, "head")` present; `ini_path` constructed relative to `__file__` |
| `backend/app/models/transaction.py` | `backend/alembic/versions/` | autogenerate detects payment_source | PARTIAL | `payment_source` column in model; `add_payment_source` migration correctly alters it; BUT initial_schema is empty so fresh-DB chain is broken |

### Plan 03-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/parsers/hdfc_parser.py` | `backend/app/parsers/base_parser.py` | `parse(self, email: dict)` signature | VERIFIED | hdfc_parser.py line 84: `def parse(self, email: dict)` |
| `backend/app/services/email_sync_service.py` | `backend/app/parsers/parser_factory.py` | `get_parser()` + `parser.parse(email)` | VERIFIED (behavior) / PARTIAL (implementation) | Service imports both `get_parser` and `parse_email`; the sync loop calls `parse_email(email)` (wrapper), not the two-step directly. Behavior is correct — unmatched/parse_failed separation works. Tests confirm. |
| `backend/app/services/email_sync_service.py` | `backend/app/models/transaction.py` | `payment_source` stored in Transaction | VERIFIED | Line 99: `payment_source=parsed.payment_source` |
| `backend/app/api/routes/gmail.py` | `backend/app/services/email_sync_service.py` | `unmatched` key surfaced | VERIFIED | Line 117: `"unmatched": summary["unmatched"]` |

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
| Alembic upgrade head works on fresh DB | `python -m pytest tests/test_migrations.py -v` | 2 FAILED | FAIL |
| ICICI + SBI in parser_factory | `grep -n "ICICIParser\|SBIParser" backend/app/parsers/parser_factory.py` | Both present | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PARSE-03 | 03-03-PLAN.md | ICICI Bank alerts parsed | SATISFIED | `icici_parser.py` exists; 8 tests pass; registered in factory |
| PARSE-04 | 03-03-PLAN.md | SBI alerts parsed | SATISFIED | `sbi_parser.py` exists; 11 tests pass; registered in factory |
| PARSE-09 | 03-02-PLAN.md | All parsers extract payment_source | SATISFIED | `ParsedTransaction.payment_source` field; HDFC/ICICI/SBI all set it; stored to DB |
| INFRA-01 | 03-01-PLAN.md | Alembic initial migration generated; startup uses alembic upgrade head | BLOCKED | Initial migration file exists but has empty `upgrade()`. Fresh-DB deployment fails. Startup replacement works on existing DB only. |
| INFRA-02 | 03-01-PLAN.md | All new schema changes via Alembic migration files | BLOCKED | `add_payment_source` migration is correct, but it is unreachable on a fresh DB because the initial_schema migration creates no tables. The migration chain is functionally broken for new deployments. |
| INFRA-05 | 03-02-PLAN.md | parse_failed / unmatched counters separated in sync summary | SATISFIED | Both counters in summary dict; both surfaced in API response; both displayed in frontend with distinct labels; both tested |

**Orphaned requirements check:** REQUIREMENTS.md maps `PARSE-03, PARSE-04, PARSE-09, INFRA-01, INFRA-02, INFRA-05` to Phase 3. All six are claimed by the plans. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/alembic/versions/7a9eaedc9937_initial_schema.py` | 22-23 | `def upgrade() -> None: pass` | BLOCKER | Prevents `alembic upgrade head` from working on a fresh database; migration tests fail |
| `backend/app/parsers/icici_parser.py` | 72 | `payment_source = f"ICICI CC \u2019{last4}"` — uses RIGHT SINGLE QUOTATION MARK (`'`) not bullet characters (`••`) | WARNING | Deviates from plan spec which said `••`, but tests match implementation (`\u2019`), so this is a consistent design choice, not a bug. No functional impact. |
| `backend/app/parsers/sbi_parser.py` | 75 | Same `\u2019` character for `SBI \u2019{last4}` | WARNING | Same as above — consistent with ICICI |
| `backend/app/parsers/hdfc_parser.py` | 219 | `f"HDFC CC \u2019{account_last4}"` | WARNING | Same `\u2019` character — all three parsers use it consistently; test fixtures match |
| `backend/app/services/email_sync_service.py` | 14 | Imports `parse_email` (still present) but sync logic also calls `parse_email()` directly | INFO | `parse_email` import is used (line 71), so it is not dead code. The plan spec described a two-step pattern but the wrapper approach is functionally equivalent and tests pass. |

---

## Human Verification Required

### 1. Live Gmail sync with ICICI and SBI emails

**Test:** Connect a real Gmail account that has received ICICI credit card transaction emails and SBI debit alerts. Trigger the "Sync Emails" button from the frontend.
**Expected:** New transactions appear in the transaction list with correct amounts, dates, merchant names, and payment_source values. The sync result banner shows `transactions_created` count, and any unrecognized emails appear in the "unrecognised emails" count.
**Why human:** Requires a live Gmail OAuth token and real bank email bodies in the inbox.

### 2. Server startup behavior

**Test:** Restart the FastAPI backend (`uvicorn app.main:app --reload --port 8000`) and observe the startup output.
**Expected:** Alembic prints migration context logs showing the current revision; server starts without error. No `Base.metadata.create_all` behavior should occur.
**Why human:** The dev database already has all tables so `alembic upgrade head` is a no-op and no error will appear. Only observable by watching startup logs.

---

## Gaps Summary

**1 gap blocking full goal achievement:**

**INFRA-01 / INFRA-02 — Initial migration is empty (fresh DB deployment broken)**

The initial Alembic migration (`7a9eaedc9937_initial_schema.py`) was generated by running `alembic revision --autogenerate` against an existing database that already had all tables, then immediately stamping the DB at that revision without running the migration. As a result, autogenerate saw no schema diff and wrote `pass` in `upgrade()`.

On a fresh database, `alembic upgrade head` first runs this empty migration (creates no tables), then tries to run `add_payment_source` which calls `ALTER TABLE transactions ADD COLUMN payment_source` — but `transactions` does not exist. This raises `sqlite3.OperationalError: no such table: transactions`.

The two migration tests (`test_alembic_upgrade_head`, `test_payment_source_column_nullable`) both fail for this reason.

**Impact on goal:** INFRA-01 states "startup uses `alembic upgrade head`" — this IS implemented in main.py and works on the existing dev database (which already has all tables). However, INFRA-02 states "all new schema changes delivered via Alembic migration files" and INFRA-01 implies a complete migration chain. On a fresh database (Phase 10 VPS deployment), the current migration chain would fail.

**Fix required:** Add `CREATE TABLE` DDL for all 4 tables (users, sessions, transactions, email_metadata) to the `upgrade()` function of `7a9eaedc9937_initial_schema.py`.

---

_Verified: 2026-04-05_
_Verifier: Claude (gsd-verifier)_
