# Testing Patterns
_Generated: 2026-03-29_

## Summary

Testing infrastructure is partially set up but contains zero test files. The backend has pytest, pytest-asyncio, and httpx installed, and an empty `tests/` directory with a `fixtures/` subdirectory exists. No test files, no `conftest.py`, no pytest config, and no test code of any kind. The frontend has no test framework installed and no test files. This is a zero-coverage codebase.

---

## Current State

### Backend Test Setup
- **Frameworks installed:** `pytest==8.3.4`, `pytest-asyncio==0.24.0`, `httpx==0.28.1`
- **Test directory:** `backend/tests/` — exists but empty
- **Fixtures directory:** `backend/tests/fixtures/` — exists but empty
- **conftest.py:** Not present
- **pytest.ini / pyproject.toml:** Not present — no pytest configuration
- **Test files:** None

### Frontend Test Setup
- **Frameworks installed:** None — no Vitest, Jest, React Testing Library, or similar
- **Test scripts:** Not present in `frontend/package.json`
- **Test files:** None

### Coverage
- **Backend coverage:** 0%
- **Frontend coverage:** 0%
- **CI enforcement:** None

---

## What the Infrastructure Supports (Ready to Use)

The installed packages mean backend tests can be written immediately:

```bash
# From backend/ with venv active:
pytest                        # Run all tests
pytest tests/ -v              # Verbose output
pytest tests/ --tb=short      # Short tracebacks
pytest tests/ -x              # Stop on first failure
```

httpx's `AsyncClient` works with FastAPI's `TestClient` for HTTP-level integration tests without a running server:

```python
from httpx import AsyncClient
from app.main import app

async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
```

---

## Recommended Test Structure

### Backend

```
backend/tests/
├── conftest.py               # Shared fixtures: test DB, test client, sample users
├── fixtures/
│   └── email_samples/        # Raw email bodies for parser tests
├── test_auth.py              # Auth route integration tests
├── test_transactions.py      # Transaction CRUD integration tests
├── test_gmail.py             # Gmail route tests (mocked Google API)
├── unit/
│   ├── test_auth_service.py  # AuthService unit tests
│   ├── test_crypto_service.py
│   ├── test_totp_service.py
│   └── test_parsers/
│       └── test_hdfc_parser.py
```

### Frontend (requires installing Vitest + React Testing Library)

```
frontend/src/
├── components/auth/__tests__/
│   └── LoginForm.test.jsx
├── context/__tests__/
│   └── AuthContext.test.jsx
└── services/__tests__/
    └── api.test.js
```

---

## Critical Test Gaps (by Risk Priority)

### High Priority — Security-Critical Code with No Tests

**`backend/app/services/auth_service.py`**
- Password hashing and verification (`hash_password`, `verify_password`)
- JWT creation and validation for both `"access"` and `"temp"` token types
- Token type enforcement (temp token rejected as access token and vice versa)
- `register_user`: duplicate username/email rejection
- `authenticate_password`: bad credentials return 401, inactive account returns 403
- TOTP enrollment flow: `setup_totp` → `confirm_totp_enrollment`

**`backend/app/services/crypto_service.py`**
- Encrypt/decrypt round-trip
- Singleton behavior (same Fernet instance reused)
- Key persistence across instances

**`backend/app/services/totp_service.py`**
- TOTP verification with valid code succeeds
- TOTP verification with invalid code fails
- Clock skew window (`valid_window=1`) behavior

### High Priority — Route Authorization

**`backend/app/api/routes/transactions.py`**
- All routes return 401 without Bearer token
- User A cannot access User B's transactions (ownership enforcement in `transaction_service.get`)
- Pagination bounds: `page_size` max 200 enforced

**`backend/app/api/routes/auth.py`**
- Full login flow (password → temp token → TOTP → access token)
- TOTP setup flow (password → temp token → setup → verify → access token)
- `/auth/me` returns correct user

### Medium Priority — Business Logic

**`backend/app/services/transaction_service.py`**
- Create, get, update, delete cycle
- Ownership check: 404 when user_id doesn't match tx owner
- List filtering: date range, category, payment_method, search (ilike)
- Pagination: offset/limit math, `total_pages` calculation
- Summary: category and payment breakdowns

**`backend/app/schemas/transaction.py` and `backend/app/schemas/auth.py`**
- Pydantic validators: negative amount rejected, empty description rejected
- Invalid category/payment_method values rejected
- Password strength rules: uppercase, lowercase, digit, min 8 chars
- TOTP code format: exactly 6 digits

### Medium Priority — Email Parsers

**`backend/app/parsers/hdfc_parser.py`** and any future parsers
- `can_parse()` returns True/False for matching/non-matching senders
- `parse()` extracts correct amount, merchant, date from sample email bodies
- `parse()` returns `None` on malformed input (does not raise)
- These are pure functions with no DB dependency — easy to unit test with raw strings

**`backend/app/parsers/categorizer.py`**
- Merchant-to-category mapping logic

### Low Priority — Frontend

**`frontend/src/services/api.js`**
- Request interceptor attaches `Authorization: Bearer <token>` header
- Response interceptor redirects to `/login` on 401

**`frontend/src/context/AuthContext.jsx`**
- `login()` writes to localStorage and updates state
- `logout()` clears localStorage
- `isAuthenticated` is false when token absent from localStorage

---

## Recommended conftest.py Pattern

```python
# backend/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    from app.services.auth_service import auth_service
    return auth_service.register_user(db, "testuser", "test@example.com", "Password1")

@pytest.fixture
def auth_headers(test_user):
    from app.services.auth_service import auth_service
    token = auth_service.create_access_token(test_user.id, test_user.username)
    return {"Authorization": f"Bearer {token}"}
```

---

## Frontend Test Setup (When Needed)

Install Vitest and React Testing Library:
```bash
cd frontend
npm install -D vitest @vitest/ui jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

Add to `vite.config.js`:
```js
test: {
  globals: true,
  environment: 'jsdom',
  setupFiles: './src/test/setup.js',
}
```

Add test script to `package.json`:
```json
"test": "vitest",
"test:ui": "vitest --ui"
```

---

## Gaps / Unknowns

- **No pytest.ini or `[tool.pytest.ini_options]` in pyproject.toml** — pytest will run with all defaults. Add config to set `testpaths = ["tests"]` and `asyncio_mode = "auto"` for pytest-asyncio.
- **`backend/tests/fixtures/`** is empty — email sample bodies for parser tests should be added here as `.txt` or `.html` files.
- **Gmail service tests** require mocking the Google API client — consider `unittest.mock.patch` on `gmail_service.exchange_code` and the Gmail API list/get calls.
- **No snapshot or E2E tests** — no Playwright or Cypress setup. Not needed for current scope.
- **`CryptoService` tests** will require either a real key file or mocking `_load_or_create_key` to inject a test key — the singleton pattern means test isolation needs care.
