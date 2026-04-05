# Phase 3: Multi-Bank Parsers - Research

**Researched:** 2026-04-05
**Domain:** Python regex email parsing, Alembic schema migrations, FastAPI service refactoring
**Confidence:** HIGH

---

## Summary

Phase 3 is a well-scoped extension of the existing parser framework established in Phase 2. All decisions are fully locked in CONTEXT.md — exact regex patterns, field names, skip logic, and DB column definitions are specified. The research task is to verify the existing codebase state, confirm the Alembic setup, and identify gotchas before planning begins.

The codebase is in a clean state: Alembic is initialized (`alembic/env.py` exists and correctly imports all models), but zero migration files exist in `alembic/versions/`. The `alembic_version` table does not exist in the SQLite DB, and current revision is `None`. This means the first migration must create the full schema from scratch (autogenerate will produce a complete `CREATE TABLE` migration). Autogenerate was verified to detect zero drift between the current DB and models — the DB matches the models exactly, so the initial migration will be a clean snapshot.

The sync service already separates parse errors from unmatched emails at the code level (`parse_failed` counter handles both), but the API route response and frontend only expose a combined count. The frontend `GmailSync.jsx` already references `result.parse_failed` in one place but treats it as "unrecognised emails" — a display string fix, not a data-model change. The main work is adding an `unmatched` key and separating the counter logic in `email_sync_service.py`.

**Primary recommendation:** Implement tasks in this order: (1) Alembic initial migration, (2) add `payment_source` to model + migration, (3) update `ParsedTransaction` dataclass, (4) fix HDFC parser, (5) add ICICI parser, (6) add SBI parser, (7) register parsers in factory, (8) fix sync service counters, (9) replace `create_all` in main.py, (10) update frontend display. This ordering avoids running the server with a schema mismatch.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ICICI Parser**
- Sender: `credit_cards@icicibank.com`
- Trigger: subject/body contains "ICICI Bank Credit Card" and "has been used for a transaction"
- Amount: from `INR <amount>` — strip commas before float conversion
- Date: `Apr 03, 2026` format → `strptime("%b %d, %Y")`
- Card last 4: from `Credit Card XX(\d{4})`
- Merchant: from `Info: (.+?)\.` at end of sentence — keep raw value
- Payment method: `Credit Card`
- payment_source: `"ICICI CC ••{last4}"`
- bank_name: `"ICICI Bank"`

**SBI Parser**
- Sender: `cbsalerts.sbi@alerts.sbi.bank.in`
- Trigger: body matches `has a debit by`
- Skip if body contains `"Multi Option Dep"` or `"TDS of"`
- Amount: from `Rs ([\d,]+\.?\d*)` — strip commas
- Date: `DD/MM/YY` → `strptime("%d/%m/%y")`
- Account last 4: from `A/C XXXXX(\d{4,})` — take last 4 digits
- Merchant: `None`
- Description: `"SBI {debit_type} Debit"` where debit_type from `debit by (\w+)`
- Payment method: `"Net Banking"`
- payment_source: `"SBI ••{last4}"`
- bank_name: `"SBI"`

**payment_source Field**
- HDFC UPI: `"HDFC UPI"` (no card number in UPI alerts)
- HDFC Credit Card: `"HDFC CC ••{last4}"`
- ICICI Credit Card: `"ICICI CC ••{last4}"`
- SBI Account: `"SBI ••{last4}"`
- Manual transactions: `null`
- DB column: `payment_source VARCHAR nullable`

**Alembic Migration Strategy**
- Full switch: `alembic upgrade head` at startup (not `Base.metadata.create_all()`)
- Initialize Alembic (already done — `alembic/env.py` exists)
- Run `alembic revision --autogenerate -m "initial_schema"` to capture existing schema
- Add `payment_source` column to `Transaction` model
- Run `alembic revision --autogenerate -m "add_payment_source"` for that column
- Replace `Base.metadata.create_all(db)` in `app/main.py` with `alembic upgrade head` call
- Both migrations applied in order on startup

**HDFC Date Fallback Fix**
- Current bug: uses `date.today()` when date can't be parsed from body
- Fix: pass `received_at` from email dict into `parse()`; use `email_received_at.date()` as fallback
- Interface change: `parse(email: dict) -> Optional[ParsedTransaction]`
- `email` dict already contains `received_at` key (confirmed from gmail_service.py)

