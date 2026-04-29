# Requirements: Expense Tracker

**Defined:** 2026-04-05
**Core Value:** Automatically pull every bank transaction from Gmail and show exactly where your money is going — no manual entry, no spreadsheets.

---

## v1 Requirements (Active Roadmap)

### Authentication & Security

- [x] **AUTH-01**: User can log in with username + password (bcrypt hashed)
- [x] **AUTH-02**: Login requires TOTP 2FA (TOTP secret encrypted at rest)
- [x] **AUTH-03**: JWT access tokens issued on successful 2FA verify (30 min TTL)
- [ ] **AUTH-04**: JWT stored in HttpOnly cookie (not localStorage) — Phase 9
- [ ] **AUTH-05**: Logout invalidates server-side token (blacklist or session check) — Phase 9
- [ ] **AUTH-06**: TOTP verify endpoint rate-limited per user (max 5 attempts) — Phase 9
- [ ] **AUTH-07**: App refuses to start with default SECRET_KEY in production — Phase 9

### Transaction Management

- [x] **TXN-01**: User can manually add a transaction (amount, merchant, date, category, payment method, notes)
- [x] **TXN-02**: User can edit and delete manually-entered transactions
- [x] **TXN-03**: Transactions are paginated (50 per page)
- [x] **TXN-04**: Transactions filterable by date range and category
- [x] **TXN-05**: Transaction table supports multi-select filters: category, payment source, merchant, amount range — Phase 5
- [x] **TXN-06**: Quick date presets: Today / This Week / This Month / Last Month / Last 3M / This Year — Phase 5
- [x] **TXN-07**: Filtered view shows total count and sum in table header — Phase 5
- [x] **TXN-08**: Filtered view exportable to CSV — Phase 5
- [x] **TXN-09**: Transaction table collapses to card list view on mobile — Phase 8
- [x] **TXN-10**: Cash transactions supported (payment_method=Cash, payment_source=null) — Phase 5
- [x] **TXN-11**: Category re-assignable inline; option to apply to all future transactions from same merchant — Phase 5
- [x] **TXN-12**: Bulk category re-assignment (multi-select rows) — Phase 5
- [x] **TXN-13**: CSV file upload for bulk import — Phase 5

### Gmail Integration

- [x] **GMAIL-01**: User can connect Gmail via OAuth2 (read-only scope)
- [x] **GMAIL-02**: OAuth token encrypted at rest with Fernet
- [x] **GMAIL-03**: Manual email sync fetches and parses transaction emails
- [x] **GMAIL-04**: Duplicate emails skipped by Gmail message ID dedup
- [x] **GMAIL-05**: Refreshed OAuth access tokens persisted back to DB — Phase 4 ✅ Plan 04-01
- [x] **GMAIL-06**: Automated sync on configurable cron schedule (default: daily 02:00) — Phase 4 ✅ Plan 04-02
- [ ] **GMAIL-07**: Sync status visible in header: "Last synced: Xh ago · Sync Now" — Phase 4
- [x] **GMAIL-08**: Sync failures logged and do not crash scheduler (GMAIL-08) — Phase 4 ✅ Plan 04-02
- [ ] **GMAIL-09**: Sync history log accessible in Settings — Phase 4 (deferred per D-15)
- [x] **GMAIL-10**: Sync schedule user-configurable via PUT /api/gmail/settings — Phase 4 ✅ Plan 04-02

### Bank Parsers

- [x] **PARSE-01**: HDFC UPI debit alerts parsed (amount, merchant, VPA, date)
- [x] **PARSE-02**: HDFC Credit Card alerts parsed (amount, merchant, card ending, date)
- [x] **PARSE-03**: ICICI Bank alerts parsed — Phase 3
- [x] **PARSE-04**: SBI alerts parsed — Phase 3
- [x] **PARSE-09**: All parsers extract payment_source (specific card/account identifier) — Phase 3
- **PARSE-05**: Axis Bank alerts parsed — deferred (out of scope for Phase 3)
- **PARSE-06**: IDFC First Bank alerts parsed — deferred (out of scope for Phase 3)
- **PARSE-07**: Kotak Mahindra alerts parsed — deferred (out of scope for Phase 3)
- **PARSE-08**: Flash.co alerts parsed — deferred (out of scope for Phase 3)

