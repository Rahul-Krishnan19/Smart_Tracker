# Roadmap: Expense Tracker

## Overview

Transform the expense tracker from a manual Gmail-sync viewer into an active financial intelligence tool. Phases progress from data pipeline (parsers, auto-sync) through data quality, analytics, pattern detection, polish, security, and VPS deployment.

## Phases

- [x] **Phase 1: Auth + Manual Transactions** - JWT + TOTP 2FA auth and manual transaction CRUD
- [x] **Phase 2: Gmail OAuth + HDFC Parsing** - Gmail OAuth2 integration and HDFC email parser
- [x] **Phase 3: Multi-Bank Parsers** - ICICI and SBI bank email parsers + Alembic migration setup (completed 2026-04-05)
- [ ] **Phase 4: Automated Email Sync** - APScheduler cron sync with settings and sync history
- [ ] **Phase 5: Data Quality** - Sub-categories, payment source, enhanced filtering, CSV upload
- [ ] **Phase 6: Analytics & Trends** - Trend charts, budgets, and spending goal tracking
- [ ] **Phase 7: Pattern Detection & Insights** - Anomaly detection, recurring charges, insights feed
- [ ] **Phase 8: Polish & Publishing** - Mobile-responsive layout and onboarding wizard
- [ ] **Phase 9: Security Hardening** - HttpOnly cookies, token blacklist, TOTP rate limiting
- [ ] **Phase 10: VPS Deployment** - nginx, TLS, systemd, Alembic production migrations

## Phase Details

### Phase 1: Auth + Manual Transactions
**Goal**: Working authentication with TOTP 2FA and manual transaction entry
**Depends on**: Nothing
**Requirements**: AUTH-01, AUTH-02, AUTH-03, TXN-01, TXN-02, TXN-03, TXN-04, PAY-01, CAT-01, CAT-02, ANA-01, ANA-02
**Status**: Complete
**Success Criteria** (what must be TRUE):
  1. User can register and log in with password + TOTP code
  2. User can add, edit, and delete transactions manually
  3. Category and payment method breakdown charts display for a date range

Plans:
- [x] 01-01: Auth service, JWT, TOTP enrollment and verification
- [x] 01-02: Transaction CRUD API and frontend transaction table
- [x] 01-03: Analytics page with category and payment method charts

### Phase 2: Gmail OAuth + HDFC Parsing
**Goal**: Connect Gmail, fetch HDFC transaction emails, parse and store transactions
**Depends on**: Phase 1
**Requirements**: GMAIL-01, GMAIL-02, GMAIL-03, GMAIL-04, PARSE-01, PARSE-02
**Status**: Complete
**Success Criteria** (what must be TRUE):
  1. User can connect Gmail via OAuth2 and token is stored encrypted
  2. Manual sync fetches HDFC UPI and Credit Card emails and creates transactions
  3. Re-syncing the same emails does not create duplicate transactions

Plans:
- [x] 02-01: Gmail OAuth2 flow, token encryption, auth-url and exchange endpoints
- [x] 02-02: HDFC email parser (UPI + Credit Card), email sync service, dedup logic
- [x] 02-03: Frontend Gmail connect/sync/disconnect UI

### Phase 3: Multi-Bank Parsers
**Goal**: Support ICICI and SBI bank emails in the parser framework, fix known data bugs, and establish Alembic as the migration tool
**Depends on**: Phase 2
**Requirements**: PARSE-03, PARSE-04, PARSE-09, INFRA-01, INFRA-02, INFRA-05
**Success Criteria** (what must be TRUE):
  1. ICICI Bank transaction emails are parsed and stored as transactions
  2. SBI transaction emails are parsed and stored as transactions
  3. All parsers populate payment_source (card/account identifier)
  4. Alembic initial migration generated; startup uses alembic upgrade head
  5. Sync summary correctly separates parse errors from unmatched emails
  6. HDFC transactions use email received_at date as fallback (not date.today())

**Plans:** 4/4 plans complete