**Sync Summary Separation**
- Return dict must include: `emails_fetched`, `transactions_added`, `duplicates_skipped`, `parse_failed`, `unmatched`
- `parse_failed`: parser matched but threw exception
- `unmatched`: no parser's `can_parse()` returned True
- Frontend: display all 5 fields in sync result UI

### Claude's Discretion

None explicitly stated. All decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Axis Bank, IDFC First, Kotak, Flash.co parsers
- SBI UPI parser (no sample provided)
- ICICI UPI / debit parser (only credit card sample provided)
- payment_source filter UI — Phase 5
- Automated sync — Phase 4
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PARSE-03 | ICICI Bank alerts parsed | ICICIParser class following BaseEmailParser pattern; regex patterns fully specified in CONTEXT.md |
| PARSE-04 | SBI alerts parsed | SBIParser class with skip logic for FD/TDS emails; regex patterns fully specified in CONTEXT.md |
| PARSE-09 | All parsers extract payment_source | Add `payment_source: Optional[str] = None` to ParsedTransaction dataclass; populate in all 3 parsers; store in Transaction DB column |
| INFRA-01 | Alembic initial migration generated; startup uses `alembic upgrade head` | Alembic 1.14.0 installed, env.py configured, versions/ empty, DB has no alembic_version table — clean state for initial autogenerate |
| INFRA-02 | All new schema changes delivered via Alembic migration files | Established by INFRA-01; payment_source column is the first Alembic-managed change |
| INFRA-05 | parse_failed / unmatched counters separated in sync summary | email_sync_service.py already has both code paths; needs counter split + new `unmatched` key; API route and frontend need corresponding updates |
</phase_requirements>

---

## Standard Stack

### Core (all already installed in venv)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| alembic | 1.14.0 | Schema migration management | Already in requirements.txt and installed |
| sqlalchemy | 2.0.36 | ORM + DB abstraction | Already in use throughout codebase |
| Python re | stdlib | Regex parsing of email bodies | Already used in hdfc_parser.py |
| Python dataclasses | stdlib | ParsedTransaction data container | Already used in base_parser.py |

### No New Dependencies Required
All functionality for Phase 3 uses libraries already installed. No `pip install` step is needed.

---

## Architecture Patterns

### Existing Parser Pattern (follow exactly)
```
backend/app/parsers/
├── base_parser.py       # BaseEmailParser ABC + ParsedTransaction dataclass
├── categorizer.py       # categorize(merchant, description) → str
├── hdfc_parser.py       # HDFCParser(BaseEmailParser) — reference implementation
├── parser_factory.py    # PARSERS list + get_parser() + parse_email()
├── icici_parser.py      # NEW — same pattern as hdfc_parser.py
└── sbi_parser.py        # NEW — same pattern as hdfc_parser.py
```

### Pattern 1: BaseEmailParser Subclass
**What:** Every parser subclasses `BaseEmailParser` from `app.parsers.base_parser`.
**When to use:** Always — for all new bank parsers.

Current `parse()` signature (to be changed in this phase):
```python
def parse(self, body: str, subject: str = "") -> Optional[ParsedTransaction]:
```

New signature after interface change (CONTEXT.md decision):
```python
def parse(self, email: dict) -> Optional[ParsedTransaction]:
    # email["body"], email["subject"], email["received_at"] all available
    received_at = email.get("received_at")
    email_date = received_at.date() if received_at else date.today()
```

**All three parsers** (HDFC, ICICI, SBI) must use this new signature.

**CRITICAL:** `parser_factory.py`'s `parse_email()` function currently calls `parser.parse(body, subject)`. It must be updated to pass the full email dict: `parser.parse(email)`.

**ALSO CRITICAL:** `email_sync_service.py` calls `parse_email(sender, subject, body)` — this call site must also pass the full email dict.

### Pattern 2: can_parse() Guard
**What:** `can_parse(sender, subject, body)` returns True/False before `parse()` is called. The factory calls this first; only calls `parse()` if `can_parse()` returns True.
**When to use:** All parsers implement this.