### Categories & Classification

- [x] **CAT-01**: Auto-categorisation on import via keyword matching
- [x] **CAT-02**: Categories: Rent, Groceries, Shopping, Electricity, Food & Dining, Transport, Entertainment, Healthcare, Others
- [x] **CAT-03**: Extended taxonomy: Subscriptions, Utilities, Travel added — Phase 5
- [x] **CAT-04**: DB-backed category rules (keyword → category, user-editable) — Phase 5
- [x] **CAT-05**: Match types: exact, contains, starts_with, regex — Phase 5
- [x] **CAT-06**: Unclassified transactions flagged separately (not lumped into Others) — Phase 5
- [x] **CAT-07**: Category rules editor in Settings — Phase 5

### Payment Methods

- [x] **PAY-01**: Payment methods: Credit Card, UPI, Cash, Debit Card, Net Banking, Others
- [x] **PAY-02**: payment_source column added (specific card/account, nullable for Cash) — Phase 5
- [x] **PAY-03**: Multi-select filter by payment source on dashboard and transaction table — Phase 5
- [ ] **PAY-04**: Analytics charts respond to payment source filter — Phase 5
- [x] **PAY-05**: GET /api/payment-sources returns distinct sources for current user — Phase 5

### Analytics

- [x] **ANA-01**: Category breakdown (pie chart) for selected date range
- [x] **ANA-02**: Payment method breakdown (bar chart) for selected date range
- [x] **ANA-03**: Trend chart with granularity toggle: Daily / Weekly / Monthly / Annual — Phase 6
- [x] **ANA-04**: Category overlay toggle on trend chart — Phase 6
- [x] **ANA-05**: Drill-down: clicking trend bar filters transaction table — Phase 6
- [x] **ANA-06**: Period comparison callout: "X% more/less vs last period" — Phase 6
- [x] **ANA-07**: Merchant breakdown table (total, count, avg, % of total, payment split) — Phase 5
- [ ] **ANA-08**: Top 10 merchants by spend on main dashboard — Phase 5
- [x] **ANA-09**: Merchant autocomplete for transaction filter — Phase 5

### Budgets & Goals

- [ ] **BUDGET-01**: User sets monthly spending limit per category — Phase 6
- [ ] **BUDGET-02**: Dashboard shows progress bar per budget (green/amber/orange/red) — Phase 6
- [ ] **BUDGET-03**: Summary card: "X of Y budgets on track this month" — Phase 6
- [ ] **BUDGET-04**: Budgets auto-reset at start of each calendar month — Phase 6
- [ ] **GOAL-01**: User sets optional monthly savings target — Phase 6
- [x] **GOAL-02**: Dashboard shows projected month-end spend based on burn rate — Phase 6
- [ ] **GOAL-03**: Historical goal achievement shown as win/loss per month — Phase 6

### Insights & Patterns

- [ ] **INS-01**: Anomaly detection runs after each sync (rule-based, 4 rules) — Phase 7
- [ ] **INS-02**: Alerts badge shows unreviewed anomaly count — Phase 7
- [ ] **INS-03**: User can dismiss or mark anomaly for investigation — Phase 7
- [ ] **INS-04**: Recurring transaction detection (same merchant, similar amount, 2+ months) — Phase 7
- [ ] **INS-05**: Subscriptions list with estimated monthly total — Phase 7
- [ ] **INS-06**: Alert if known recurring charge missing for current month — Phase 7
- [ ] **INS-07**: Rule-based insights feed (up to 5, computed daily, dismissible) — Phase 7
- [ ] **INS-08**: Insights cached in DB — not recomputed on every page load — Phase 7

### UX & Polish

