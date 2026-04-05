# Expense Tracker

## What This Is

A self-hosted, privacy-first personal finance tool that automatically imports transactions from Gmail (major Indian banks) and provides actionable analytics. Built for a single power user first, then publishable as a small SaaS product for other self-hosters.

## Core Value

Automatically pull every bank transaction from Gmail and show exactly where your money is going — no manual entry, no spreadsheets.

## Requirements

### Validated

- ✓ JWT + TOTP 2FA authentication with bcrypt password hashing — Phase 1
- ✓ Manual transaction entry (CRUD) with category and payment method — Phase 1
- ✓ Gmail OAuth2 integration (read-only scope, token encrypted at rest) — Phase 2
- ✓ HDFC Bank email parsing — UPI debit + Credit Card alerts — Phase 2
- ✓ Email deduplication by Gmail message ID — Phase 2
- ✓ Category breakdown + payment method breakdown charts — Phase 2

### Active

- [ ] Multi-bank parser support (ICICI, SBI, Axis, IDFC, Kotak, Flash.co) — Phase 3
- [ ] Automated email sync via cron job (APScheduler) — Phase 4
- [ ] Sub-categories + DB-backed keyword classification rules — Phase 5
- [ ] Granular payment source filtering (per card/account) — Phase 5
- [ ] Enhanced transaction table with advanced filtering + CSV export — Phase 5
- [ ] Merchant analytics and breakdown — Phase 5
- [ ] CSV upload for manual import — Phase 5
- [ ] Time-series trend charts (daily/weekly/monthly/annual) — Phase 6
- [ ] Budget setting per category with visual progress — Phase 6
- [ ] Spending goal tracking with burn-rate projection — Phase 6
- [ ] Anomaly detection (rule-based) — Phase 7
- [ ] Recurring transaction detection — Phase 7
- [ ] Rule-based insights feed (LLM-compatible design) — Phase 7
- [ ] Fully responsive mobile layout + dark mode — Phase 8
- [ ] Onboarding wizard with demo data mode — Phase 8
- [ ] Security hardening (HttpOnly cookies, token blacklist, TOTP rate-limit) — Phase 9
- [ ] VPS deployment (nginx, TLS, systemd, Alembic migrations) — Phase 10

### Out of Scope

- LLM-powered insights — deferred post-v2; DB schema designed to support it later
- Push/email notifications — in-app alerts only for v2
- Multi-currency — INR (₹) only for v2
- Shared household accounts — out of scope for v2
- Real-time sync (websockets) — cron-based is sufficient
- Mobile native app — web-first, responsive design covers mobile
- Billing / monetisation infrastructure — build only after traction

## Context

- **Codebase state:** Phases 1–2 complete. Python 3.14 on Windows dev machine; Linux VPS is the deployment target.
- **Critical bug — Alembic:** Installed but no migration files exist. `Base.metadata.create_all()` is used at startup. Must generate initial migration before any new column is added in Phase 3+.
- **Critical bug — Gmail token refresh:** Refreshed access tokens are not persisted back to DB. Fix in Phase 4.
- **Python 3.14 constraints:** `pydantic>=2.12.5` required (cp314 wheel). `pandas` blocked on Windows dev — use VPS for CSV/Excel. APScheduler wheel must be verified before Phase 4.
- **Parser architecture:** `BaseEmailParser` ABC at `backend/app/parsers/base_parser.py`. Adding a bank = one new file + one line in `PARSERS` list.
- **Frontend:** React 18 + Vite 6 + Tailwind 3 + Recharts 2. All installed. Vite proxies `/api` → port 8000.
- **PRD:** Full product spec at `C:\Users\rahul\AppData\Roaming\Claude\plans\PRD-expense-tracker-v2.md`

## Constraints

- **Compatibility:** Python 3.14 only on dev machine — no packages requiring Rust/C compilation without a cp314 wheel
- **Database:** SQLite with WAL mode — single-writer; safe for ~10 concurrent users; document this limit; migrate to PostgreSQL if scaling
- **Auth:** Direct bcrypt (no passlib) — do not add passlib dependency
- **Encryption:** All secrets (TOTP, OAuth tokens) encrypted with Fernet before DB storage — maintain this invariant
- **Privacy:** All data stays local/self-hosted; no third-party analytics or telemetry
- **Currency:** INR (₹) only for v2.0

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite over PostgreSQL | Single-user personal tool; WAL mode handles read concurrency | — Pending (revisit if multi-user SaaS grows) |
| Direct bcrypt (no passlib) | passlib incompatible with bcrypt 5.0+ on Python 3.14 | ✓ Good |
| Fernet symmetric encryption for secrets | Simple, auditable, no external KMS needed for self-hosted | ✓ Good |
| PARSERS list over registry pattern | Simple, readable, sufficient for the number of banks | ✓ Good |
| Rule-based insights first, LLM later | Avoid LLM dependency for v2; design DB/UI to be LLM-compatible | — Pending |
| payment_method (existing) + payment_source (new) | payment_method column already exists; payment_source adds per-card granularity | — Pending |
| CSV-only import without pandas | stdlib `csv` works on Python 3.14; pandas deferred to VPS | — Pending |
| Phase order: parsers → auto-sync → data quality → analytics → insights | Fixes data pipeline before building analytics on top of it | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-03 after initial GSD project initialization*
