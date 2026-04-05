# Phase 5: Data Quality - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the transaction table a first-class feature: richer filtering (payment source, amount range, date presets), inline category re-assignment with rule persistence, merchant analytics on the Analytics page, and CSV export. CSV upload is explicitly deferred to v2.

CAT-06 (Unclassified vs Others) is NOT in scope — "Others" stays as-is.

</domain>

<decisions>
## Implementation Decisions

### Category Rules Engine
- **D-01:** No full regex rules engine or Settings rules editor. Keep it simple: inline re-assignment on a transaction row with an "Apply to all future transactions from this merchant" checkbox.
- **D-02:** When user re-categorizes a transaction and checks "apply to future": (a) create a contains-rule in the DB (merchant name → category), AND (b) retroactively update all existing transactions with the same merchant to the new category. Both happen together.
- **D-03:** Category rules stored in a new `CategoryRule` DB table: `(id, user_id, keyword, match_type='contains', category, created_at)`. Only `contains` match type needed — no regex, exact, starts_with for now.
- **D-04:** Auto-categorizer at import time checks DB rules first (user rules take precedence over hardcoded keywords), then falls back to hardcoded `CATEGORY_RULES` in `categorizer.py`.
- **D-05:** Extended taxonomy — add `Subscriptions`, `Utilities`, `Travel` to the category list (CAT-03). These go into both the Transaction model `CATEGORIES` constant and the frontend `FilterPanel`.

### "Others" / Unclassified
- **D-06:** No changes to "Others" category. CAT-06 is deferred. Transactions that don't match any rule continue to land in "Others".

### CSV Upload
- **D-07:** TXN-13 (CSV file upload) is explicitly OUT OF SCOPE for Phase 5. Moved to v2 requirements. Do not implement.

### Filtering Enhancements
- **D-08:** Add payment source filter to the transaction filter panel. `GET /api/payment-sources` returns distinct payment_source values for the current user (non-null only). Frontend populates a dropdown from this.
- **D-09:** Add amount range filter: min_amount and max_amount query params on the transactions list endpoint.
- **D-10:** Add quick date preset buttons: Today / This Week / This Month / Last Month / Last 3 Months / This Year. These are frontend-only — they set the date_from/date_to fields in the filter form.
- **D-11:** Filtered view shows total transaction count and sum in the table header area (e.g. "42 transactions · ₹15,230.00"). This comes from the existing `/api/transactions/summary` endpoint extended to respect all active filters.

### CSV Export
- **D-12:** Filtered transaction view exportable to CSV via a new `GET /api/transactions/export` endpoint. Accepts same filter params as the list endpoint, returns a CSV file. Frontend has an "Export CSV" button that triggers a download.
- **D-13:** CSV columns: Date, Amount, Description, Merchant, Category, Payment Method, Payment Source, Notes.

### Merchant Analytics
- **D-14:** Merchant breakdown goes on the **Analytics page**, below all existing charts (category pie + payment method bar). NOT on the transactions page.
- **D-15:** Show top 10 merchants by total spend for the selected date range (same date range already used by the analytics charts). Columns: Merchant, Total Spend, Transaction Count, Avg per Transaction, % of Total.
- **D-16:** ANA-08 (top merchants on dashboard) also goes on the Analytics page — same section, same component.
- **D-17:** Merchant autocomplete for the transaction search field (ANA-09): when the user types in the Search box in FilterPanel, suggest matching merchants from the user's transaction history. `GET /api/merchants?q=<query>` returns top 10 matching merchant names.

### Payment Source Filtering
- **D-18:** Analytics charts (category pie + payment method bar) respond to the payment source filter — add `payment_source` as an optional filter param to `GET /api/transactions/summary`.
- **D-19:** Payment source filter is a single-select dropdown (not multi-select) — simpler implementation, sufficient for the use case.

### Bulk Category Re-assignment
- **D-20:** TXN-12 (bulk re-assignment): user can select multiple transaction rows (checkboxes) and apply a category to all selected at once. No "apply to future" option in bulk mode — just change the category on selected rows.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Transaction Layer
- `backend/app/models/transaction.py` — Transaction model, CATEGORIES constant (add Subscriptions, Utilities, Travel)
- `backend/app/api/routes/transactions.py` — existing filter params (add payment_source, min_amount, max_amount, export endpoint)
- `backend/app/services/transaction_service.py` — list(), get_summary() to extend
- `backend/app/schemas/transaction.py` — TransactionFilters schema to extend

