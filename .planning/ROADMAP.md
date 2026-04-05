# Roadmap: Expense Tracker

**Created:** 2026-04-05
**Milestone:** v2.0 — Financial Intelligence Dashboard

---

## Milestone Goal

Transform the expense tracker from a passive Gmail-sync viewer into an active financial intelligence tool: automatic syncing from all major Indian banks, deep analytics with trend views and budgets, pattern detection, and mobile-responsive UX — publishable for other self-hosters.

---

## Phases

### Phase 1 — Auth + Manual Transactions
**Status:** ✅ Complete
**Goal:** Working authentication with TOTP 2FA and manual transaction entry.

Delivered:
- JWT + TOTP 2FA (bcrypt, Fernet-encrypted secrets)
- Manual transaction CRUD
- Category + payment method breakdown charts
- Date range filtering

---

### Phase 2 — Gmail OAuth + HDFC Parsing
**Status:** ✅ Complete
**Goal:** Connect Gmail, fetch HDFC transaction emails, parse and store transactions.

Delivered:
- Gmail OAuth2 flow (read-only, token encrypted at rest)
- HDFC UPI debit + Credit Card email parser
- Email deduplication by Gmail message ID
- Manual sync trigger UI

---

### Phase 3 — Multi-Bank Parsers
**Status:** 🔲 Not started
**Goal:** Support all major Indian banks in the email parser framework.

Scope:
- ICICI Bank parser (credit card + iMobile alerts)
- SBI parser (credit card + YONO alerts)
- All parsers extract `payment_source` (card/account identifier)
- Fix: HDFC date fallback → use `email["received_at"]` not `date.today()`
- Fix: separate `parse_failed` vs `unmatched` counters in sync summary
- **Prerequisite:** Generate initial Alembic migration before this phase

Out of scope (deferred to later):
- Axis Bank parser
- IDFC First Bank parser
- Kotak Mahindra parser
- Flash.co parser

Requirements: PARSE-03–04, PARSE-09, INFRA-01–02, INFRA-05

Canonical refs:
- `backend/app/parsers/base_parser.py` — BaseEmailParser interface
- `backend/app/parsers/hdfc_parser.py` — reference implementation
- `backend/app/parsers/parser_factory.py` — PARSERS list to extend
- `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md` §F-02

---

### Phase 4 — Automated Email Sync
**Status:** 🔲 Not started
**Goal:** Replace manual sync button with a scheduled background job.

Scope:
- APScheduler cron job (default: daily 02:00, configurable)
- Sync status badge in nav header: "Last synced: Xh ago · Sync Now"
- Sync history log in Settings
- User-configurable schedule (hourly / 6h / daily / custom cron)
- In-app alert on sync failure
- New DB tables: `sync_log`, `sync_config` (via Alembic)
- Fix: persist refreshed Gmail OAuth tokens back to DB
- Fix: use `settings.email_retention_days` (not hardcoded 30)
- Fix: background cleanup job for expired `EmailMetadata` rows
- New API: GET/POST /api/sync/status, /api/sync/trigger, /api/sync/logs, /api/settings/sync

Requirements: GMAIL-05–10, INFRA-03–04

Canonical refs:
- `backend/app/services/gmail_service.py` — token refresh location
- `backend/app/services/email_sync_service.py` — sync pipeline
- `backend/app/main.py` — where scheduler attaches
- `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md` §F-01

---

### Phase 5 — Data Quality: Categories, Payment Methods, Filtering
**Status:** 🔲 Not started
**Goal:** Reduce "Others" category, add per-card filtering, and make the transaction table a first-class feature.

Scope:
- Extended category taxonomy (add Subscriptions, Utilities, Travel)
- DB-backed category rules (keyword → category, user-editable, 4 match types)
- Unclassified state separate from Others
- `payment_source` column (Alembic migration, nullable)
- Multi-select payment source filter on dashboard + transaction table
- Enhanced transaction table: multi-select filters, amount range, quick date presets, sort
- CSV export of filtered view
- Merchant autocomplete filter
- Merchant analytics: breakdown table + payment split + top 10 on dashboard
- Improved manual entry: FAB, searchable category dropdown, cash support
- CSV upload (stdlib `csv`, no pandas)
- Category rules editor in Settings
- New API endpoints: /api/categories/rules, /api/payment-sources, /api/merchants, /api/analytics/merchants

Requirements: TXN-05–13, CAT-03–07, PAY-02–05, ANA-07–09

Canonical refs:
- `backend/app/models/transaction.py` — CATEGORIES, PAYMENT_METHODS lists
- `backend/app/parsers/categorizer.py` — existing keyword map to extend
- `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md` §F-03, F-04, F-05, F-05a, F-06

---

### Phase 6 — Analytics & Trend Views
**Status:** 🔲 Not started
**Goal:** Turn transaction data into a story across time with trend charts, budgets, and goal tracking.

Scope:
- Trend chart with granularity toggle (Daily / Weekly / Monthly / Annual)
- Category overlay toggle on trend chart
- Drill-down: clicking bar filters transaction table to that period
- Period comparison callout ("X% more/less vs last period")
- Budget setup: monthly limit per category, progress bars (green/amber/orange/red)
- Summary card: "X of Y budgets on track this month"
- Budgets auto-reset monthly
- Optional monthly savings goal with burn-rate projection
- Historical goal win/loss per month
- New DB table: `budgets` (Alembic)
- New API: /api/analytics/trends, /api/budgets, /api/analytics/summary