SBI skip logic belongs inside `parse()`, NOT `can_parse()`. Reason: `can_parse()` matches on "has a debit by" — FD and TDS emails don't contain that phrase anyway. The skip guards (`"Multi Option Dep"`, `"TDS of"`) are a belt-and-suspenders safety check inside `parse()`.

### Pattern 3: Alembic Programmatic Startup Call
**What:** Replace `Base.metadata.create_all(bind=engine)` in `main.py` with a programmatic Alembic call.

Verified API (Alembic 1.14.0):
```python
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

# In main.py startup, replace create_all with:
run_migrations()
```

**Pitfall:** The `alembic.ini` path is relative to the working directory. When running `uvicorn app.main:app` from `backend/`, the path `"alembic.ini"` resolves correctly. Use `os.path.join(os.path.dirname(__file__), "..", "alembic.ini")` if needed for robustness.

### Pattern 4: Alembic Initial Migration Sequence
The DB currently has no `alembic_version` table and no migration files. The correct sequence:

**Step 1 — Generate initial migration (captures existing schema):**
```bash
cd backend/
source venv/Scripts/activate
alembic revision --autogenerate -m "initial_schema"
```
This will create a migration with full CREATE TABLE statements for all 4 tables (users, sessions, transactions, emails). Verified: autogenerate detects zero drift (DB matches models exactly), so the initial migration will be a clean snapshot.

**Step 2 — Add payment_source to Transaction model:**
Edit `app/models/transaction.py` to add:
```python
payment_source = Column(String(100), nullable=True)
```

**Step 3 — Generate payment_source migration:**
```bash
alembic revision --autogenerate -m "add_payment_source"
```
This will produce an `ALTER TABLE transactions ADD COLUMN payment_source VARCHAR(100)`.

**Step 4 — Verify migration chain:**
```bash
alembic upgrade head
alembic current  # should show head revision
```

### Pattern 5: Sync Summary Counter Separation
Current `email_sync_service.py` increments `parse_failed` for BOTH exceptions AND unmatched emails:

```python
# Current (WRONG — combines both):
if parsed is None:
    summary["parse_failed"] += 1  # actually "unmatched"
```

Fixed structure:
```python
summary = {
    "fetched": 0,
    "skipped_duplicate": 0,
    "parsed_ok": 0,
    "parse_failed": 0,    # parser matched + can_parse() True, but parse() threw exception
    "unmatched": 0,       # no parser's can_parse() returned True
    "transactions_created": 0,
}
```

The current service calls `parse_email(sender, subject, body)` which returns `None` for both failure cases. To distinguish them, the service must call `get_parser()` first, then call `parser.parse()` directly:

```python
parser = get_parser(sender=email["sender"], subject=email["subject"], body=email["body"])
if parser is None:
    summary["unmatched"] += 1
    # ...
else:
    try:
        parsed = parser.parse(email)  # full email dict
    except Exception as e:
        summary["parse_failed"] += 1
        # ...
```

