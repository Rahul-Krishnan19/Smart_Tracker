# Technology Stack

_Generated: 2026-03-29_

## Summary

Full-stack personal expense tracker with a FastAPI/SQLite backend and a React/Vite frontend. The backend handles JWT + TOTP authentication, Fernet-encrypted secret storage, and Gmail-based transaction ingestion. The frontend is a single-page app with Tailwind styling, Recharts analytics, and a Vite dev proxy to avoid CORS in development.

---

## Languages

**Primary:**
- Python 3.14 — entire backend (`backend/`)
- JavaScript (ES Modules) — entire frontend (`frontend/`)

**Secondary:**
- SQL — SQLite via SQLAlchemy ORM

---

## Runtime

**Backend:**
- Python 3.14 (only version installed on host)
- Virtual environment: `backend/venv/` (activate via `source venv/Scripts/activate`)

**Frontend:**
- Node.js (version unspecified; no `.nvmrc`)
- Package manager: npm (lockfile present: `frontend/package-lock.json` assumed)

---

## Frameworks

**Backend:**
- `fastapi==0.115.0` — async HTTP framework, REST API
- `uvicorn[standard]==0.32.0` — ASGI server; run with `uvicorn app.main:app --reload --port 8000`
- `python-multipart==0.0.19` — multipart/form-data parsing (required by FastAPI)
- `alembic==1.14.0` — database migrations (configured but migrations workflow not yet scripted)

**Frontend:**
- `react==^18.3.1` + `react-dom==^18.3.1` — UI framework
- `vite==^6.0.3` — build tool and dev server (port 3000)
- `@vitejs/plugin-react==^4.3.4` — Babel-based React JSX transform

---

## Key Dependencies

**Database / ORM:**
- `sqlalchemy==2.0.36` — ORM and query builder
  - Engine: `sqlite:///` with WAL journal mode and foreign keys enabled (`backend/app/database.py`)
  - DB file: `data/database/expense_tracker.db` (relative to repo root)

**Authentication:**
- `bcrypt==4.2.1` — password hashing (12 rounds, `backend/app/services/auth_service.py`)
- `python-jose[cryptography]==3.3.0` — JWT encode/decode, algorithm HS256
  - Access token TTL: 30 minutes (configurable via `jwt_expire_minutes`)
  - Temp token TTL: 5 minutes (used between password verify and TOTP verify)
- `pyotp==2.9.0` — TOTP generation and verification, 1-period clock-skew window
- `qrcode==8.0` — QR code PNG generation for TOTP enrollment
- `Pillow` (version unpinned) — required by qrcode image rendering

**Encryption:**
- `cryptography==44.0.0` — provides `cryptography.fernet.Fernet`
  - Singleton `CryptoService` at `backend/app/services/crypto_service.py`
  - Master key auto-generated and stored at `data/credentials/master.key` (chmod 0600 best-effort)
  - Encrypts: Gmail OAuth tokens, TOTP secrets (both stored as `Text` columns in SQLite)

**Validation:**
- `pydantic==2.12.5` — request/response schema validation
  - NOTE: `pydantic==2.10.3` fails on Python 3.14 (pydantic-core requires Rust compilation). Must use `>=2.12.5`.
- `pydantic-settings==2.8.1` — settings loaded from `.env` via `backend/app/config.py`
- `email-validator==2.2.0` — validates email fields in Pydantic schemas

**Security / Middleware:**
- `slowapi==0.1.9` — rate limiting; default 200 req/min per IP (`backend/app/main.py`)
- Security headers middleware (custom, inline in `backend/app/main.py`): `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`
- CORS: configured via `CORSMiddleware`, origin whitelist from `ALLOWED_ORIGINS` env var

**Gmail / Google APIs:**
- `google-auth==2.37.0` — Google credential objects and token refresh
- `google-auth-oauthlib==1.2.1` — OAuth2 flow (`Flow.from_client_config`)
- `google-auth-httplib2==0.2.0` — HTTP transport for google-auth
- `google-api-python-client==2.155.0` — Gmail API client (`build("gmail", "v1", ...)`)

**Testing:**
- `pytest==8.3.4` — test runner
- `pytest-asyncio==0.24.0` — async test support
- `httpx==0.28.1` — async HTTP client used in tests (TestClient compatible)

**Frontend — UI / Routing:**
- `react-router-dom==^6.28.0` — client-side routing, `BrowserRouter`; routes in `frontend/src/App.jsx`
- `axios==^1.7.9` — HTTP client; configured instance in `frontend/src/services/api.js` with JWT interceptors
- `tailwindcss==^3.4.1` + `autoprefixer==^10.4.17` + `postcss==^8.4.35` — utility-first CSS

**Frontend — Forms / Validation:**
- `react-hook-form==^7.54.2` — form state management
- `zod==^3.24.1` — schema validation
- `@hookform/resolvers==^3.9.1` — connects Zod to react-hook-form

**Frontend — Data Visualization:**
- `recharts==^2.15.0` — chart components for analytics; used in `frontend/src/pages/AnalyticsPage.jsx`
- `date-fns==^4.1.0` — date formatting utilities

**Frontend — Dev / Linting:**
- `eslint==^9.18.0` + `eslint-plugin-react==^7.37.2` + `eslint-plugin-react-hooks==^5.0.0`

---

## Configuration

**Environment (backend):**
- Loaded from `backend/.env` via `pydantic-settings` (`backend/app/config.py`)
- Key settings and defaults:

| Setting | Default | Notes |
|---|---|---|
| `SECRET_KEY` | `change-this-...` | JWT signing key — must be changed |
| `DEBUG` | `False` | Enables `/api/docs` when `True` |
| `DATABASE_URL` | `../data/database/expense_tracker.db` | Relative path resolved from `backend/` |
| `ENCRYPTION_KEY_PATH` | `../data/credentials/master.key` | Fernet key file |
| `GOOGLE_CLIENT_ID` | `""` | Required for Gmail integration |
| `GOOGLE_CLIENT_SECRET` | `""` | Required for Gmail integration |
| `GOOGLE_REDIRECT_URI` | `http://localhost:3000/auth/gmail/callback` | OAuth callback URL |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS origins |
| `JWT_EXPIRE_MINUTES` | `30` | Access token TTL |
| `SESSION_EXPIRE_HOURS` | `24` | Server-side session TTL |
| `EMAIL_RETENTION_DAYS` | `30` | Email metadata retention |

**Frontend (Vite):**
- Config: `frontend/vite.config.js`
- Dev server port: 3000
- Proxy: all `/api` requests forwarded to `http://localhost:8000`

---

## Platform Constraints

**Python 3.14 — known incompatibilities:**
- `pydantic<=2.10.x` — fails: pydantic-core requires Rust compilation. Use `pydantic==2.12.5`.
- `pandas>=2.2` — fails: requires meson + Visual Studio build tools. Commented out in `requirements.txt`; deferred to Phase 4.
- `openpyxl==3.1.5` — also deferred to Phase 4.
- Google API libraries are included and working (no Rust/C compilation needed).

**Pillow:**
- Version unpinned in `requirements.txt`. Pin to a specific version before deployment to ensure reproducible builds.

---

## Production Notes

- Deployment target: VPS (Phase 7, not yet implemented)
- No Docker configuration detected
- No production WSGI/ASGI server config beyond `uvicorn` CLI

---

_Stack analysis: 2026-03-29_
