# Phase 3 Context: Multi-Bank Parsers

**Phase:** 3 — Multi-Bank Parsers
**Status:** Ready to plan
**Created:** 2026-04-05

---

## What This Phase Delivers

1. ICICI Bank Credit Card email parser
2. SBI Bank debit email parser (debit transactions only — FD/TDS emails ignored)
3. `payment_source` field added to `ParsedTransaction` and DB schema
4. Alembic initial migration generated; startup switches to `alembic upgrade head`
5. HDFC date fallback fixed: use `email["received_at"]` not `date.today()`
6. Sync summary separates `parse_failed` (parser crashed) from `unmatched` (no parser matched)

---

## Decisions

### ICICI Parser

**Sender:** `credit_cards@icicibank.com`

**Email structure (real sample):**
```
Your ICICI Bank Credit Card XX6005 has been used for a transaction of INR 2,009.98
on Apr 03, 2026 at 04:53:52. Info: RAZ*Urbanaut.
```

**Parsing rules:**
- Trigger: subject/body contains "ICICI Bank Credit Card" and "has been used for a transaction"
- Amount: extracted from `INR <amount>` — strip commas before float conversion
- Date: `Apr 03, 2026` format → `strptime("%b %d, %Y")`
- Card last 4: extracted from `Credit Card XX(\d{4})`
- Merchant: extracted from `Info: (.+?)\.` at end of sentence — keep raw value (e.g. `RAZ*Urbanaut`)
- Payment method: `Credit Card`
- payment_source: `"ICICI CC ••{last4}"` (e.g. `"ICICI CC ••6005"`)
- bank_name: `"ICICI Bank"`

### SBI Parser

**Sender:** `cbsalerts.sbi@alerts.sbi.bank.in`

**Email structure — PARSE these (debit transactions):**
```
Your A/C XXXXX404599 has a debit by NACH of Rs 35,000.00 on 02/04/26. Avl Bal Rs 22,80,612.96.
Your A/C XXXXX404599 has a debit by transfer of Rs 215.00 on 06/03/26. Avl Bal Rs 21,82,299.06.
```

**Email structure — SKIP these (non-spending):**
```
Multi Option Dep (FD) of Rs 75,000.00 created on 05/03/26 ...
TDS of INR 3.00 deducted for interest paid on A/C No ...
```

**Skip rules (check before parsing):**
- Body contains `"Multi Option Dep"` → skip (FD auto-sweep, not a spend)
- Body contains `"TDS of"` → skip (tax deduction, not a spend)

**Parsing rules (for debit transactions):**
- Trigger: body matches `has a debit by`
- Amount: extracted from `Rs ([\d,]+\.?\d*)` — strip commas
- Date: `DD/MM/YY` format → `strptime("%d/%m/%y")`
- Account last 4: extract from `A/C XXXXX(\d{4,})` — take last 4 digits of the account number
- Merchant: `None` (SBI debit alerts do not include merchant name)
- Description: constructed as `"SBI {debit_type} Debit"` where debit_type is from `debit by (\w+)` (e.g. `"NACH"`, `"transfer"`) → e.g. `"SBI NACH Debit"`, `"SBI Transfer Debit"`
- Payment method: `"Net Banking"` (NACH and bank transfers)
- payment_source: `"SBI ••{last4}"` (e.g. `"SBI ••4599"`)
- bank_name: `"SBI"`

### payment_source Field

**Format:** `"Bank Instrument ••last4"` — standardized across all parsers
- HDFC UPI: `"HDFC UPI"` (no card number in UPI alerts)
- HDFC Credit Card: `"HDFC CC ••{last4}"`
- ICICI Credit Card: `"ICICI CC ••{last4}"`
- SBI Account: `"SBI ••{last4}"`
- Manual transactions: `null` (user can fill in later; Phase 5 adds UI for this)

**DB column:** `payment_source VARCHAR nullable` — added via Alembic migration in this phase.

**`ParsedTransaction` dataclass:** add `payment_source: Optional[str] = None` field.

### Alembic Migration Strategy

**Decision:** Full switch — `alembic upgrade head` at startup (not `Base.metadata.create_all()`).

**Steps in this phase:**
1. Initialize Alembic if not already done (`alembic init alembic/` in backend/)
2. Configure `alembic.ini` and `alembic/env.py` to point to SQLAlchemy models
3. Run `alembic revision --autogenerate -m "initial_schema"` to capture existing schema
4. Add `payment_source` column to `Transaction` model
5. Run `alembic revision --autogenerate -m "add_payment_source"` for that column
6. Replace `Base.metadata.create_all(db)` in `app/main.py` with `alembic upgrade head` call
7. Both migrations applied in order on startup

**Note:** Dev machine only; no VPS deployment yet. Migration safety testing is Phase 10.

### HDFC Date Fallback Fix

**Current bug:** `hdfc_parser.py` uses `date.today()` when it can't parse the date from the email body.

**Fix:** Pass `received_at` from the email metadata into `parse()`. Use it as fallback:
```python
transaction_date = parsed_date or email_received_at.date()
```

**Scope:** Only fix HDFC. ICICI and SBI parsers must also use `received_at` as fallback from the start.

**Interface change:** `parse(email: dict) -> Optional[ParsedTransaction]` — `email` dict already contains `received_at` key (confirmed from `gmail_service.py`).

### Sync Summary Separation

**Current bug:** Parse errors and unmatched emails are combined in a single counter.

**Fix:** Sync service returns:
```python
{
  "emails_fetched": int,
  "transactions_added": int,
  "duplicates_skipped": int,
  "parse_failed": int,    # parser matched but threw exception
  "unmatched": int,       # no parser's can_parse() returned True
}
```

**Frontend:** Display all 5 fields in sync result UI (currently only shows `transactions_added`).

---

## Files Impacted

| File | Change |
|------|--------|
| `backend/app/parsers/base_parser.py` | Add `payment_source` field to `ParsedTransaction` |
| `backend/app/parsers/hdfc_parser.py` | Fix date fallback to use `received_at`; populate `payment_source` |
| `backend/app/parsers/icici_parser.py` | **NEW** — ICICI credit card parser |
| `backend/app/parsers/sbi_parser.py` | **NEW** — SBI debit parser |
| `backend/app/parsers/parser_factory.py` | Add ICICI and SBI to `PARSERS` list |
| `backend/app/models.py` | Add `payment_source` column to `Transaction` model |
| `backend/app/services/email_sync_service.py` | Separate parse_failed vs unmatched; pass received_at to parse() |
| `backend/app/main.py` | Replace `create_all()` with `alembic upgrade head` |
| `backend/alembic/` | **NEW** — Alembic directory with initial + payment_source migrations |
| `frontend/src/components/gmail/GmailSync.jsx` | Show parse_failed and unmatched in sync result |

---

## Out of Scope for This Phase

- Axis Bank, IDFC First, Kotak, Flash.co parsers — deferred
- SBI UPI parser — no sample provided; deferred
- ICICI UPI / debit parser — only credit card sample provided; deferred
- payment_source filter UI — Phase 5
- Automated sync — Phase 4

---

## Phase Success Criteria (from ROADMAP)

1. ICICI Bank transaction emails are parsed and stored as transactions ✓ (when criterion met)
2. SBI transaction emails (debit only) are parsed and stored as transactions ✓
3. All parsers populate payment_source ✓
4. Alembic initial migration generated; startup uses `alembic upgrade head` ✓
5. Sync summary correctly separates parse errors from unmatched emails ✓
6. HDFC transactions use email received_at date as fallback (not date.today()) ✓