### Anti-Patterns to Avoid
- **Calling `date.today()` as fallback:** All parsers must use `email["received_at"].date()` as fallback, not `date.today()`. This is a known bug in the existing HDFC parser that must be fixed.
- **Using `parse_email()` convenience function in the sync service:** After the refactor, the sync service must call `get_parser()` + `parser.parse(email)` directly to separate the two failure modes.
- **Leaving `Base.metadata.create_all()` in main.py after Alembic is running:** These two must not coexist or they create a split-brain schema management scenario.
- **SBI: categorizing with merchant=None:** `categorize(None, description)` will fail on string concatenation. Pass `merchant or ""` to `categorize()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migration | Custom SQL ALTER scripts | Alembic autogenerate | Already installed; handles SQLite ADD COLUMN correctly |
| Startup migration check | Custom version table | `alembic upgrade head` | Alembic's alembic_version table is the standard |
| Date parsing multi-format | Custom parser | `datetime.strptime` with format list | HDFC already uses this pattern; reuse `_parse_date()` |

---

## Common Pitfalls

### Pitfall 1: Alembic + SQLite ADD COLUMN Constraint
**What goes wrong:** SQLite does not support `ALTER TABLE ... ADD COLUMN` with constraints (e.g., NOT NULL without default, UNIQUE). Alembic autogenerate for SQLite emits `ADD COLUMN` for nullable columns — this works fine for `payment_source VARCHAR nullable`.
**Why it happens:** SQLite's limited ALTER TABLE support.
**How to avoid:** `payment_source` is `nullable=True` with no default constraint — autogenerate will emit a safe `ADD COLUMN`. No issue here.
**Warning signs:** Migration fails with "Cannot add a NOT NULL column with default value NULL".

### Pitfall 2: Alembic Initial Migration on Existing DB
**What goes wrong:** Running `alembic upgrade head` on an existing DB that has tables but no `alembic_version` table. Alembic will try to execute the initial migration's `CREATE TABLE` statements, which fail because the tables already exist.
**Why it happens:** Alembic doesn't check if tables exist before running CREATE TABLE — it just executes the SQL.
**How to avoid:** Use `alembic stamp head` to mark the existing DB as already at the initial migration state, OR use `IF NOT EXISTS` in the migration. The recommended approach for this project is:
  1. Generate initial migration
  2. Run `alembic stamp head` (marks DB as current without running SQL)
  3. Then run `alembic upgrade head` for subsequent migrations (payment_source)
  This is the correct workflow when the DB already exists and matches the models.
**Warning signs:** `OperationalError: table "users" already exists`.

### Pitfall 3: Parser Interface Change Breaks Factory
**What goes wrong:** Changing `parse(body, subject)` to `parse(email: dict)` in all parsers but forgetting to update `parser_factory.py`'s `parse_email()` function, which calls `parser.parse(body, subject)`.
**Why it happens:** Two call sites must be updated together.
**How to avoid:** Update `base_parser.py` abstract method signature first, then fix all implementing classes (HDFCParser, ICICIParser, SBIParser), then fix `parser_factory.py`, then fix `email_sync_service.py`.
**Warning signs:** `TypeError: parse() takes 2 positional arguments but 3 were given`.

### Pitfall 4: SBI `received_at` as `datetime` vs `date`
**What goes wrong:** `email["received_at"]` is a `datetime` object (from `EmailMetadata.received_at` which is `Column(DateTime)`). Calling `.date()` on it returns a `date` object — correct. But if `received_at` is `None` (email dict may have None for very old emails), `.date()` raises `AttributeError`.
**How to avoid:** Always guard: `email_date = received_at.date() if received_at else date.today()`. CONTEXT.md already specifies this pattern.

### Pitfall 5: ICICI Amount Regex — Commas in Indian Number Format
**What goes wrong:** `INR 2,009.98` — naive float conversion of `"2,009.98"` raises `ValueError`.
**Why it happens:** Indian number format uses commas as thousands separators.
**How to avoid:** Strip commas before conversion: `Decimal(raw.replace(',', ''))`. The existing `_parse_amount()` helper in `hdfc_parser.py` already does this — reuse the same pattern in `icici_parser.py`.

### Pitfall 6: Frontend `result.unmatched` Is a New Key
**What goes wrong:** After the sync service adds `unmatched` to the summary dict, the API route must also pass it through, and the frontend must reference `result.unmatched` (not `result.parse_failed` for unmatched emails).
**Why it happens:** The API route in `gmail.py` currently only surfaces 5 keys from the summary dict.
**Warning signs:** Frontend shows `undefined` for unmatched count.

---

## Code Examples

### ICICI Parser Structure
```python
# Based on: CONTEXT.md locked decisions + base_parser.py pattern
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from app.parsers.base_parser import BaseEmailParser, ParsedTransaction
from app.parsers.categorizer import categorize

class ICICIParser(BaseEmailParser):

    @property
    def bank_name(self) -> str:
        return "ICICI Bank"

    @property
    def sender_patterns(self) -> list[str]:
        return ["credit_cards@icicibank.com"]

    @property
    def subject_patterns(self) -> list[str]:
        return ["icici bank credit card", "has been used for a transaction"]

    def can_parse(self, sender: str, subject: str, body: str) -> bool:
        text = body.lower()
        return (
            "icici bank credit card" in text
            and "has been used for a transaction" in text
        )

    def parse(self, email: dict) -> Optional[ParsedTransaction]:
        body = ' '.join(email["body"].split())
        received_at = email.get("received_at")
        fallback_date = received_at.date() if received_at else date.today()
        # ... regex extraction ...