Plans:
- [x] 03-01-PLAN.md -- Test infrastructure + Alembic migrations + payment_source schema
- [x] 03-02-PLAN.md -- Parser interface change + HDFC fixes + sync service refactor
- [x] 03-03-PLAN.md -- ICICI and SBI parsers + factory registration

### Phase 4: Automated Email Sync
**Goal**: Add APScheduler background sync with per-user configurable schedule, fix Gmail token refresh persistence, and clean up expired email metadata
**Depends on**: Phase 3
**Requirements**: GMAIL-05, GMAIL-06, GMAIL-07, GMAIL-08, GMAIL-10, INFRA-03, INFRA-04
**Note**: GMAIL-09 (sync history log) explicitly deferred
**Success Criteria** (what must be TRUE):
  1. Emails sync automatically on a schedule (default: daily) without user action
  2. "Last updated at" timestamp shows in IST next to Sync Emails button
  3. Sync failures surface as in-app alert (not silent)
  4. User can change sync frequency in Settings
  5. Refreshed Gmail OAuth tokens are persisted back to DB

**Plans:** 3 plans

Plans:
- [ ] 04-01-PLAN.md -- APScheduler install + schema migration + token refresh fix + INFRA-03
- [ ] 04-02-PLAN.md -- Scheduler module + lifespan + settings route + cleanup job
- [ ] 04-03-PLAN.md -- Frontend last-synced display + sync settings UI + verification

### Phase 5: Data Quality
**Goal**: Reduce "Others" category share, add per-card payment filtering, and make the transaction table a first-class feature with filtering, export, and CSV upload
**Depends on**: Phase 4
**Requirements**: TXN-05, TXN-06, TXN-07, TXN-08, TXN-09, TXN-10, TXN-11, TXN-12, TXN-13, CAT-03, CAT-04, CAT-05, CAT-06, CAT-07, PAY-02, PAY-03, PAY-04, PAY-05, ANA-07, ANA-08, ANA-09
**Success Criteria** (what must be TRUE):
  1. User can filter transactions by category, payment source, merchant, and amount range
  2. "Others" category reduced — uncategorised transactions shown separately
  3. User can edit category rules in Settings and re-classify transactions inline
  4. Merchant breakdown table shows top merchants with payment method split
  5. Filtered transaction view exportable to CSV
  6. CSV file upload imports transactions in bulk

**Plans:** 3/3 plans executed (Task 2 of plan 03 pending human verify)

Plans:
- [x] 05-01-PLAN.md -- CategoryRule model, _build_filter_query, payment-sources/merchant-breakdown/summary APIs
- [x] 05-02-PLAN.md -- FilterPanel, TransactionList, TransactionsPage wiring with payment_source + merchant filters
- [x] 05-03-PLAN.md -- AnalyticsPage: payment source filter dropdown + merchant breakdown table (top 10)

### Phase 6: Analytics & Trends
**Goal**: Turn transaction data into a time story — trend chart with granularity toggle, click-through to filtered transactions, and burn-rate projection with per-granularity spending limit
**Depends on**: Phase 5
**Requirements**: ANA-03, ANA-04, ANA-05, ANA-06, GOAL-02
**Note**: BUDGET-01–04 (per-category budgets) and GOAL-01, GOAL-03 (savings goals) deferred per CONTEXT.md D-10/D-11
**Success Criteria** (what must be TRUE):
  1. Trend chart shows spend over time with Daily/Weekly/Monthly/Annual toggle
  2. Clicking a trend data point navigates to /transactions pre-filtered to that period
  3. Period comparison badge shows "X% more/less vs last period"
  4. Burn-rate projection card shows projected month-end spend when viewing current period
  5. User can set a per-granularity spending limit; card shows progress and turns red when over

**Plans:** 3 plans

Plans:
- [ ] 06-01-PLAN.md -- TrendService (SQLite strftime grouping), analytics schemas, GET /api/analytics/trend, 13 pytest unit tests
- [ ] 06-02-PLAN.md -- SpendingLimit model + Alembic migration + GET/PUT/DELETE /api/analytics/spending-limit, 10 pytest tests
- [ ] 06-03-PLAN.md -- TrendChart (Recharts AreaChart), GranularityToggle, BurnRateCard, AnalyticsPage wiring, URL-param seeding for TransactionsPage