Requirements: ANA-03–06, BUDGET-01–04, GOAL-01–03

Canonical refs:
- `frontend/src/pages/AnalyticsPage.jsx` — existing charts to extend
- `backend/app/services/transaction_service.py` — summary aggregation to extend
- `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md` §F-07, F-08, F-09

---

### Phase 7 — Pattern Detection & Insights
**Status:** 🔲 Not started
**Goal:** Surface things the user would never notice manually — anomalies, subscriptions, and spending patterns.

Scope:
- Anomaly detection (4 rules: 2× median, 50% above period avg, new merchant >₹2000, duplicate charge)
- Alerts badge in header with unreviewed count
- Dismiss or mark-for-investigation per anomaly
- Recurring transaction detection (2+ months, ±10% amount, ±5 days)
- Subscriptions list with monthly total
- Alert if known recurring charge missing this month
- Rule-based insights feed: up to 5 insights, computed daily, dismissible (7-day suppression)
- Insights cached in DB; UI designed for LLM layer later
- New DB tables: `anomalies`, `recurring_patterns`, `insights` (Alembic)
- New API: /api/anomalies, /api/recurring, /api/insights

Requirements: INS-01–08

Canonical refs:
- `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md` §F-10, F-11, F-12

---

### Phase 8 — Polish & Publishing Readiness
**Status:** 🔲 Not started
**Goal:** Make the app fully responsive, polished, and usable by a general audience.

Scope:
- Full mobile responsive layout (≥375px, no horizontal scroll)
- Bottom nav on mobile (Dashboard / Transactions / Budgets / Settings)
- Side nav on desktop
- Floating "+ Add Transaction" FAB on mobile
- Dark mode toggle (respects system preference)
- Touch targets ≥44×44px
- Charts horizontally scrollable on mobile (trend chart)
- Transaction table → card list on mobile
- Onboarding wizard: 6 steps (account → Gmail → banks → sync → budget → first sync)
- Demo/sample data mode
- Settings page consolidation (sync, banks, categories, budgets)

Requirements: UX-01–08

Canonical refs:
- `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md` §F-13, F-14

---

### Phase 9 — Security Hardening
**Status:** 🔲 Not started
**Goal:** Close known security gaps before public exposure.

Scope:
- Migrate JWT from localStorage to HttpOnly cookie
- Logout invalidation: token blacklist table with TTL
- TOTP verify: per-user attempt counter, lockout after 5 failures
- SECRET_KEY: enforce non-default, min 32 chars at startup when DEBUG=False
- Migrate `python-jose` → `PyJWT` (active maintenance)
- Fix: `totp/setup` should not overwrite existing pending secret on repeat calls

Requirements: AUTH-04–07

Canonical refs:
- `backend/app/api/routes/auth.py` — TOTP verify, login routes
- `backend/app/config.py` — SECRET_KEY validation
- `frontend/src/context/AuthContext.jsx` — localStorage token storage
- `frontend/src/services/api.js` — axios JWT interceptor

---

### Phase 10 — VPS Deployment
**Status:** 🔲 Not started
**Goal:** Production-ready self-hosted deployment on a Linux VPS.

Scope:
- Generate initial Alembic migration + switch startup to `alembic upgrade head`
- nginx reverse proxy config with Let's Encrypt TLS (certbot)
- systemd service file for uvicorn (no --reload, restart-on-crash)
- `FRONTEND_URL` env var replaces hardcoded `localhost` in OAuth redirect
- `DEBUG=False` startup assertion
- Document single-worker SQLite constraint
- `.env.production.example` with all required vars
- Deployment README with step-by-step setup guide

Requirements: DEPLOY-01–05, INFRA-01 (if not done in Phase 3)

Canonical refs:
- `backend/app/api/routes/gmail.py:76` — hardcoded localhost redirect
- `backend/app/config.py` — settings that need production values
- `C:\Users\rahul\projects\expense-tracker\.planning\codebase\CONCERNS.md` — full concern list

---

## Phase Summary

| Phase | Name | Status | Key Deliverable |
|-------|------|--------|-----------------|
| 1 | Auth + Manual Transactions | ✅ Complete | 2FA auth, manual CRUD |
| 2 | Gmail OAuth + HDFC Parsing | ✅ Complete | Gmail sync, HDFC parser |
| 3 | Multi-Bank Parsers | 🔲 Not started | ICICI, SBI, Axis, IDFC, Kotak, Flash |
| 4 | Automated Email Sync | 🔲 Not started | APScheduler cron, sync settings |
| 5 | Data Quality | 🔲 Not started | Categories, payment source, filtering, CSV |
| 6 | Analytics & Trends | 🔲 Not started | Trend charts, budgets, goals |
| 7 | Pattern Detection | 🔲 Not started | Anomalies, recurring, insights feed |
| 8 | Polish & Publishing | 🔲 Not started | Mobile layout, onboarding |
| 9 | Security Hardening | 🔲 Not started | HttpOnly cookies, rate limits |
| 10 | VPS Deployment | 🔲 Not started | nginx, TLS, systemd, Alembic |

---
*Roadmap created: 2026-04-05*
*PRD reference: `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md`*