```

### SBI Skip Logic Pattern
```python
def can_parse(self, sender: str, subject: str, body: str) -> bool:
    return "has a debit by" in body.lower()

def parse(self, email: dict) -> Optional[ParsedTransaction]:
    body = ' '.join(email["body"].split())
    # Skip non-spending emails
    if "Multi Option Dep" in body or "TDS of" in body:
        return None
    # ... parse debit transaction ...
```

### Alembic Programmatic Startup (main.py)
```python
import os
from alembic.config import Config
from alembic import command

def run_db_migrations():
    """Run Alembic migrations on startup instead of create_all."""
    ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    alembic_cfg = Config(os.path.normpath(ini_path))
    command.upgrade(alembic_cfg, "head")

# Replace: Base.metadata.create_all(bind=engine)
# With:
run_db_migrations()
```

### Sync Service Counter Split
```python
from app.parsers.parser_factory import get_parser  # not parse_email

parser = get_parser(
    sender=email["sender"],
    subject=email["subject"],
    body=email["body"],
)
if parser is None:
    meta.parse_status = "unmatched"
    meta.parse_error = "No parser matched"
    summary["unmatched"] += 1
    db.commit()
    continue

try:
    parsed = parser.parse(email)  # full dict
except Exception as e:
    meta.parse_status = "failed"
    meta.parse_error = str(e)[:500]
    summary["parse_failed"] += 1
    db.commit()
    continue
