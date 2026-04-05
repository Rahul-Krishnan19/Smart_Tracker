# Codebase Structure

_Generated: 2026-03-29_

## Summary

The project root contains two independent applications (`backend/` and `frontend/`) plus shared runtime data (`data/`) and planning artifacts (`.planning/`). The backend is a Python/FastAPI package; the frontend is a Vite/React SPA. They share no code — all communication is over HTTP.

---

## Directory Layout

```
expense-tracker/
├── backend/                    # FastAPI application
│   ├── app/                    # Python package (all application code)
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app factory, middleware, router mounts
│   │   ├── config.py           # Pydantic Settings (reads .env)
│   │   ├── database.py         # SQLAlchemy engine, session factory, Base
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py         # /api/auth/* — register, login, TOTP, logout
│   │   │       ├── transactions.py # /api/transactions/* — CRUD + summary
│   │   │       └── gmail.py        # /api/gmail/* — OAuth2, sync, status
│   │   ├── models/
│   │   │   ├── user.py         # User ORM model (users table)
│   │   │   ├── transaction.py  # Transaction ORM model + CATEGORIES/PAYMENT_METHODS enums
│   │   │   ├── email_metadata.py # EmailMetadata ORM model (emails table)
│   │   │   └── session.py      # UserSession ORM model (sessions table)
│   │   ├── schemas/
│   │   │   ├── auth.py         # Pydantic: UserRegister, UserLogin, TOTPVerify,
│   │   │   │                   #   TOTPSetupResponse, LoginResponse, AuthResponse, UserOut
│   │   │   └── transaction.py  # Pydantic: TransactionCreate, TransactionUpdate,
│   │   │                       #   TransactionOut, TransactionListResponse, TransactionFilters
│   │   ├── services/
│   │   │   ├── auth_service.py       # Password, JWT, temp token, TOTP enrollment, sessions
│   │   │   ├── crypto_service.py     # Fernet singleton — encrypt/decrypt strings
│   │   │   ├── totp_service.py       # pyotp wrapper — generate, verify, QR code PNG
│   │   │   ├── gmail_service.py      # Google OAuth2 flow + Gmail API fetch + body extract
│   │   │   ├── email_sync_service.py # fetch→dedup→parse→save orchestrator
│   │   │   └── transaction_service.py # CRUD, filtered list, summary aggregation
│   │   ├── parsers/
│   │   │   ├── base_parser.py    # BaseEmailParser ABC + ParsedTransaction dataclass
│   │   │   ├── parser_factory.py # PARSERS list + parse_email() entry point
│   │   │   ├── hdfc_parser.py    # HDFCParser: UPI debit + credit card debit patterns
│   │   │   └── categorizer.py    # Keyword → category mapping; categorize() function
│   │   ├── middleware/
│   │   │   └── __init__.py      # (empty — security headers inline in main.py)
│   │   └── utils/
│   │       └── __init__.py      # (empty — reserved for helpers)
│   ├── alembic/                 # Alembic migration scaffolding (no migrations yet)
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/            # Empty — schema managed via create_all()
│   ├── scripts/
│   │   ├── create_admin.py      # One-time: create first user (run manually)
│   │   └── reset_password.py    # Utility: reset a user's password
│   ├── tests/
│   │   ├── fixtures/            # Empty — no test files yet
│   │   └── (no test files)
│   ├── venv/                    # Python 3.14 virtualenv (not committed)
│   ├── requirements.txt         # Python dependencies
│   ├── alembic.ini
│   ├── .env                     # Local config (not committed)
│   └── .env.example             # Template for required env vars
│
├── frontend/                    # React + Vite SPA
│   ├── src/
│   │   ├── main.jsx             # React entry point — renders <App /> into #root
│   │   ├── index.css            # Tailwind directives + global styles
│   │   ├── App.jsx              # BrowserRouter, AuthProvider, route definitions
│   │   ├── context/
│   │   │   └── AuthContext.jsx  # React context: user state, login(), logout(), isAuthenticated
│   │   ├── services/
│   │   │   └── api.js           # Axios instance (/api base), JWT interceptor, 401 redirect,
│   │   │                        #   authApi and transactionsApi named exports
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.jsx    # Multi-step login: credentials → totp_setup | totp_verify
│   │   │   │   ├── TOTPSetup.jsx    # QR display + code verify for first-time enrollment
│   │   │   │   └── ProtectedRoute.jsx # Redirects to /login if not authenticated
│   │   │   ├── transactions/
│   │   │   │   ├── TransactionList.jsx  # Paginated table; inline edit/delete per row
│   │   │   │   ├── TransactionForm.jsx  # Form for manual transaction creation
│   │   │   │   └── FilterPanel.jsx      # Date range, category, payment method, search filters
│   │   │   ├── gmail/
│   │   │   │   └── GmailSync.jsx    # Connect / Sync / Disconnect Gmail; shows sync results
│   │   │   └── analytics/
│   │   │       └── (empty — charts rendered directly in AnalyticsPage)
│   │   ├── pages/
│   │   │   ├── TransactionsPage.jsx # Summary cards + GmailSync + FilterPanel + TransactionList
│   │   │   ├── AnalyticsPage.jsx    # Date range picker + KPI cards + Recharts pie/bar + table
│   │   │   └── GmailCallbackPage.jsx # OAuth redirect landing; reads ?code, POSTs to /api/gmail/exchange
│   │   ├── hooks/               # Empty — no custom hooks yet
│   │   └── utils/               # Empty — reserved
│   ├── index.html               # Vite entry HTML
│   ├── vite.config.js           # Port 3000, proxy /api → localhost:8000
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   ├── package-lock.json
│   └── .env.example             # Frontend env template
│
├── data/                        # Runtime data (NOT committed to git)
│   ├── credentials/
│   │   └── master.key           # Fernet encryption key (auto-generated on first run)
│   ├── database/
│   │   ├── expense_tracker.db   # SQLite database file
│   │   ├── expense_tracker.db-shm
│   │   └── expense_tracker.db-wal
│   └── uploads/                 # Reserved for Phase 4 CSV/Excel uploads
│
├── .planning/
│   └── codebase/                # GSD mapping documents
├── docs/                        # Empty — documentation placeholder
├── .gitignore
└── README.md
```