### Phase 7: Pattern Detection & Insights
**Goal**: Surface anomalies, recurring charges, and spending patterns automatically using rule-based detection
**Depends on**: Phase 6
**Requirements**: INS-01, INS-02, INS-03, INS-04, INS-05, INS-06, INS-07, INS-08
**Success Criteria** (what must be TRUE):
  1. Unusual transactions are flagged and shown in an alerts panel with dismiss/investigate actions
  2. Recurring charges are detected and shown as a subscriptions list with monthly total
  3. Rule-based insights feed shows up to 5 daily insights (dismissible)
  4. Insights are cached in DB — not recomputed on every page load

**Plans:** 3 plans

Plans:
- [ ] 07-01-PLAN.md -- TBD
- [ ] 07-02-PLAN.md -- TBD
- [ ] 07-03-PLAN.md -- TBD

### Phase 8: Polish & Publishing Readiness
**Goal**: Fully responsive mobile layout, dark mode, and a guided onboarding wizard for new users
**Depends on**: Phase 7
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07, UX-08
**Success Criteria** (what must be TRUE):
  1. Core flows (add transaction, view analytics, sync) completable on mobile without horizontal scroll
  2. Bottom nav on mobile, side nav on desktop
  3. Dark mode respects system preference and can be toggled
  4. New user onboarding wizard completes in 6 steps and surfaces first transactions

**Plans:** 3 plans

Plans:
- [ ] 08-01-PLAN.md -- TBD
- [ ] 08-02-PLAN.md -- TBD
- [ ] 08-03-PLAN.md -- TBD

### Phase 9: Security Hardening
**Goal**: Close known security gaps — JWT storage, token invalidation, TOTP rate limiting, and dependency hygiene
**Depends on**: Phase 8
**Requirements**: AUTH-04, AUTH-05, AUTH-06, AUTH-07
**Success Criteria** (what must be TRUE):
  1. JWT stored in HttpOnly cookie — not accessible via JavaScript
  2. Logout invalidates the token server-side
  3. TOTP verify endpoint locks out after 5 failed attempts per user
  4. App refuses to start with default SECRET_KEY in production

**Plans:** 3 plans

Plans:
- [ ] 09-01-PLAN.md -- TBD
- [ ] 09-02-PLAN.md -- TBD
- [ ] 09-03-PLAN.md -- TBD

### Phase 10: VPS Deployment
**Goal**: Production-ready self-hosted deployment on Linux VPS with nginx, TLS, systemd, and Alembic migrations
**Depends on**: Phase 9
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05
**Success Criteria** (what must be TRUE):
  1. App accessible over HTTPS via nginx + Let's Encrypt on a real domain
  2. Uvicorn managed by systemd with restart-on-crash
  3. Gmail OAuth works end-to-end on VPS (no localhost hardcoding)
  4. Schema changes deployable via `alembic upgrade head`

**Plans:** 3 plans

Plans:
- [ ] 10-01-PLAN.md -- TBD
- [ ] 10-02-PLAN.md -- TBD
- [ ] 10-03-PLAN.md -- TBD

## Progress

**Execution Order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auth + Manual Transactions | 3/3 | Complete | 2026-03 |
| 2. Gmail OAuth + HDFC Parsing | 3/3 | Complete | 2026-04 |
| 3. Multi-Bank Parsers | 3/3 | Complete    | 2026-04-05 |
| 4. Automated Email Sync | 0/3 | Planned | - |
| 5. Data Quality | 3/3 | In Progress (awaiting human-verify) | 2026-04-28 |
| 6. Analytics & Trends | 0/3 | Planned | - |
| 7. Pattern Detection & Insights | 0/TBD | Not started | - |
| 8. Polish & Publishing | 0/TBD | Not started | - |
| 9. Security Hardening | 0/TBD | Not started | - |
| 10. VPS Deployment | 0/TBD | Not started | - |