```

---

## Runtime State Inventory

> This phase adds a DB column — a schema migration, not a rename/refactor.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | SQLite DB at `data/database/expense_tracker.db` — 4 tables, no alembic_version table, no payment_source column in transactions | Alembic stamp + migrate |
| Live service config | None — no external service config stores schema state | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no env vars reference column names | None |
| Build artifacts | `backend/venv/` — no compiled artifacts reference schema | None |

**Critical pre-condition:** The DB exists and has data. Must use `alembic stamp head` (after generating initial migration) before running `alembic upgrade head` — otherwise initial migration's CREATE TABLE statements will fail on existing tables.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv) | All backend changes | Yes | 3.14 (venv) | — |
| alembic | INFRA-01, INFRA-02 | Yes | 1.14.0 | — |
| sqlalchemy | All DB changes | Yes | 2.0.36 | — |
| pytest | Test suite | Yes | 8.3.4 | — |
| SQLite DB | Alembic stamp/migrate | Yes | Exists at data/database/expense_tracker.db | — |
| Node.js / npm | Frontend GmailSync.jsx update | Yes (frontend runs) | — | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | None — no pytest.ini or pyproject.toml found |
| Quick run command | `cd backend && source venv/Scripts/activate && pytest tests/ -x -q` |
| Full suite command | `cd backend && source venv/Scripts/activate && pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PARSE-03 | ICICI email parsed to correct transaction fields | unit | `pytest tests/test_icici_parser.py -x` | No — Wave 0 |
| PARSE-03 | ICICI skip: non-ICICI email returns None from can_parse | unit | `pytest tests/test_icici_parser.py::test_can_parse_rejects_other -x` | No — Wave 0 |
| PARSE-04 | SBI debit email parsed to correct transaction fields | unit | `pytest tests/test_sbi_parser.py -x` | No — Wave 0 |
| PARSE-04 | SBI skip: FD email returns None from parse() | unit | `pytest tests/test_sbi_parser.py::test_fd_email_skipped -x` | No — Wave 0 |
| PARSE-04 | SBI skip: TDS email returns None from parse() | unit | `pytest tests/test_sbi_parser.py::test_tds_email_skipped -x` | No — Wave 0 |
| PARSE-09 | payment_source populated on HDFC UPI transaction | unit | `pytest tests/test_hdfc_parser.py::test_payment_source_upi -x` | No — Wave 0 |
| PARSE-09 | payment_source populated on HDFC CC transaction | unit | `pytest tests/test_hdfc_parser.py::test_payment_source_cc -x` | No — Wave 0 |
| PARSE-09 | payment_source populated on ICICI CC transaction | unit | `pytest tests/test_icici_parser.py::test_payment_source -x` | No — Wave 0 |
| PARSE-09 | payment_source populated on SBI transaction | unit | `pytest tests/test_sbi_parser.py::test_payment_source -x` | No — Wave 0 |
| INFRA-01 | alembic upgrade head runs without error on fresh DB | integration | `pytest tests/test_migrations.py -x` | No — Wave 0 |
| INFRA-05 | unmatched email increments unmatched counter, not parse_failed | unit | `pytest tests/test_email_sync_service.py::test_unmatched_counter -x` | No — Wave 0 |
| INFRA-05 | parser exception increments parse_failed counter | unit | `pytest tests/test_email_sync_service.py::test_parse_failed_counter -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/Scripts/activate && pytest tests/ -x -q`
- **Per wave merge:** `cd backend && source venv/Scripts/activate && pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_icici_parser.py` — covers PARSE-03, PARSE-09 (ICICI)
- [ ] `backend/tests/test_sbi_parser.py` — covers PARSE-04, PARSE-09 (SBI)
- [ ] `backend/tests/test_hdfc_parser.py` — covers PARSE-09 (HDFC payment_source) + date fallback fix
- [ ] `backend/tests/test_email_sync_service.py` — covers INFRA-05
- [ ] `backend/tests/test_migrations.py` — covers INFRA-01
- [ ] `backend/tests/conftest.py` — shared fixtures (in-memory SQLite DB, sample email dicts)
- [ ] Framework install: already installed (pytest 8.3.4 in venv)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Base.metadata.create_all()` | `alembic upgrade head` | This phase | Enables tracked, reproducible schema evolution |
| Combined parse_failed counter | Separate `parse_failed` + `unmatched` | This phase | Operators can distinguish bugs from missing parsers |
| `parse(body, subject)` signature | `parse(email: dict)` | This phase | Allows access to `received_at` for date fallback |

**Deprecated after this phase:**
- `Base.metadata.create_all(bind=engine)` in `main.py`: replaced by `command.upgrade(alembic_cfg, "head")`
- `parse_email(sender, subject, body)` in sync service: replaced by `get_parser()` + `parser.parse(email)`

---

## Open Questions

1. **Alembic `alembic.ini` path from uvicorn working directory**
   - What we know: `alembic.ini` uses relative path `script_location = alembic`; uvicorn is run from `backend/`
   - What's unclear: If uvicorn is ever run from a different directory, the relative path breaks
   - Recommendation: Use `os.path` to construct absolute path from `__file__` in `main.py`'s migration call

2. **Frontend `result.unmatched` vs existing `result.parse_failed` display**
   - What we know: `GmailSync.jsx` already shows `result.parse_failed` labeled as "unrecognised emails"
   - What's unclear: After split, should the UI show both counters or combine them for the user?
   - Recommendation: CONTEXT.md says "Display all 5 fields" — show both separately with clear labels ("X parse errors, Y unrecognised")

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `backend/app/parsers/base_parser.py`, `hdfc_parser.py`, `parser_factory.py`
- Direct code inspection: `backend/app/services/email_sync_service.py`
- Direct code inspection: `backend/app/main.py`, `backend/app/models/transaction.py`
- Direct code inspection: `backend/alembic/env.py`, `backend/alembic.ini`
- Direct DB inspection: Verified schema via `sqlalchemy.inspect`, current Alembic revision = None
- Alembic 1.14.0 API verified: `alembic.command.upgrade(config, "head")`
- Autogenerate drift check: confirmed zero drift (DB matches models)

### Secondary (MEDIUM confidence)
- Alembic docs pattern for programmatic usage: standard `Config + command.upgrade` pattern
- SQLite ALTER TABLE limitations: well-documented, verified `nullable=True` column is safe

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in use; versions verified from venv
- Architecture: HIGH — patterns directly observed in existing codebase; no inference needed
- Pitfalls: HIGH — Alembic stamp/existing-DB issue directly verified by inspecting DB state; other pitfalls from direct code reading
- Test gaps: HIGH — `tests/` directory has only an empty `fixtures/` subdirectory; no .py test files exist

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack, no fast-moving dependencies)
