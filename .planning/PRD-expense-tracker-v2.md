# Product Requirements Document
## Expense Tracker — Dashboard v2.0

**Author:** Rahul
**Last Updated:** April 2026
**Status:** Draft v2 (updated to reflect actual codebase)
**Stack:** FastAPI · SQLite · React 18 · Recharts · Tailwind CSS

---

## 1. Overview & Vision

The Expense Tracker is a self-hosted, privacy-first personal finance tool that automatically imports transactions from Gmail (major Indian banks) and provides actionable analytics.

**Vision for v2.0:** Move from a passive data viewer to an active financial intelligence tool — one that surfaces patterns, flags anomalies, helps users set and track budgets, and is polished enough to publish for other users.

**Dual Goals:**
- **Personal:** Deep, actionable insight into where money is going so spending can be consciously controlled.
- **Product:** A publishable, multi-user-ready personal finance dashboard that others can self-host.

**Design Constraint:** All UI must be fully responsive — the dashboard must look and function well on both mobile and desktop without separate builds.

---

## 2. Current State (v1.0 Baseline — Actual)

### What Actually Exists

- JWT + TOTP 2FA authentication (bcrypt passwords, Fernet-encrypted TOTP secrets)
- Manual transaction entry (CRUD) with categories and payment methods
- Gmail OAuth2 integration (read-only scope, token encrypted at rest)
- HDFC Bank email parser — UPI debit + Credit Card alerts (regex-based)
- Email deduplication by Gmail message ID
- Category breakdown and payment method breakdown (pie/bar charts) for a date range
- Date range filtering on transactions

### What Does NOT Exist Yet (Despite Being Planned)

- CSV / Excel upload — blocked by `pandas` on Python 3.14 dev machine; works on Linux VPS
- Time-series / trend charts (daily / weekly / monthly / annual)
- Budget or spending goal tracking
- Pattern analysis, anomaly detection, insights feed
- Automated email sync (cron) — currently manual only
- ICICI, SBI, Axis, IDFC, Kotak, Flash.co parsers
- Settings page
- Mobile-responsive layout

### Known Bugs / Technical Debt (Must Fix)

These are pre-requisites woven into the phase plan:

