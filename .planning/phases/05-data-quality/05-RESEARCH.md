# Phase 5: Data Quality - Research

**Researched:** 2026-04-06
**Domain:** FastAPI filter extension, SQLAlchemy GROUP BY aggregates, Alembic migrations, React form state, CSV export via StreamingResponse
**Confidence:** HIGH (all findings verified against live codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** No full regex rules engine or Settings rules editor. Inline re-assignment on a transaction row with "Apply to all future transactions from this merchant" checkbox.
- **D-02:** "Apply to future" = (a) create contains-rule in DB AND (b) retroactively update all existing transactions with the same merchant to the new category. Both happen together.
- **D-03:** `CategoryRule` DB table: `(id, user_id, keyword, match_type='contains', category, created_at)`. Only `contains` match type.
- **D-04:** Auto-categorizer at import time checks DB rules first (user rules take precedence over hardcoded keywords), then falls back to hardcoded `CATEGORY_RULES` in `categorizer.py`.
- **D-05:** Add `Subscriptions`, `Utilities`, `Travel` to `CATEGORIES` constant (Transaction model) and frontend FilterPanel.
- **D-06:** No changes to "Others" category. CAT-06 deferred.
- **D-07:** TXN-13 (CSV file upload) is explicitly OUT OF SCOPE for Phase 5.
- **D-08:** `GET /api/payment-sources` returns distinct payment_source values for the current user (non-null only). Frontend populates a dropdown.
- **D-09:** Add `min_amount` and `max_amount` query params to transactions list endpoint.
- **D-10:** Quick date preset buttons (Today/This Week/This Month/Last Month/Last 3 Months/This Year) — frontend-only, set date_from/date_to in filter form. No backend changes.
- **D-11:** Filtered view shows total count and sum in the table header from the existing `/api/transactions/summary` endpoint extended to respect all active filters.
- **D-12:** `GET /api/transactions/export` — same filter params as list endpoint, returns CSV file.
- **D-13:** CSV columns: Date, Amount, Description, Merchant, Category, Payment Method, Payment Source, Notes.
- **D-14:** Merchant breakdown goes on Analytics page, below existing charts.
- **D-15:** Top 10 merchants by total spend for the selected date range.
- **D-16:** ANA-08 (top merchants on dashboard) goes on Analytics page — same section.
- **D-17:** Merchant autocomplete: debounced search input → `GET /api/merchants?q=<query>` → top 10 matching merchant names.
- **D-18:** Analytics charts respond to payment_source filter — add `payment_source` as optional filter param to `GET /api/transactions/summary`.
- **D-19:** Payment source filter is single-select dropdown (not multi-select).
- **D-20:** Bulk re-assignment: select multiple rows with checkboxes, apply category to all selected at once. No "apply to future" in bulk mode.

### Claude's Discretion

- None recorded in CONTEXT.md. All key decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- TXN-13: CSV file upload
- CAT-06: Unclassified separate from Others
- CAT-05: Match types beyond `contains` (regex, exact, starts_with)
- CAT-07: Settings rules editor (dedicated page)
- PARSE-05 through PARSE-08: Additional bank parsers (Axis, IDFC, Kotak, Flash.co)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TXN-05 | Transaction table supports multi-select filters: category, payment source, merchant, amount range | FilterPanel uses react-hook-form; extend with 3 new fields; backend extends TransactionFilters schema |
| TXN-06 | Quick date presets: Today / This Week / This Month / Last Month / Last 3M / This Year | Frontend-only; `date-fns` already installed (used in TransactionList.jsx); set `date_from`/`date_to` via setValue |
| TXN-07 | Filtered view shows total count and sum in table header | TransactionsPage already calls `fetchSummary(appliedFilters)` — extend summary endpoint to accept all filter params |
| TXN-08 | Filtered view exportable to CSV | New `GET /api/transactions/export` endpoint using Python `csv` + `io.StringIO` + `StreamingResponse` |
| TXN-10 | Cash transactions supported (payment_method=Cash, payment_source=null) | `payment_source` column already nullable; Cash already in PAYMENT_METHODS; no schema change needed |
| TXN-11 | Category re-assignable inline; option to apply to all future transactions from same merchant | PUT /api/transactions/{id} body needs `apply_to_merchant: bool` field; backend creates CategoryRule + bulk updates |
| TXN-12 | Bulk category re-assignment (multi-select rows) | TransactionList needs checkbox state + bulk action bar; new `POST /api/transactions/bulk-categorize` endpoint |
| CAT-03 | Extended taxonomy: Subscriptions, Utilities, Travel | Add to `CATEGORIES` list in `transaction.py`, update validator in `schemas/transaction.py`, update `FilterPanel.jsx` |
| CAT-04 | DB-backed category rules (keyword → category, user-editable) | New `CategoryRule` SQLAlchemy model + Alembic migration; service reads rules at import and re-categorize time |
| CAT-05 | Match types: contains only (others deferred) | `match_type` column with default `'contains'`; only contains logic implemented |
| PAY-02 | payment_source column added (nullable for Cash) | Column already exists in DB (migration 628c6541bc23); `TransactionOut` schema needs `payment_source` field added |
| PAY-03 | Multi-select filter by payment source | Single-select per D-19; dropdown populated from GET /api/payment-sources |
| PAY-04 | Analytics charts respond to payment source filter | Add `payment_source` param to `GET /api/transactions/summary`; AnalyticsPage passes it through |
| PAY-05 | GET /api/payment-sources returns distinct sources for current user | `SELECT DISTINCT payment_source FROM transactions WHERE user_id=? AND payment_source IS NOT NULL` |
| ANA-07 | Merchant breakdown table (total, count, avg, % of total) | New `GET /api/transactions/merchant-breakdown` endpoint; GROUP BY merchant query |
| ANA-08 | Top 10 merchants by spend on Analytics page | Same endpoint as ANA-07; component on AnalyticsPage below existing charts |
| ANA-09 | Merchant autocomplete for transaction filter | `GET /api/merchants?q=<query>` with debounced input in FilterPanel; simple datalist or custom dropdown |
</phase_requirements>

---

## Summary

Phase 5 extends an existing, well-structured FastAPI + React codebase. All backend changes are additive: new query parameters on existing endpoints, two new GET endpoints (`/api/payment-sources`, `/api/merchants`), one new export endpoint, one new aggregate endpoint, a new DB table (`category_rules`), and a modified `PUT /api/transactions/{id}`. No existing endpoint signatures break.

The `payment_source` column already exists in the DB (migration `628c6541bc23`) and in the `Transaction` SQLAlchemy model. The gap is that `TransactionOut` schema does not yet expose it, and the filter/summary endpoints don't yet accept it as a parameter.

The categorizer change is the highest-risk item. The recommended approach (from CONTEXT.md) is to keep `categorize()` stateless and add a separate `apply_user_rules(db, user_id, transactions)` step — this avoids changing the call signature in all four parser files (hdfc x2, icici, sbi). User rules are only applied at import time (post-parse step in `email_sync_service.py`) and on manual re-categorize (the `PUT /api/transactions/{id}` handler).

The frontend changes are concentrated in three files: `FilterPanel.jsx` (add payment source dropdown, amount range, date preset buttons, merchant autocomplete), `TransactionList.jsx` (add checkbox column, inline category edit UI, bulk action bar), and `AnalyticsPage.jsx` (add payment_source filter dropdown, merchant breakdown table). `TransactionsPage.jsx` needs small wiring updates to pass new filter keys to `fetchSummary()`.

**Primary recommendation:** Plan in 3 waves: (1) DB migration + backend API extensions, (2) TransactionList/FilterPanel frontend, (3) Analytics page + merchant breakdown.

---

## Standard Stack

### Core (already installed — verified via pip show)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36 | ORM query building | Already used throughout |
| FastAPI | 0.115.0 | Route handlers, Query params, StreamingResponse | Already used throughout |
| Alembic | 1.14.0 | DB schema migrations | Established in Phase 3 |
| Pydantic | 2.12.5 | Schema validation (TransactionFilters extension) | Already used throughout |
| Python stdlib `csv` + `io.StringIO` | 3.14 stdlib | CSV export — no extra install | Sufficient for export; no pandas needed |

### Frontend (already installed)

| Library | Version | Purpose |
|---------|---------|---------|
| react-hook-form | already in use (FilterPanel.jsx) | Form state for new filter fields |
| date-fns | already imported (TransactionList.jsx, AnalyticsPage.jsx) | Date preset calculations |
| axios | already in use (api.js) | API calls including CSV export via `responseType: 'blob'` |
| Recharts | already in use (AnalyticsPage.jsx) | Charts (no new charts needed in Phase 5) |

### No New Installs Required

Everything Phase 5 needs is already installed. No `pip install` or `npm install` steps.

---

## Architecture Patterns

### Pattern 1: Extending TransactionFilters (Pydantic + FastAPI Query params)

The current pattern in `transactions.py` route explicitly maps each Query param to a `TransactionFilters` constructor. New params follow the identical pattern.

**What to add to `TransactionFilters` in `schemas/transaction.py`:**
```python
payment_source: Optional[str] = None
min_amount: Optional[Decimal] = None
max_amount: Optional[Decimal] = None
```

**What to add to the route in `routes/transactions.py`:**
```python
payment_source: Optional[str] = Query(None),
min_amount: Optional[Decimal] = Query(None, ge=0),
max_amount: Optional[Decimal] = Query(None, ge=0),
```

**What to add to `transaction_service.list()` in `transaction_service.py`:**
```python
if filters.payment_source:
    query = query.filter(Transaction.payment_source == filters.payment_source)
if filters.min_amount is not None:
    query = query.filter(Transaction.amount >= filters.min_amount)
if filters.max_amount is not None:
    query = query.filter(Transaction.amount <= filters.max_amount)
```

### Pattern 2: Extending get_summary() for payment_source + all filter params

The current `get_summary()` only accepts `date_from`, `date_to`. It needs to accept all TransactionFilters params (for TXN-07 and PAY-04). The cleanest approach: change the signature to accept a `TransactionFilters` object instead of individual date params. The route handler for `GET /api/transactions/summary` would be updated identically to the list endpoint.

**Caution:** `TransactionsPage.jsx` calls `fetchSummary(appliedFilters)` but currently only passes `date_from`/`date_to` to the API. The `fetchSummary` function must be updated to pass ALL active filters (including `payment_source`, `min_amount`, `max_amount`) so TXN-07 shows the correct filtered count/sum.

### Pattern 3: New GET endpoints (payment-sources, merchants, merchant-breakdown)

Follow the existing pattern in `routes/transactions.py`:
```python
@router.get("/payment-sources")
def list_payment_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Transaction.payment_source).filter(
        Transaction.user_id == current_user.id,
        Transaction.payment_source.isnot(None),
    ).distinct().all()
    return {"payment_sources": [r[0] for r in rows]}
```

**Route ordering is critical in FastAPI:** `/payment-sources`, `/export`, and `/merchant-breakdown` MUST be registered BEFORE `/{tx_id}` in the router. Currently `/{tx_id}` is at line 66 of `routes/transactions.py`. New static-path routes must appear before it.

### Pattern 4: CSV Export via StreamingResponse

```python
import csv
import io
from fastapi.responses import StreamingResponse

@router.get("/export")
def export_transactions(
    # same filter params as list endpoint...
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Re-use transaction_service.list() with page_size=10000 (no pagination for export)
    # OR: build the query directly in the route
    rows = transaction_service.export(db, current_user.id, filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Amount", "Description", "Merchant",
                     "Category", "Payment Method", "Payment Source", "Notes"])
    for tx in rows:
        writer.writerow([
            tx.transaction_date, float(tx.amount), tx.description,
            tx.merchant or "", tx.category, tx.payment_method,
            tx.payment_source or "", tx.notes or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )
```

**Frontend trigger:** `window.location.href` won't work (auth header not sent). Must use:
```javascript
export const transactionsApi = {
  // ...existing
  export: (params) => api.get('/transactions/export', {
    params,
    responseType: 'blob',
  }),
}
```
Then in component:
```javascript
const res = await transactionsApi.export(activeFilters)
const url = URL.createObjectURL(new Blob([res.data]))
const a = document.createElement('a')
a.href = url
a.download = 'transactions.csv'
a.click()
URL.revokeObjectURL(url)
```

### Pattern 5: CategoryRule Model + Alembic Migration

**New SQLAlchemy model** (new file `backend/app/models/category_rule.py`):
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class CategoryRule(Base):
    __tablename__ = "category_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(200), nullable=False)
    match_type = Column(String(20), nullable=False, default="contains")
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
```

**Alembic migration command:**
```bash
cd backend && source venv/Scripts/activate
alembic revision --autogenerate -m "add_category_rules"
```
Expected: generates a migration that adds `category_rules` table.
Last migration is `628c6541bc23` (add_payment_source). New migration `down_revision` must point to `628c6541bc23`.

**Import model before autogenerate:** `env.py` must import `CategoryRule` so Alembic sees it. Check `backend/alembic/env.py` — it imports `Base` from `app.database`. Either import `CategoryRule` model in `app/models/__init__.py` or add an explicit import in `env.py`.

### Pattern 6: apply_user_rules() — stateless categorize() stays unchanged

Per D-04, keep `categorize()` stateless. Add a new function in `categorizer.py` or in a new `category_rule_service.py`:

```python
def apply_user_rules(db: Session, user_id: int, merchant: str, description: str) -> Optional[str]:
    """Check DB rules first; return category if match found, else None."""
    from app.models.category_rule import CategoryRule
    text = (merchant + " " + description).lower()
    rules = db.query(CategoryRule).filter(
        CategoryRule.user_id == user_id,
        CategoryRule.match_type == "contains",
    ).all()
    for rule in rules:
        if rule.keyword.lower() in text:
            return rule.category
    return None
```

Usage in `email_sync_service.py` (post-parse step):
```python
user_category = apply_user_rules(db, user_id, parsed.merchant or "", parsed.description)
if user_category:
    parsed.category = user_category
```

Usage in `PUT /api/transactions/{id}` handler when `apply_to_merchant=True`:
1. Update the transaction's category
2. Upsert a `CategoryRule` for `keyword=merchant, category=new_category, user_id=user_id`
3. Bulk-update: `db.query(Transaction).filter(Transaction.user_id==user_id, Transaction.merchant==merchant).update({"category": new_category})`

### Pattern 7: PUT /api/transactions/{id} — category re-assign with apply_to_merchant

The existing `PUT /api/transactions/{id}` uses `TransactionUpdate` which does not have `apply_to_merchant`. Options:

**Option A (recommended):** Add a new `TransactionCategoryUpdate` schema specifically for the inline re-categorize call, keeping `TransactionUpdate` unchanged. The route can check which schema is passed, or create a new dedicated route `PUT /api/transactions/{id}/category`.

**Option B:** Add `apply_to_merchant: Optional[bool] = False` to `TransactionUpdate` and strip it before applying to the model.

Option A is cleaner and avoids mixing concerns. New schema:
```python
class TransactionCategoryUpdate(BaseModel):
    category: str
    apply_to_merchant: bool = False

    @field_validator("category")
    @classmethod
    def category_valid(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(...)
        return v
```

Route: `PUT /api/transactions/{id}/category` (avoids route conflict with existing `PUT /api/transactions/{id}`).

### Pattern 8: Bulk category re-assignment endpoint

```python
class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[int]
    category: str

@router.post("/bulk-categorize")
def bulk_categorize(
    data: BulkCategorizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = db.query(Transaction).filter(
        Transaction.id.in_(data.transaction_ids),
        Transaction.user_id == current_user.id,  # security: only own transactions
    ).update({"category": data.category}, synchronize_session=False)
    db.commit()
    return {"updated": updated}
```

`synchronize_session=False` is the correct SQLAlchemy 2.0 flag for bulk UPDATE without loading objects into session.

### Pattern 9: Merchant breakdown query

The `get_summary()` pattern uses explicit filter lists with `*([condition] if flag else [])`. For merchant breakdown, build a helper method in `transaction_service.py`:

```python
def get_merchant_breakdown(
    self, db: Session, user_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    payment_source: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    query = db.query(
        Transaction.merchant,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
        func.avg(Transaction.amount).label("avg"),
    ).filter(
        Transaction.user_id == user_id,
        Transaction.merchant.isnot(None),
    )
    if date_from:
        query = query.filter(Transaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(Transaction.transaction_date <= date_to)
    if payment_source:
        query = query.filter(Transaction.payment_source == payment_source)
    rows = query.group_by(Transaction.merchant)\
                .order_by(func.sum(Transaction.amount).desc())\
                .limit(limit).all()
    # compute % of total separately
    ...
```

**SQLite GROUP BY note:** SQLite supports `GROUP BY` with aggregate functions (`SUM`, `COUNT`, `AVG`) correctly. The `func.sum().desc()` ordering with `ORDER BY` on an aggregate requires using the label or repeating the aggregate — SQLAlchemy generates this correctly.

### Pattern 10: Merchant autocomplete endpoint

```python
@router.get("/merchants")
def search_merchants(
    q: str = Query("", max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    term = f"%{q}%"
    rows = db.query(Transaction.merchant).filter(
        Transaction.user_id == current_user.id,
        Transaction.merchant.isnot(None),
        Transaction.merchant.ilike(term),
    ).distinct().limit(10).all()
    return {"merchants": [r[0] for r in rows]}
```

Frontend: debounce with `setTimeout`/`clearTimeout` pattern (no library needed). Attach to the `onChange` of the Search field in FilterPanel with a 300ms delay. Display results as `<datalist>` (simplest, native browser support) or a small absolutely-positioned `<ul>`.

### Recommended Project Structure Changes

```
backend/app/
├── models/
│   ├── transaction.py          # add Subscriptions, Utilities, Travel to CATEGORIES
│   └── category_rule.py        # NEW: CategoryRule model
├── schemas/
│   ├── transaction.py          # extend TransactionFilters, TransactionOut, add TransactionCategoryUpdate, BulkCategorizeRequest
│   └── category_rule.py        # NEW: CategoryRuleOut schema (for future use)
├── services/
│   ├── transaction_service.py  # extend list(), get_summary(), add export(), get_merchant_breakdown()
│   └── category_rule_service.py # NEW: apply_user_rules(), upsert_rule(), bulk_update_merchant()
├── api/routes/
│   └── transactions.py         # add new routes (payment-sources, export, merchant-breakdown, merchants, bulk-categorize, /{id}/category)
└── parsers/
    └── categorizer.py          # stays stateless; apply_user_rules() lives in category_rule_service

backend/alembic/versions/
└── <new_hash>_add_category_rules.py    # NEW migration

frontend/src/
├── components/transactions/
│   ├── FilterPanel.jsx          # add payment_source, min/max amount, date presets, merchant autocomplete
│   └── TransactionList.jsx      # add checkbox column, inline category edit, bulk action bar, payment_source display
├── pages/
│   ├── TransactionsPage.jsx     # pass full filters to fetchSummary, add Export CSV button
│   └── AnalyticsPage.jsx        # add payment_source filter dropdown, merchant breakdown table
└── services/
    └── api.js                   # add paymentSources, merchants, merchantBreakdown, export, bulkCategorize, updateCategory
```

### Anti-Patterns to Avoid

- **Passing `db` to `categorize()`:** Changes signature in 4 parser files and makes unit-testing parsers harder. Use `apply_user_rules()` as a separate post-parse step instead.
- **Using `window.location.href` for CSV download:** Will not send the Authorization header. Use `axios` with `responseType: 'blob'` and the Blob URL pattern.
- **Registering `/export`, `/payment-sources`, `/merchants` after `/{tx_id}`:** FastAPI will route `GET /transactions/export` to `GET /transactions/{tx_id}` with `tx_id="export"` which will fail with 422. Always register static paths before path parameters.
- **Bulk UPDATE without `Transaction.user_id == current_user.id`:** Security vulnerability — a user could update other users' transactions by submitting foreign IDs. Always scope bulk operations by user_id.
- **`synchronize_session="evaluate"` (SQLAlchemy default) for bulk UPDATE with `in_()` filter:** May produce incorrect results. Use `synchronize_session=False` for bulk updates.
- **Loading all CategoryRule rows on every parse:** If user has many rules, this hits DB on every email parse. For Phase 5 volume (single user, <100 rules), this is acceptable. No caching needed yet.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV generation | Custom string concatenation | Python stdlib `csv.writer` | Handles quoting, newlines, commas in values automatically |
| Decimal → float in CSV | Manual `str(tx.amount)` | `float(tx.amount)` | `Decimal('1158.00')` stringifies as `'1158.00'`; `float` is fine for CSV |
| Debounce in React | `lodash.debounce` | `setTimeout`/`clearTimeout` in `useEffect` cleanup | No new dependency needed |
| Merchant autocomplete UI | Full autocomplete library | Native `<datalist>` element or small `<ul>` div | 10-item list doesn't need a library |

---

## Common Pitfalls

### Pitfall 1: FastAPI route ordering — static paths before `/{tx_id}`

**What goes wrong:** `GET /transactions/export` matches `/{tx_id}` with `tx_id="export"`, returns 422 (unprocessable entity) or 404.

**Why it happens:** FastAPI matches routes in registration order. Path parameters capture any string.

**How to avoid:** In `routes/transactions.py`, register all new static-path routes (`/payment-sources`, `/export`, `/merchant-breakdown`, `/merchants`, `/bulk-categorize`) BEFORE the `@router.get("/{tx_id}")` route at line 66.

**Warning signs:** 422 error on new endpoint with "value is not a valid integer" message.

### Pitfall 2: TransactionOut schema missing payment_source

**What goes wrong:** The `payment_source` column exists in the DB and SQLAlchemy model, but `TransactionOut` does not declare it (lines 80-94 of `schemas/transaction.py`). Every transaction response silently drops `payment_source`. Frontend cannot display or filter on it.

**How to avoid:** Add `payment_source: Optional[str] = None` to `TransactionOut`. This is a quick fix but easy to forget since the DB already has the column.

### Pitfall 3: CategoryRule model not imported before Alembic autogenerate

**What goes wrong:** `alembic revision --autogenerate` produces an empty migration because Alembic doesn't detect the new `CategoryRule` model.

**Why it happens:** Alembic's `env.py` imports `Base` from `app.database`, but if `CategoryRule` is never imported anywhere in the import chain, SQLAlchemy's `Base.metadata` won't know about it.

**How to avoid:** Add `from app.models.category_rule import CategoryRule` to `app/models/__init__.py` (or wherever other models are imported) before running autogenerate. Check `env.py` to confirm the import chain reaches all models.

### Pitfall 4: get_summary() and fetchSummary() filter mismatch

**What goes wrong:** TXN-07 requires the table header summary to reflect the active filters, but `TransactionsPage.jsx` currently calls `fetchSummary(appliedFilters)` but strips everything except `date_from`/`date_to` before sending to the API (lines 37-44). Adding `payment_source` to the filter panel but not updating `fetchSummary` to pass it will give a wrong total.

**How to avoid:** After extending `get_summary()` in the backend to accept all filter params, update `fetchSummary` in `TransactionsPage.jsx` to pass `payment_source`, `min_amount`, `max_amount` as well.

### Pitfall 5: CATEGORIES validator rejects new categories until both model and schema are updated

**What goes wrong:** Adding `Subscriptions`, `Utilities`, `Travel` to `CATEGORIES` in `transaction.py` but not regenerating a migration means existing transactions are fine, but if existing tests create transactions with hardcoded category strings, they may still pass. However, the Pydantic validator in `TransactionCreate` and `TransactionUpdate` imports `CATEGORIES` at module load time — both model and schema see the same list because schema.py imports from `models/transaction.py`. This part is fine. But the frontend `FilterPanel.jsx` has its own hardcoded `CATEGORIES` list — it must be updated independently.

**How to avoid:** Update `CATEGORIES` in `transaction.py` (one source of truth for backend), update `FilterPanel.jsx` `CATEGORIES` constant, update `TransactionList.jsx` `CATEGORY_COLORS` dict for new categories, and update `AnalyticsPage.jsx` if it references category names explicitly.

### Pitfall 6: Bulk UPDATE after inline re-categorize creates CategoryRule before updating transactions

**What goes wrong:** If `upsert_rule()` commits but the bulk `UPDATE` fails, the rule exists but old transactions aren't updated — inconsistent state.

**How to avoid:** Perform both operations in a single transaction: upsert rule, bulk update, then commit once. Use SQLAlchemy's session to batch both operations before calling `db.commit()`.

### Pitfall 7: SQLite `ilike` case sensitivity

**What goes wrong:** SQLite's `LIKE` is case-insensitive for ASCII but case-sensitive for non-ASCII characters. Merchant names are generally ASCII-safe for Indian banks, but this is worth knowing.

**Impact:** Low. The existing codebase already uses `ilike` (line 57-63 of `transaction_service.py`) without issues. No action needed — just document for awareness.

---

## Code Examples

### Extending TransactionFilters (verified from existing schema pattern)

```python
# Source: backend/app/schemas/transaction.py — extend existing TransactionFilters

class TransactionFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    payment_source: Optional[str] = None      # NEW
    min_amount: Optional[Decimal] = None      # NEW
    max_amount: Optional[Decimal] = None      # NEW
    search: Optional[str] = None
    page: int = 1
    page_size: int = 50
    # existing validators stay unchanged
```

### Date Presets in FilterPanel (frontend, uses existing date-fns)

```javascript
// Source: date-fns already imported in AnalyticsPage.jsx
import {
  startOfDay, endOfDay, startOfWeek, endOfWeek,
  startOfMonth, endOfMonth, subMonths, startOfYear,
  format
} from 'date-fns'

const DATE_PRESETS = [
  { label: 'Today', from: () => startOfDay(new Date()), to: () => endOfDay(new Date()) },
  { label: 'This Week', from: () => startOfWeek(new Date(), { weekStartsOn: 1 }), to: () => endOfWeek(new Date(), { weekStartsOn: 1 }) },
  { label: 'This Month', from: () => startOfMonth(new Date()), to: () => endOfMonth(new Date()) },
  { label: 'Last Month', from: () => startOfMonth(subMonths(new Date(), 1)), to: () => endOfMonth(subMonths(new Date(), 1)) },
  { label: 'Last 3M', from: () => startOfMonth(subMonths(new Date(), 3)), to: () => endOfMonth(new Date()) },
  { label: 'This Year', from: () => startOfYear(new Date()), to: () => endOfDay(new Date()) },
]
// In FilterPanel: call setValue('date_from', format(preset.from(), 'yyyy-MM-dd'))
// react-hook-form's setValue is available via: const { register, handleSubmit, reset, setValue } = useForm()
```

### Inline Category Edit (TransactionList row)

The current edit flow uses a full-row `TransactionForm` (lines 101-119 of `TransactionList.jsx`). Inline category re-assign is a simpler UX — replace the category badge with a `<select>` in-place when edit mode active, with a checkbox "Apply to all from this merchant".

```jsx
// Pattern: local state per row
const [categoryEdit, setCategoryEdit] = useState(null) // { txId, value, applyToMerchant }

// Render category cell when editing:
{categoryEdit?.txId === tx.id ? (
  <div className="flex items-center gap-2">
    <select value={categoryEdit.value} onChange={e => setCategoryEdit({...categoryEdit, value: e.target.value})}>
      {CATEGORIES.map(c => <option key={c}>{c}</option>)}
    </select>
    <label className="flex items-center gap-1 text-xs">
      <input type="checkbox"
        checked={categoryEdit.applyToMerchant}
        onChange={e => setCategoryEdit({...categoryEdit, applyToMerchant: e.target.checked})}
        disabled={!tx.merchant}
      />
      Apply to all from {tx.merchant || 'this merchant'}
    </label>
    <button onClick={() => saveCategoryEdit(tx)}>Save</button>
    <button onClick={() => setCategoryEdit(null)}>Cancel</button>
  </div>
) : (
  <span className={`badge ...`} onClick={() => setCategoryEdit({txId: tx.id, value: tx.category, applyToMerchant: false})}>
    {tx.category}
  </span>
)}
```

### Merchant Breakdown Table in AnalyticsPage

The Analytics page already has a category detail table (lines 122-157). Merchant breakdown follows the same structure below it. The endpoint response shape:

```json
{
  "merchants": [
    {
      "merchant": "Swiggy",
      "total": 8540.0,
      "count": 12,
      "avg": 711.67,
      "pct_of_total": 23.4
    }
  ],
  "total_amount": 36500.0
}
```

### CSV export trigger from frontend (blob download)

```javascript
// In api.js:
export: (params) => api.get('/transactions/export', { params, responseType: 'blob' }),

// In TransactionsPage.jsx:
async function handleExport() {
  const res = await transactionsApi.export(filters)
  const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'transactions.csv'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
```

---

## Environment Availability

Step 2.6: SKIPPED — Phase 5 is purely code/config changes. All required packages are already installed. No external services or CLI tools beyond the existing stack are needed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && source venv/Scripts/activate && python -m pytest tests/test_transaction_service.py -x -q` |
| Full suite command | `cd backend && source venv/Scripts/activate && python -m pytest -x -q` |
| Current test count | 42 tests collected |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TXN-05 | `list()` filters by payment_source, min_amount, max_amount | unit | `pytest tests/test_transaction_service.py::test_filter_payment_source -x` | Wave 0 |
| TXN-07 | `get_summary()` respects payment_source + amount range filters | unit | `pytest tests/test_transaction_service.py::test_summary_with_filters -x` | Wave 0 |
| TXN-08 | `export()` returns correct CSV rows for filtered set | unit | `pytest tests/test_transaction_service.py::test_export_csv -x` | Wave 0 |
| TXN-11 | PUT /transactions/{id}/category with `apply_to_merchant=True` creates rule + bulk updates | unit | `pytest tests/test_transaction_service.py::test_recategorize_with_rule -x` | Wave 0 |
| TXN-12 | POST /transactions/bulk-categorize updates only current user's transactions | unit | `pytest tests/test_transaction_service.py::test_bulk_categorize -x` | Wave 0 |
| CAT-03 | CATEGORIES list contains Subscriptions, Utilities, Travel | unit | `pytest tests/test_category_rules.py::test_categories_extended -x` | Wave 0 |
| CAT-04 | `apply_user_rules()` returns user rule match before hardcoded fallback | unit | `pytest tests/test_category_rules.py::test_user_rule_takes_precedence -x` | Wave 0 |
| CAT-04 | `apply_user_rules()` returns None when no rule matches | unit | `pytest tests/test_category_rules.py::test_no_rule_match -x` | Wave 0 |
| PAY-02 | `TransactionOut` serializes `payment_source` field | unit | `pytest tests/test_transaction_service.py::test_transaction_out_has_payment_source -x` | Wave 0 |
| PAY-05 | GET /payment-sources returns distinct non-null values for user | unit | `pytest tests/test_transaction_service.py::test_payment_sources_endpoint -x` | Wave 0 |
| ANA-07 | `get_merchant_breakdown()` returns top 10 sorted by total desc | unit | `pytest tests/test_transaction_service.py::test_merchant_breakdown -x` | Wave 0 |
| ANA-09 | GET /merchants?q= returns up to 10 matching distinct merchants | unit | `pytest tests/test_transaction_service.py::test_merchant_search -x` | Wave 0 |
| Migration | Alembic upgrade head creates `category_rules` table with correct columns | integration | `pytest tests/test_migrations.py -x` | Extend existing |

**Frontend requirements (TXN-06, TXN-10, PAY-03, PAY-04, ANA-08):** These are UI/visual requirements. No backend tests cover them. Verified manually by running the dev server and checking browser behavior. Mark as manual-only.

### Sampling Rate

- **Per task commit:** `cd backend && source venv/Scripts/activate && python -m pytest tests/test_transaction_service.py tests/test_category_rules.py -x -q`
- **Per wave merge:** `cd backend && source venv/Scripts/activate && python -m pytest -x -q` (full 42+ test suite)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_transaction_service.py` — covers TXN-05, TXN-07, TXN-08, TXN-11, TXN-12, PAY-02, PAY-05, ANA-07, ANA-09
- [ ] `backend/tests/test_category_rules.py` — covers CAT-03, CAT-04 (apply_user_rules logic)
- [ ] `backend/tests/conftest.py` — add `user_with_transactions` fixture (user + N transactions, some with merchant names, some with payment_source values) to support service-level tests

**Extend existing:**
- [ ] `backend/tests/test_migrations.py` — add assertion that `category_rules` table exists after upgrade head

*(42 existing tests must remain green — no regressions.)*

---

## Open Questions

1. **`env.py` model import chain**
   - What we know: `env.py` imports `Base` from `app.database`. The existing models (`Transaction`, `User`, `EmailMetadata`, etc.) are imported somewhere that makes them visible to `Base.metadata`.
   - What's unclear: Whether adding `category_rule.py` to `app/models/` alone is sufficient, or if an explicit import is needed in `env.py` or `app/models/__init__.py`.
   - Recommendation: During Wave 1 (migration task), check the existing import chain by running `python -c "from app.database import Base; print(Base.metadata.tables.keys())"` in the backend venv before running autogenerate. If `category_rules` is not listed, add the import.

2. **`TransactionsPage.jsx` fetchSummary filter scope**
   - What we know: Currently `fetchSummary` strips all filters except `date_from`/`date_to` (lines 37-44).
   - What's unclear: Whether `payment_source` should also be passed to summary for TXN-07, or if summary should always be unfiltered by payment source.
   - Recommendation: Per D-11 and D-18, pass all active filters (including `payment_source`, `min_amount`, `max_amount`) to summary. The count/sum in the header should reflect the actual filtered view.

3. **Merchant breakdown `% of total` calculation**
   - What we know: The endpoint should return `pct_of_total` per D-15. The total for the percentage must be the total for the entire filtered period (not just the top 10 merchants).
   - Recommendation: Compute total separately, then calculate pct in the service layer before returning. Do not delegate to frontend.

---

## Sources

### Primary (HIGH confidence)
- Live codebase — `backend/app/services/transaction_service.py`, `routes/transactions.py`, `schemas/transaction.py`, `models/transaction.py`, `parsers/categorizer.py` — read directly
- Live codebase — `frontend/src/components/transactions/FilterPanel.jsx`, `TransactionList.jsx`, `pages/TransactionsPage.jsx`, `pages/AnalyticsPage.jsx`, `services/api.js` — read directly
- Live codebase — `backend/tests/conftest.py`, `pytest.ini`, existing test files — read directly
- Live codebase — `backend/alembic/versions/628c6541bc23_add_payment_source.py` — migration pattern confirmed

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 docs pattern for `synchronize_session=False` — consistent with what's used in codebase
- FastAPI StreamingResponse + CSV pattern — stdlib `csv` module usage is well-established

### Tertiary (LOW confidence)
- None. All findings grounded in live codebase or stdlib.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via `pip show` + live code imports
- Architecture: HIGH — all patterns derived directly from existing code
- Pitfalls: HIGH — identified from actual code gaps (TransactionOut missing payment_source, route ordering issue, filter mismatch)
- Test infrastructure: HIGH — verified via pytest --collect-only (42 tests) and pytest.ini

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stack; no fast-moving dependencies)