---

## Key File Locations

**Backend entry point:**
- `backend/app/main.py` — FastAPI app object, CORS, rate limiter, security headers, router mounts

**Configuration:**
- `backend/app/config.py` — all settings via `Settings(BaseSettings)`; reads `backend/.env`
- `backend/.env.example` — required vars: `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `ALLOWED_ORIGINS`, `DEBUG`

**Database:**
- `backend/app/database.py` — engine creation, WAL pragma, `get_db()` dependency
- `data/database/expense_tracker.db` — SQLite file (path resolved relative to `backend/` dir)

**Encryption key:**
- `data/credentials/master.key` — Fernet key; auto-generated by `crypto_service.py` on first run; file permissions set to owner-only (0600)

**Frontend entry:**
- `frontend/src/main.jsx` — mounts `<App />`
- `frontend/src/App.jsx` — router + auth provider + all route definitions

**API client:**
- `frontend/src/services/api.js` — single Axios instance; all frontend API calls go through `authApi` or `transactionsApi` exports (or the default `api` instance for gmail calls)

---

## Naming Conventions

**Backend files:** `snake_case.py` for all modules. Services named `<domain>_service.py`. Parsers named `<bank>_parser.py`.

**Backend classes:** `PascalCase`. Services are classes with a module-level singleton instance: `auth_service = AuthService()`.

**Frontend files:** `PascalCase.jsx` for components and pages. `camelCase.js` for non-component modules (`api.js`).

**Frontend context/hooks:** Context file named after what it provides (`AuthContext.jsx`), exports both `AuthProvider` and `useAuth`.

---

## Where to Add New Code

**New bank parser (Phase 3):**
1. Create `backend/app/parsers/<bank>_parser.py` — subclass `BaseEmailParser`
2. Add instance to `PARSERS` list in `backend/app/parsers/parser_factory.py`
3. Extend `GMAIL_QUERY` in `backend/app/services/gmail_service.py` to include new sender domains

**New API endpoint group:**
1. Create `backend/app/api/routes/<domain>.py` with `router = APIRouter()`
2. Mount in `backend/app/main.py`: `app.include_router(<domain>.router, prefix="/api/<domain>")`

**New Pydantic schema:**
- Add to `backend/app/schemas/<domain>.py` (create file if domain is new)

**New service:**
- Create `backend/app/services/<domain>_service.py`
- Instantiate singleton at bottom: `<domain>_service = <Domain>Service()`

**New frontend page:**
1. Create `frontend/src/pages/<Name>Page.jsx`
2. Add route in `frontend/src/App.jsx` — wrap in `<ProtectedRoute>` and `<Layout>` as needed
3. Add `<NavLink>` in the `Layout` component's `<nav>` in `App.jsx`

**New frontend component:**
- Place in `frontend/src/components/<domain>/` matching the page/feature it supports

**New API calls (frontend):**
- Add to the relevant named export in `frontend/src/services/api.js` (`authApi`, `transactionsApi`)
- For Gmail/other domains, add a new named export object following the same pattern

**New categorizer keywords:**
- Edit `CATEGORY_RULES` list in `backend/app/parsers/categorizer.py`

---

## Special Directories

**`data/`:**
- Purpose: Runtime-generated files — database, encryption key, future uploads
- Generated: Yes (auto-created by `config.py` path resolution)
- Committed: No (in `.gitignore`)

**`backend/venv/`:**
- Purpose: Python 3.14 virtual environment
- Generated: Yes (`python -m venv venv`)
- Committed: No

**`frontend/node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes (`npm install`)
- Committed: No

**`frontend/dist/`:**
- Purpose: Vite production build output
- Generated: Yes (`npm run build`)
- Committed: No

**`backend/alembic/versions/`:**
- Purpose: Database migration scripts
- Currently: Empty — no migrations exist. Schema created via `Base.metadata.create_all()`.
- Committed: Yes (directory exists, no version files)

**`.planning/codebase/`:**
- Purpose: GSD mapping documents consumed by plan/execute commands
- Committed: Yes