1. **Gmail token refresh not persisted** — after an access token expires, the refreshed token is discarded. If Google rotates the refresh token, Gmail connection breaks silently. Fix: persist re-encrypted credentials to DB after refresh.
2. **`parse_failed` conflates parse errors with unmatched emails** — fix by using separate `"unmatched"` counter.
3. **`email_retention_days` setting ignored** — hardcoded `timedelta(days=30)` in sync service. Fix: use `settings.email_retention_days`.
4. **No cleanup job for expired `EmailMetadata` rows** — `delete_after` column exists but nothing acts on it.
5. **Alembic installed but no migration files** — app uses `Base.metadata.create_all()` at startup. Must generate initial migration before first column additions in v2.
6. **HDFC date fallback to `date.today()`** — if date parsing fails, transaction is stamped with import date not actual date. Fix: fall back to `email["received_at"]` (Gmail's `internalDate`).

### Key Gaps (Prioritised)

1. Email sync is manual — needs scheduled/automatic sync
2. Bank support limited to HDFC — needs all major Indian banks
3. No time-series / trend views (daily / weekly / monthly / annual)
4. No budget or spending goal setting
5. Weak pattern analysis — anomalies go unnoticed
6. Payment method filter too coarse (Credit Card / UPI binary only — no per-card breakdown)
7. "Others" category is high — needs sub-categories + smarter classification
8. No proactive insights or pattern summaries surfaced to the user

---

## 3. User Personas

### Persona A — Rahul (Primary / Power User)
- Technically proficient, self-hosts the app
- Wants granular control and deep insight
- Has multiple credit cards + UPI accounts across major Indian banks
- Goal: identify spending leakage, set intentional budgets, spot unusual charges fast

### Persona B — General Self-Hoster (Future Launch)
- Non-technical to moderately technical
- Wants a clean, guided setup
- Needs sensible defaults (auto-categories, suggested budgets)
- Goal: understand spending without maintaining spreadsheets manually

---

## 4. Feature Requirements

Features are grouped into four delivery phases. Priority: P0 = must-have, P1 = high value, P2 = nice-to-have.

---

### Phase 1 (New: Phase 4) — Automated Email Sync
*Goal: Make sync automatic and reliable.*

---

#### F-01 · Automated Email Sync (Cron Job)
**Priority:** P0

**Description:** Replace the manual sync button with an automated background job that syncs Gmail transactions on a configurable schedule. The manual trigger remains available for on-demand use.

**Acceptance Criteria:**
- [ ] Scheduler runs as a background service within the FastAPI app using APScheduler
- [ ] Default schedule: daily at a configurable time (e.g., 02:00 AM)
- [ ] User-configurable frequency via Settings: hourly / every 6h / daily / custom cron expression
- [ ] Dashboard header shows: "Last synced: 2 hours ago" with a manual "Sync Now" button still available
- [ ] Sync runs are logged: timestamp, emails processed, transactions imported, errors
- [ ] If a sync fails (Gmail API error, auth expiry), the app surfaces an in-app alert — not silent failure
- [ ] Duplicate detection: re-scanning the same emails does not create duplicate transactions
- [ ] On first launch after Gmail connect, a sync runs automatically

**Also fix in this phase:**
- [ ] Persist refreshed Gmail credentials to DB (bug #1 above)
- [ ] Use `settings.email_retention_days` not hardcoded 30 days (bug #3)
- [ ] Add cleanup job for expired `EmailMetadata` rows (bug #4)

**Backend Implementation:**
```python
# APScheduler with AsyncIOScheduler — add to backend/app/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(sync_all_users, 'cron', hour=2, minute=0)
scheduler.start()
```

> **Note:** APScheduler must be compatible with Python 3.14. Verify wheel availability before adding to `requirements.txt`. Check `apscheduler>=3.10` for pre-built wheels.

New DB tables (via Alembic migration):
```sql
CREATE TABLE sync_log (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  emails_scanned INTEGER DEFAULT 0,
  transactions_imported INTEGER DEFAULT 0,
  status TEXT,  -- 'success' | 'partial' | 'failed'
  error_message TEXT
);

CREATE TABLE sync_config (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  frequency TEXT DEFAULT 'daily',
  cron_expression TEXT DEFAULT '0 2 * * *',
  enabled BOOLEAN DEFAULT TRUE,
  UNIQUE(user_id)
);
```

New API endpoints:
```
GET  /api/sync/status          -- last sync time, status, counts
POST /api/sync/trigger         -- manual on-demand sync
GET  /api/sync/logs            -- sync history
GET  /api/settings/sync        -- get sync schedule config
PUT  /api/settings/sync        -- update sync schedule
```

**Frontend:**
- Move current GmailSync component's "Sync Emails" button to a persistent `SyncStatusBadge` in the top nav/header
- Header shows: "Last synced: Xh ago · Sync Now"
- New Settings page with Sync Schedule section + next run time display
- Sync log viewer in Settings for debugging

---

### Phase 2 (New: Phase 3) — Multi-Bank Parser Framework
*Goal: Parse all major Indian banks.*

---

#### F-02 · Multi-Bank Parser Framework
**Priority:** P0

**Description:** Extend Gmail parsing to support all major Indian banks. The parser system must be modular so new banks can be added without touching core code.

**Banks to Support (v2.0):**

| Bank | Email Patterns | Status |
|---|---|---|
| HDFC Bank | Credit card alerts, UPI debit alerts | ✅ Done |
| ICICI Bank | Credit card transaction alerts, iMobile alerts | 🔲 Phase 3 |
| SBI | Credit card spend alerts, YONO alerts | 🔲 Phase 3 |
| Axis Bank | Edge card alerts, UPI notifications | ⏸ Deferred |
| IDFC First Bank | Credit card/FASTag alerts | ⏸ Deferred |
| Kotak Mahindra | Credit card alerts | ⏸ Deferred |
| Flash.co | Spend alerts | ⏸ Deferred |

**Acceptance Criteria:**
- [ ] Each bank has its own parser class inheriting from `BaseEmailParser` (already defined at `backend/app/parsers/base_parser.py`)
- [ ] `parser_factory.py` `PARSERS` list updated — no other core code changes needed
- [ ] Each parser extracts: amount, merchant, date, transaction type, card/account identifier
- [ ] Parsers are testable in isolation using sample email fixtures in `backend/tests/fixtures/bank_emails/`
- [ ] Fix `parse_failed` / `unmatched` conflation (bug #2 above)

**Existing Architecture (actual):**
```python
# Already exists at backend/app/parsers/base_parser.py
class BaseEmailParser(ABC):
    @property
    def bank_name(self) -> str: ...
    @property
    def sender_patterns(self) -> list[str]: ...
    @property
    def subject_patterns(self) -> list[str]: ...
    def can_parse(self, sender, subject, body) -> bool: ...
    def parse(self, body, subject) -> Optional[ParsedTransaction]: ...

# Already exists at backend/app/parsers/parser_factory.py
PARSERS: list[BaseEmailParser] = [
    HDFCParser(),
    # ICICIParser(),   # Phase 3
    # SBIParser(),     # Phase 3
]
```

Adding a new bank = create `backend/app/parsers/{bank}_parser.py` + add to `PARSERS` list. No registry abstraction needed — the list IS the registry.

**Also fix in this phase:**
- [ ] HDFC date fallback: use `email["received_at"]` instead of `date.today()` (bug #6)
- [ ] Update Gmail query in `gmail_service.py` to cover all supported sender domains

---

### Phase 3 (New: Phase 5) — Data Quality: Categories, Payment Methods, Filtering

---

#### F-03 · Sub-Categories & Smart Auto-Classification
**Priority:** P0

**Existing category set** (defined in `backend/app/models/transaction.py`):
```python
CATEGORIES = ["Rent", "Groceries", "Shopping", "Electricity",
              "Food & Dining", "Transport", "Entertainment", "Healthcare", "Others"]
```

**Target taxonomy (v2.0):**
```
Food & Dining       → Restaurants, Cafes, Food Delivery (Swiggy, Zomato)
Transport           → Fuel, Cab (Ola, Uber), Metro, Auto, FASTag
Groceries           → Supermarkets, BigBasket, Zepto, Blinkit
Shopping            → Amazon, Flipkart, Myntra
Entertainment       → OTT (Netflix, Prime), Gaming, Movies
Health              → Pharmacy, Doctor, Hospital, Gym
Subscriptions       → Recurring monthly/annual charges
Utilities           → Electricity, Internet, Mobile recharge
Rent & Housing
Travel              → Flights, Hotels, IRCTC
Others (catch-all)
```

**Acceptance Criteria:**
- [ ] Keyword-to-category mapping table stored in DB (user-editable)
- [ ] Merchant name matching: exact → fuzzy fallback ("SWGY*" maps to Food Delivery)
- [ ] Auto-classification runs on import; unclassified flagged for manual review
- [ ] User can re-classify any transaction inline from the transaction table
- [ ] Bulk re-classify: select multiple → assign category
- [ ] When user reclassifies a merchant, offer "Apply to all future transactions from this merchant?"
- [ ] Category rules editor in Settings page
- [ ] Existing `categorizer.py` keyword map extended — new DB-backed rules override it

**Backend — new DB table:**
```sql
CREATE TABLE category_rules (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  keyword TEXT NOT NULL,
  match_type TEXT DEFAULT 'contains',  -- 'exact' | 'contains' | 'starts_with' | 'regex'
  category TEXT NOT NULL,
  priority INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```
GET  /api/categories
POST /api/categories/rules
DELETE /api/categories/rules/{id}
PATCH /api/transactions/{id}/category
POST /api/transactions/bulk-categorise
```

---

#### F-04 · Granular Payment Method Filtering
**Priority:** P0

**Existing model** (`backend/app/models/transaction.py`):
```python
PAYMENT_METHODS = ["Credit Card", "UPI", "Cash", "Debit Card", "Net Banking", "Others"]
# column: payment_method (TEXT)
```

The PRD's original `payment_type` concept maps to the existing `payment_method` column. The change needed is:
1. Add a new `payment_source` column (specific card/account, e.g. "HDFC Regalia ••4521")
2. `payment_method` stays as the type; `payment_source` is the specific instrument

**Acceptance Criteria:**
- [ ] Add `payment_source TEXT` column via Alembic migration (nullable — null valid for cash)
- [ ] All bank parsers populate `payment_source` from card-ending digits in email
- [ ] Multi-select filter by specific payment source on dashboard and transaction table
- [ ] Charts and analytics respond to payment source filter
- [ ] `GET /api/payment-sources` — returns distinct sources for the current user

---

#### F-05 · Enhanced Transaction Table & Filtering
**Priority:** P1

**Acceptance Criteria:**
- [ ] Filters: date range, category (multi-select), payment source (multi-select), merchant (multi-select with search autocomplete), amount range
- [ ] Quick date presets: Today / This Week / This Month / Last Month / Last 3M / This Year / Custom
- [ ] Sort by: date, amount, merchant (ascending/descending)
- [ ] Pagination (default 50 rows — already backend-supported)
- [ ] Export filtered view to CSV
- [ ] Transaction total and count shown in table header for filtered view
- [ ] Mobile: table collapses to a card list view

**Backend:**
```
GET /api/transactions?category=food,transport&payment_source=hdfc_4521&merchant=swiggy&min_amount=100&max_amount=5000&sort=amount_desc&page=1&limit=50&period=this_month
GET /api/merchants?search=swi   -- autocomplete endpoint
```

---

#### F-05a · Merchant Analytics & Breakdown
**Priority:** P1

**Acceptance Criteria:**
- [ ] Merchant breakdown table: Name / Total / Transactions / Avg / % of total
- [ ] Payment method split per merchant inline
- [ ] Clicking merchant row filters transaction table
- [ ] "Top 10 merchants by spend" on main dashboard

**Backend:**
```
GET /api/analytics/merchants?period=this_month&sort=total_desc&limit=20
```

---

#### F-06 · Improved Manual Transaction Entry (incl. CSV Upload)
**Priority:** P0

**Acceptance Criteria:**
- [ ] Floating "+ Add Transaction" FAB always visible (bottom-right on mobile)
- [ ] Fields: Date, Amount (₹), Merchant, Category (searchable dropdown), Payment Method, Payment Source (conditional), Notes
- [ ] Cash transactions: `payment_method="Cash"`, `payment_source=null`
- [ ] Inline validation with clear error messages
- [ ] After save, dashboard updates without full reload
- [ ] Edit and delete on any manually-entered transaction
- [ ] CSV upload: `POST /api/transactions/upload` — accepts CSV file, maps columns, preview before import

> **CSV/Excel note:** `pandas` and `openpyxl` are commented out in `backend/requirements.txt` due to Python 3.14 build constraints on Windows. CSV-only import can use Python's stdlib `csv` module without pandas. Excel (`.xlsx`) requires `openpyxl` — available on Linux VPS target.

---

### Phase 4 (New: Phase 6) — Analytics & Trend Views

---

#### F-07 · Flexible Time-Comparison & Trend View
**Priority:** P0

**Time Granularities:**

| View | Description | Chart Type |
|---|---|---|
| Daily | Spend per day for a selected date range | Bar chart |
| Weekly | Spend per calendar week | Bar chart |
| Monthly | Spend per month for trailing N months | Line + Bar |
| Annual | Spend per year (YoY comparison) | Bar chart |

**Acceptance Criteria:**
- [ ] Granularity selector: Daily / Weekly / Monthly / Annual
- [ ] Category overlay: toggle individual categories on/off
- [ ] Comparison callout: "X% more/less this period vs last period"
- [ ] Drill-down: clicking a bar filters the transaction table to that period
- [ ] Chart responsive — scrollable horizontally on mobile

**Backend:**
```
GET /api/analytics/trends?granularity=weekly&months=3&category=food,transport
Response: [{ period: "2026-W13", label: "Mar W3", total: 3200, categories: { food: 1400 } }]
```

**Frontend:** `TrendChart` using Recharts `ComposedChart` — reuses the existing Recharts dependency already in `frontend/package.json`.

---

#### F-08 · Budget Setting per Category
**Priority:** P0

**Acceptance Criteria:**
- [ ] Budget setup screen: set a monthly limit (₹) for any category
- [ ] Optional: total monthly spending cap across all categories
- [ ] Dashboard shows progress bar per category: green (<75%) / amber (75–90%) / orange (>90%) / red (>100%)
- [ ] Summary card: "X of Y budgets on track this month"
- [ ] Budgets auto-reset at start of each calendar month

**Backend:**
```sql
CREATE TABLE budgets (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  category TEXT NOT NULL,
  monthly_limit REAL NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, category)
);
```

```
GET  /api/budgets
POST /api/budgets
PUT  /api/budgets/{id}
DELETE /api/budgets/{id}
```

---

#### F-09 · Spending Goal Tracking
**Priority:** P1

**Acceptance Criteria:**
- [ ] User sets a monthly savings target (optional)
- [ ] Dashboard shows projected month-end spend based on current burn rate
- [ ] "At this rate, you'll spend ₹18,400 by month end — ₹1,600 over your ₹16,800 goal"
- [ ] Historical goal achievement shown as win/loss per month

---

### Phase 5 (New: Phase 7) — Pattern Detection & Insights

---

#### F-10 · Anomaly Detection
**Priority:** P0

**Detection Rules (v1 — rule-based):**
1. Transaction amount > 2× the user's median spend at that merchant
2. Category spend this period > 50% above the same-period average
3. New merchant never seen before and amount > ₹2,000
4. Same merchant, same amount, same day (likely double-charge)

**Acceptance Criteria:**
- [ ] Anomaly detection runs async after each sync batch
- [ ] Dashboard shows "Alerts" badge with count when unreviewed anomalies exist
- [ ] Anomaly panel shows: merchant, amount, reason ("42% above your usual spend here")
- [ ] User can: dismiss (expected) or mark as "investigate"
- [ ] Minimum threshold ₹200 to reduce noise

**Backend:**
```sql
CREATE TABLE anomalies (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  transaction_id INTEGER REFERENCES transactions(id),
  rule_triggered TEXT,
  reason TEXT,
  status TEXT DEFAULT 'unreviewed',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

#### F-11 · Recurring Transaction Detection
**Priority:** P1

**Detection Logic:** Same merchant in 2+ consecutive months, similar amount (±10%), similar day of month (±5 days).

**Acceptance Criteria:**
- [ ] Subscriptions section on dashboard: list of detected recurring charges with monthly total
- [ ] User can mark detected item as "not recurring"
- [ ] Alert if a known recurring charge is missing for the current month
- [ ] Estimated monthly subscription spend shown as a summary number

**Backend:**
```sql
CREATE TABLE recurring_patterns (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  merchant TEXT NOT NULL,
  avg_amount REAL,
  frequency TEXT DEFAULT 'monthly',
  last_seen TIMESTAMP,
  is_confirmed BOOLEAN DEFAULT FALSE,
  user_dismissed BOOLEAN DEFAULT FALSE
);
```

---

#### F-12 · Rule-Based Spending Pattern Insights
**Priority:** P1

**Example Insights (all rule-based — no LLM):**
- "You spent 23% more on Food & Dining this week vs your 4-week average"
- "Your biggest single spend this month was ₹4,200 at [Merchant]"
- "You have 4 active subscriptions totalling ₹1,340/month"
- "Weekend spending (Sat/Sun) is 2.3× your weekday average"

**Acceptance Criteria:**
- [ ] Insights feed shows up to 5 insights, computed fresh daily
- [ ] Each insight has a category tag and sentiment: positive / neutral / warning
- [ ] Insights dismissible (suppressed 7 days per rule, then re-evaluated)
- [ ] Insights cached in DB — computed once daily, not on every page load
- [ ] Feed clearly labelled as rule-based; designed to be LLM-compatible later
- [ ] If < 2 weeks of data: "Not enough data yet" state shown

**Backend:**
```sql
CREATE TABLE insights (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  rule_key TEXT,
  type TEXT,
  message TEXT,
  severity TEXT DEFAULT 'neutral',
  data_json TEXT,
  dismissed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP
);
```

---

### Phase 6 (New: Phase 8) — Polish & Publishing Readiness

---

#### F-13 · Responsive Dashboard Layout Overhaul
**Priority:** P1

**Mobile Layout (< 768px):**
- Single column layout
- Trend chart: horizontally scrollable
- Transaction table: card list view
- Floating action button (FAB) for "+ Add Transaction"
- Bottom navigation bar: Dashboard / Transactions / Budgets / Settings

**Desktop Layout (≥ 768px):**
- Side navigation (replaces current top nav)
- 2–3 column grid for summary cards
- Charts side-by-side where space allows

**Acceptance Criteria:**
- [ ] No horizontal scrolling on mobile (except trend chart intentionally)
- [ ] Touch targets minimum 44×44px on mobile
- [ ] Dark mode toggle (system preference respected by default)
- [ ] Charts resize gracefully at all breakpoints

---

#### F-14 · Onboarding Flow
**Priority:** P2

**Steps:**
1. Create account
2. Connect Gmail (OAuth flow — existing)
3. Select banks to scan
4. Set sync frequency
5. (Optional) Set first budget
6. Run first sync — see first transactions

**Acceptance Criteria:**
- [ ] Step-by-step wizard with progress indicator
- [ ] Each step can be skipped and completed later
- [ ] Demo/sample data mode — explore with 3 months of fake data before connecting Gmail
- [ ] Completion % shown on dashboard until setup is 100% done

---

## 5. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Dashboard load time | < 1.5s for 12 months of data |
| API response time | < 300ms for analytics endpoints |
| Mobile responsiveness | Fully functional on screens ≥ 375px |
| Sync reliability | < 0.1% duplicate transactions |
| Multi-user isolation | Each user sees only their own data |
| Data privacy | All data stays local; no third-party analytics |
| Currency | INR (₹) only — single currency for v2.0 |
| Concurrent users | Single-worker SQLite safe up to ~10 users; document constraint |

---

## 6. Delivery Phases & Sequence

```
Phases 1–2: Done (auth, manual transactions, Gmail OAuth, HDFC parsing)

Phase 3 — Multi-Bank Parsers
  F-02  Multi-bank parser framework (ICICI, SBI, Axis, IDFC, Kotak, Flash)
  Bug:  HDFC date fallback fix
  Bug:  parse_failed / unmatched conflation fix

Phase 4 — Automated Sync (moved up)
  F-01  Automated email sync (APScheduler cron job)
  Bug:  Gmail token refresh persistence
  Bug:  email_retention_days setting respected
  Bug:  EmailMetadata cleanup job

Phase 5 — Data Quality
  F-03  Sub-categories & smart auto-classification
  F-04  Granular payment method filtering (add payment_source column)
  F-05  Enhanced filtering & transaction table
  F-05a Merchant analytics & breakdown
  F-06  Improved manual entry + CSV upload

Phase 6 — Analytics & Trends
  F-07  Flexible time-comparison trend view
  F-08  Budget setting per category
  F-09  Spending goal tracking

Phase 7 — Pattern Detection & Insights
  F-10  Anomaly detection
  F-11  Recurring transaction detection
  F-12  Rule-based insight feed

Phase 8 — Polish & Publishing
  F-13  Responsive dashboard overhaul
  F-14  Onboarding flow

Phase 9 — Security Hardening
  - JWT → HttpOnly cookie migration
  - TOTP brute-force protection (per-user attempt counter)
  - Secret key enforcement at startup
  - Logout invalidation / token blacklist
  - python-jose → PyJWT migration

Phase 10 — VPS Deployment
  - Alembic initial migration + migration workflow
  - nginx + Let's Encrypt TLS
  - systemd service file
  - FRONTEND_URL env var (replace hardcoded localhost in OAuth redirect)
  - DEBUG=False enforcement at startup
  - Single-worker SQLite constraint documented
```

---

## 7. Technical Architecture Notes

### Stack (Actual)

| Layer | Technology | Notes |
|---|---|---|
| Backend framework | FastAPI 0.115 + Uvicorn | Python 3.14 only on dev machine |
| ORM | SQLAlchemy 2.0 (sync) | SQLite with WAL mode |
| Migrations | Alembic 1.14 | Installed, **no migration files yet** — must generate before any column additions |
| Auth | bcrypt 4.2.1 + python-jose 3.3.0 + pyotp 2.9.0 | Direct bcrypt (no passlib) |
| Encryption | cryptography 44 (Fernet) | Singleton `CryptoService`; key at `data/credentials/master.key` |
| Gmail | google-api-python-client 2.155 + google-auth-oauthlib 1.2 | OAuth2, gmail.readonly scope |
| Scheduling | APScheduler (to add in Phase 4) | Verify Python 3.14 wheel before adding |
| Frontend | React 18 + Vite 6 + Tailwind 3 + Recharts 2 | Vite proxies `/api` → port 8000 |
| Forms | react-hook-form + zod | Already installed |

### Migration Strategy

**Current approach:** `Base.metadata.create_all()` at startup — safe for initial creation, silently ignores new columns.

**Required before any new column additions (Phase 3 or earlier):**
```bash
cd backend
source venv/Scripts/activate
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

Then switch `main.py` startup to use alembic instead of `create_all`. All new tables and columns in this PRD must be added via Alembic migration files.

### Python 3.14 Compatibility Constraints

| Package | Status | Notes |
|---|---|---|
| pydantic | ✅ Use `>=2.12.5` | pydantic-core has cp314 wheel from 2.12.5+ |
| pandas | ⚠️ Blocked on Windows dev | Use Linux VPS target — pre-built wheel available |
| openpyxl | ⚠️ Deferred | Excel upload; CSV-only works with stdlib `csv` |
| APScheduler | 🔲 Verify | Check `apscheduler>=3.10` for cp314 wheel before Phase 4 |

### Existing Parser Architecture

```
backend/app/parsers/
  base_parser.py        ← BaseEmailParser (ABC) + ParsedTransaction dataclass
  categorizer.py        ← keyword → category mapping (extend with DB rules in Phase 5)
  hdfc_parser.py        ← HDFCParser (UPI + Credit Card) ✅
  parser_factory.py     ← PARSERS list + parse_email() convenience function
  # Add in Phase 3:
  icici_parser.py
  sbi_parser.py
  axis_parser.py
  idfc_parser.py
  kotak_parser.py
  flash_parser.py
```

Adding a new bank: create `{bank}_parser.py` inheriting `BaseEmailParser` → add instance to `PARSERS` list in `parser_factory.py`. No other changes needed.

### Transactions Table — Column Additions (Phase 5)

```sql
-- Via Alembic migration
ALTER TABLE transactions ADD COLUMN payment_source TEXT;
-- payment_method already exists: Credit Card | UPI | Cash | Debit Card | Net Banking | Others
-- payment_source stores specific instrument: "HDFC Regalia ••4521", "Google Pay UPI", null for Cash
```

### New DB Tables Required (Phases 4–7, all via Alembic)

| Table | Phase | Purpose |
|---|---|---|
| `sync_log` | 4 | Automated sync run history |
| `sync_config` | 4 | Per-user sync schedule |
| `category_rules` | 5 | User-editable keyword → category mapping |
| `budgets` | 6 | Monthly spending limits per category |
| `anomalies` | 7 | Flagged unusual transactions |
| `insights` | 7 | Cached rule-based insights |
| `recurring_patterns` | 7 | Detected subscription patterns |

### Frontend Component Tree (Target State)

```
src/
  components/
    layout/
      Navbar.jsx              (responsive — sidebar desktop, bottom bar mobile)
      SyncStatusBadge.jsx     (F-01 — "Last synced Xh ago · Sync Now")
    analytics/
      TrendChart.jsx          (F-07 — granularity toggle, uses existing Recharts)
      BudgetOverview.jsx      (F-08)
      MerchantBreakdown.jsx   (F-05a)
      InsightsFeed.jsx        (F-12 — LLM-ready interface)
      AnomalyBanner.jsx       (F-10)
      RecurringList.jsx       (F-11)
    filters/
      GranularityToggle.jsx   (F-07)
      PaymentSourceFilter.jsx (F-04)
      MerchantFilter.jsx      (F-05a — autocomplete multi-select)
      CategoryFilter.jsx      (F-03)
      DateRangePresets.jsx    (F-05)
      AmountRangeFilter.jsx   (F-05)
    transactions/
      TransactionTable.jsx    (F-05 — responsive card view on mobile)
      AddTransactionModal.jsx (F-06)
      CategoryBadge.jsx       (F-03)
    settings/
      SyncScheduleConfig.jsx  (F-01)
      BankParserConfig.jsx    (F-02)
      CategoryRulesEditor.jsx (F-03)
      BudgetSetup.jsx         (F-08)
    onboarding/
      OnboardingWizard.jsx    (F-14)
  pages/
    TransactionsPage.jsx      (exists — extend)
    AnalyticsPage.jsx         (exists — extend with new charts)
    SettingsPage.jsx          (new)
```

---

## 8. Open Questions (Resolved)

| Question | Decision |
|---|---|
| LLM for insights? | Deferred — v2.0 uses rule-based insights only. DB schema and UI designed to be LLM-compatible. |
| Push notifications? | Out of scope for v2.0. In-app alerts only. |
| Multi-currency? | INR (₹) only for v2.0. |
| Which banks? | HDFC (done) + ICICI, SBI, Axis, IDFC First, Kotak. Flash.co to verify. |
| Shared households? | Out of scope for v2.0. |
| Multi-user SaaS? | Long-term goal. Design for it (user isolation already enforced). Build billing/auth infra only after traction. |
| SQLite vs PostgreSQL? | SQLite for now — document single-worker constraint. Migrate to PostgreSQL if scaling beyond ~10 concurrent users. |
| pandas on Python 3.14? | CSV import without pandas (stdlib `csv`). Excel deferred or VPS-only. |
| payment_type vs payment_method? | Use existing `payment_method` column for type. Add new `payment_source` column for specific instrument. |

---

## 9. Success Metrics

| Metric | Target |
|---|---|
| "Others" category share | Reduced from ~40% → < 15% |
| Sync reliability | < 0.1% duplicate transactions per sync run |
| Budget visibility | 100% of categories with budgets have clear progress indicators |
| Anomaly precision | < 20% false-positive rate |
| Insight relevance | User finds ≥ 1 rule-based insight actionable per week |
| Mobile experience | Core flows completable on mobile without horizontal scrolling |

---

*This document is a living spec. Update it as features are scoped, built, and shipped.*
*Stored at: `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md`*