### Categorizer
- `backend/app/parsers/categorizer.py` — hardcoded CATEGORY_RULES (fallback), categorize() function to update
- `backend/app/parsers/base_parser.py` — ParsedTransaction dataclass (uses category from categorize())

### Frontend
- `frontend/src/components/transactions/FilterPanel.jsx` — extend with payment source, amount range, date presets
- `frontend/src/components/transactions/TransactionList.jsx` — add inline category edit, bulk select, total/sum display
- `frontend/src/pages/AnalyticsPage.jsx` — add merchant breakdown section below existing charts
- `frontend/src/services/api.js` — add payment-sources and merchants endpoints

### Requirements
- `.planning/REQUIREMENTS.md` — TXN-05 through TXN-12 (TXN-13 deferred), CAT-03 through CAT-07 (CAT-06 no change), PAY-02 through PAY-05, ANA-07 through ANA-09

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FilterPanel.jsx` — already a form with react-hook-form, date range, category, payment method, search. Extend in place.
- `TransactionList.jsx` — existing table component; add checkbox column and category inline edit
- `AnalyticsPage.jsx` — existing charts section; add merchant table below
- `GET /api/transactions/summary` — already returns category/payment breakdown for date range; extend to accept payment_source filter
- `transaction_service.list()` — already supports date, category, payment_method, search filters; extend for payment_source, amount range

### Established Patterns
- Alembic migrations — new `CategoryRule` table goes in a new migration (same pattern as Phase 3/4)
- `settings` from `app/config.py` (Pydantic BaseSettings) — no new settings needed
- Frontend: Tailwind CSS utility classes, no component library
- All filter state managed via URL params / form state in FilterPanel + TransactionList

### New DB Table Needed
- `category_rules` table: `id`, `user_id` (FK users), `keyword` (str), `match_type` (str, default 'contains'), `category` (str), `created_at` — via Alembic migration

### Integration Points
- `categorize()` in `categorizer.py` — needs `db` and `user_id` passed in so it can check user rules first. This changes the call signature everywhere `categorize()` is called.
- OR: keep `categorize()` stateless (no DB), add a separate `apply_user_rules(db, user_id, transaction)` step in `email_sync_service.py` post-parse.
- Recommendation: keep `categorize()` stateless (simpler), apply user rules as a DB-lookup step only at import time and on re-categorize.

</code_context>

<specifics>
## Specific Implementation Notes

- **Date presets:** Frontend-only. Buttons set `date_from`/`date_to` in the filter form, no backend changes.
- **"Apply to future" flow:** On inline category change + checkbox → POST to new `PUT /api/transactions/{id}` with `{category, apply_to_merchant: true}`. Backend: (1) update the transaction, (2) insert/upsert CategoryRule, (3) bulk-update all transactions for that user+merchant.
- **Merchant autocomplete:** Debounced input on Search field → `GET /api/merchants?q=swiggy` → show dropdown. Keep it lightweight — no full autocomplete library needed, just a simple `<datalist>` or small dropdown div.
- **CSV export:** Use Python's built-in `csv` module + `io.StringIO`, return `StreamingResponse` with `Content-Disposition: attachment; filename=transactions.csv`.
- **Merchant breakdown query:** `SELECT merchant, SUM(amount), COUNT(*), AVG(amount) FROM transactions WHERE user_id=? AND date BETWEEN ? AND ? GROUP BY merchant ORDER BY SUM(amount) DESC LIMIT 10`
- **Payment source dropdown:** Fetch once on page load (or filter change), not on every keystroke.

</specifics>

<deferred>
## Deferred / Out of Scope

- **TXN-13: CSV file upload** — explicitly deferred to v2. Do not implement.
- **CAT-06: Unclassified separate from Others** — no changes to Others category.
- **CAT-05: Match types (regex, exact, starts_with)** — only `contains` match type implemented. Other types deferred.
- **CAT-07: Settings rules editor** — no dedicated settings page for rules. Inline editing is the UX.
- **PARSE-05 through PARSE-08: Additional bank parsers** — deferred (Axis, IDFC, Kotak, Flash.co).

</deferred>

---
*Phase: 05-data-quality*
*Context gathered: 2026-04-06*