- [ ] **UX-01**: Fully responsive layout — no horizontal scroll on mobile (≥375px) — Phase 8
- [ ] **UX-02**: Bottom navigation on mobile (Dashboard / Transactions / Budgets / Settings) — Phase 8
- [ ] **UX-03**: Side navigation on desktop — Phase 8
- [ ] **UX-04**: Floating "+ Add Transaction" FAB on mobile — Phase 8 (Phase 5 for functionality)
- [ ] **UX-05**: Dark mode toggle (system preference by default) — Phase 8
- [ ] **UX-06**: Touch targets minimum 44×44px on mobile — Phase 8
- [ ] **UX-07**: Onboarding wizard (6-step: account → Gmail → banks → sync → budget → first sync) — Phase 8
- [ ] **UX-08**: Demo / sample data mode for exploring before Gmail connect — Phase 8

### Infrastructure & Data Quality

- [ ] **INFRA-01**: Alembic initial migration generated; startup uses `alembic upgrade head` — Phase 3
- [ ] **INFRA-02**: All new schema changes delivered via Alembic migration files — Phase 3+
- [x] **INFRA-03**: email_retention_days setting respected (not hardcoded 30 days) — Phase 4 ✅ Plan 04-01
- [x] **INFRA-04**: Expired EmailMetadata rows cleaned up by background job (daily 03:00 cron) — Phase 4 ✅ Plan 04-02
- [x] **INFRA-05**: parse_failed / unmatched counters separated in sync summary — Phase 3

### Deployment

- [ ] **DEPLOY-01**: nginx reverse proxy with Let's Encrypt TLS — Phase 10
- [ ] **DEPLOY-02**: systemd service file for uvicorn (no --reload, restart-on-crash) — Phase 10
- [ ] **DEPLOY-03**: FRONTEND_URL env var replaces hardcoded localhost in OAuth redirect — Phase 10
- [ ] **DEPLOY-04**: DEBUG=False enforced at startup in production — Phase 10
- [ ] **DEPLOY-05**: Single-worker SQLite constraint documented — Phase 10

---

## v2 Requirements (Future)

### AI / LLM

- **AI-01**: LLM-powered insight generation (schema and UI already designed for this)
- **AI-02**: Natural language transaction search
- **AI-03**: AI-assisted budget recommendations

### Multi-user SaaS

- **SAAS-01**: Public signup flow
- **SAAS-02**: Billing / subscription management
- **SAAS-03**: Admin dashboard for user management
- **SAAS-04**: PostgreSQL migration for concurrent write safety

### Notifications

- **NOTF-01**: Email alerts for anomalies
- **NOTF-02**: Weekly spending summary email
- **NOTF-03**: Budget overage push notification

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-currency | INR only for v2; adds complexity without clear user need yet |
| Shared household accounts | Out of scope for v2; design doesn't preclude it later |
| Real-time sync (websockets) | Cron-based is sufficient; real-time adds infra complexity |
| Mobile native app | Web-first; responsive design covers mobile adequately |
| Income / credit transaction tracking | Only debit/spend alerts parsed; income tracking deferred |
| OAuth login (Google/GitHub) | Email+TOTP sufficient for self-hosted; add if SaaS traction warrants |
| Push notifications | In-app alerts only for v2 |
| Excel upload on dev machine | openpyxl blocked by Python 3.14 build tools; VPS-only or deferred |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01–03 | Phase 1 | ✓ Complete |
| TXN-01–04 | Phase 1 | ✓ Complete |
| GMAIL-01–04 | Phase 2 | ✓ Complete |
| PARSE-01–02 | Phase 2 | ✓ Complete |
| CAT-01–02 | Phase 2 | ✓ Complete |
| PAY-01 | Phase 1 | ✓ Complete |
| ANA-01–02 | Phase 2 | ✓ Complete |
| PARSE-03–09, INFRA-01–02, INFRA-05 | Phase 3 | Pending |
| GMAIL-05–10, INFRA-03–04 | Phase 4 | Pending |
| TXN-05–13, CAT-03–07, PAY-02–05, ANA-07–09 | Phase 5 | Pending |
| ANA-03–06, BUDGET-01–04, GOAL-01–03 | Phase 6 | Pending |
| INS-01–08 | Phase 7 | Pending |
| UX-01–08, AUTH-04–07 (partial) | Phase 8 | Pending |
| AUTH-04–07 | Phase 9 | Pending |
| DEPLOY-01–05 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 68 total
- Mapped to phases: 68
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after initial GSD project initialization*
