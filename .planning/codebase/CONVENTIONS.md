# Coding Conventions
_Generated: 2026-03-29_

## Summary

Full-stack Python/React codebase. Backend is FastAPI with SQLAlchemy; frontend is React 18 with Vite, Tailwind CSS, react-hook-form, and Zod. Conventions are consistent throughout: services use singleton pattern, routes are thin controllers, all validation happens in Pydantic schemas (backend) or Zod schemas (frontend). No linting config files are committed — ESLint is installed but `eslint.config.*` is absent from the repo root.

---

## Python Conventions

### File Naming
- Snake_case for all Python files: `auth_service.py`, `crypto_service.py`, `transaction_service.py`
- Router files match resource name: `auth.py`, `transactions.py`, `gmail.py`
- Model files match table/entity name: `user.py`, `transaction.py`, `session.py`, `email_metadata.py`

### Class and Variable Naming
- Classes: PascalCase — `AuthService`, `CryptoService`, `TransactionService`, `TOTPService`
- Instances (module-level singletons): snake_case — `auth_service`, `crypto_service`, `transaction_service`, `totp_service`
- Constants: UPPER_SNAKE_CASE — `ALGORITHM`, `TEMP_TOKEN_PREFIX`, `CATEGORIES`, `PAYMENT_METHODS`, `SOURCES`
- Parameters and local variables: snake_case — `user_id`, `tx_id`, `date_from`, `hashed`

### Module Docstrings
Every module begins with a `"""docstring"""` describing its purpose. This is consistent across all `app/` files.

```python
"""
Authentication service handling user registration, login, session management, and JWT.
"""
```

### Type Hints
Used consistently throughout. All function signatures include parameter types and return types:

```python
def hash_password(self, password: str) -> str: ...
def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]: ...
def list(self, db: Session, user_id: int, filters: TransactionFilters) -> dict: ...
def setup_totp(self, db: Session, user: User) -> tuple[str, str]: ...
```

`Optional[T]` from `typing` is used (not `T | None` union syntax). `list[T]` and `dict` bare types are used for return annotations on simpler methods.

### Import Organization
1. Standard library (`secrets`, `hashlib`, `datetime`, `math`, `os`, `stat`, `pathlib`)
2. Third-party packages (`bcrypt`, `jose`, `sqlalchemy`, `fastapi`, `pydantic`, `cryptography`, `pyotp`)
3. Internal app imports (`from app.config import ...`, `from app.models...`, `from app.services...`)

Internal imports always use absolute paths from `app.*` — no relative imports.

### Service Pattern (Singleton Classes)
All business logic lives in service classes. Each service file instantiates a module-level singleton at the bottom:

```python
class AuthService:
    def method(self, ...): ...

auth_service = AuthService()  # module-level singleton
```

Routes import the singleton directly:
```python
from app.services.auth_service import auth_service
```

`CryptoService` additionally implements `__new__` for true singleton enforcement (lazy Fernet key loading).

### Route Handler Pattern (Thin Controllers)
Route functions delegate immediately to service methods. No business logic in route files:

```python
@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_service.create(db, current_user.id, data)
```

### Pydantic Schema Conventions
- Schemas live in `backend/app/schemas/` — separate file per domain (`auth.py`, `transaction.py`)
- Validators use `@field_validator` with `@classmethod` (Pydantic v2 style)
- ORM output schemas set `model_config = {"from_attributes": True}` to enable SQLAlchemy model serialization
- Update schemas use `Optional[T] = None` for all fields (partial update pattern)

```python
class TransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    amount: Optional[Decimal] = None
    # ...

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v
```

### SQLAlchemy Model Conventions
- All models inherit from `Base` (imported from `app.database`)
- `__tablename__` is lowercase plural: `"users"`, `"transactions"`, `"user_sessions"`
- `created_at` and `updated_at` use `server_default=func.now()` — always present on every model
- Relationships declared with `back_populates` (bidirectional) and `cascade="all, delete-orphan"`
- Composite indexes declared in `__table_args__` as tuples of `Index(...)` objects

### Error Handling
`HTTPException` is raised directly from both route handlers and service methods. Services are allowed to raise HTTP exceptions — this is an established pattern, not a violation:

```python
def authenticate_password(self, db: Session, username: str, password: str) -> User:
    user = self.get_user_by_username(db, username)
    if not user or not self.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
```

Standard HTTP status codes used:
- `400` — Bad request / validation failure
- `401` — Unauthenticated
- `403` — Forbidden (account disabled)
- `404` — Resource not found
- `502` — Upstream service failure (Gmail sync)
- `503` — Integration not configured

External errors (OAuth, Gmail) are caught with broad `except Exception as e` and re-raised as `HTTPException` with the message included in `detail`.

### Security Conventions

**Passwords:** bcrypt with 12 rounds.
```python
bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
```

**JWT:** HS256 via `python-jose`. Two token types enforced by a `"type"` claim (`"access"` or `"temp"`). Access tokens expire in 30 min; temp tokens in 5 min.

**Encryption:** Fernet symmetric encryption via `cryptography` library. Master key auto-generated at `data/credentials/master.key` with 0600 permissions. All secrets stored encrypted: TOTP secrets, Gmail OAuth tokens.

**CORS:** Locked to configured origins only — no wildcard. Headers restricted to `Authorization` and `Content-Type`.

**Security headers middleware:** Applied globally via `app.middleware("http")` — sets `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`.

**Rate limiting:** slowapi with 200 req/min global default.

**API docs:** Disabled (`docs_url=None`) unless `debug=True`.

---

## JavaScript / React Conventions

### File Naming
- Components: PascalCase `.jsx` files — `LoginForm.jsx`, `TransactionForm.jsx`, `ProtectedRoute.jsx`
- Pages: PascalCase with `Page` suffix — `TransactionsPage.jsx`, `AnalyticsPage.jsx`, `GmailCallbackPage.jsx`
- Context: PascalCase with `Context` suffix — `AuthContext.jsx`
- Services: camelCase `.js` — `api.js`

### Component Pattern
All components are function components using arrow functions or `function` declarations. Default export per file. Named exports for context hooks:

```jsx
// Page components — function declarations
export default function TransactionsPage() { ... }

// Context providers — named + default exports
export function AuthProvider({ children }) { ... }
export function useAuth() { ... }
```

### Hooks Usage
- `useState` for local component state
- `useCallback` for stable function references passed as props or used in `useEffect` deps
- `useEffect` for data fetching on mount
- `useForm` from react-hook-form with `zodResolver` for all forms
- Custom hook `useAuth()` exported from `AuthContext.jsx` — must be used inside `AuthProvider`

### Form Validation Pattern
All forms use react-hook-form + Zod. Schema defined at module level, resolver wired in `useForm`:

```jsx
const schema = z.object({
  amount: z.string().refine(v => Number(v) > 0, 'Must be a positive number'),
  description: z.string().min(1).max(500),
})

const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(schema),
  defaultValues: { ... },
})
```

Error display pattern is consistent across all forms:
```jsx
{errors.fieldName && (
  <p className="text-red-600 text-xs mt-1">{errors.fieldName.message}</p>
)}
```

### API Service Pattern
All API calls go through the centralized axios instance in `frontend/src/services/api.js`. Grouped by domain as named object exports:

```js
export const transactionsApi = {
  list: (params) => api.get('/transactions', { params }),
  create: (data) => api.post('/transactions', data),
}
```

JWT is attached via request interceptor. 401 responses trigger automatic logout and redirect to `/login`.

### Error Handling in Components
`try/catch` with `finally` for loading state. Error messages extracted from `e.response?.data?.detail` (matching FastAPI's error shape):

```jsx
try {
  const res = await authApi.login(data)
  // handle success
} catch (e) {
  setError(e.response?.data?.detail || 'Login failed. Check your credentials.')
} finally {
  setLoading(false)
}
```

Success messages auto-clear with `setTimeout(() => setSuccess(''), 3000)`.

### Auth State
Stored in `localStorage` as two keys: `access_token` (raw JWT string) and `user` (JSON object `{id, username}`). Managed via `AuthContext`. The `isAuthenticated` check verifies both `user` state and `access_token` presence in storage.

### Styling Conventions
Pure Tailwind CSS utility classes. Custom component classes defined in `frontend/src/index.css` via `@layer components`:

| Class | Description |
|---|---|
| `.btn-primary` | Indigo filled button with disabled state |
| `.btn-secondary` | White outlined button |
| `.btn-danger` | Red filled button |
| `.input-field` | Standard form input with indigo focus ring |
| `.label` | Form field label |
| `.card` | White rounded card with shadow |
| `.badge` | Pill-shaped inline badge |

Use these classes from `index.css` — do not recreate them inline. Responsive design uses Tailwind breakpoints (`sm:`, `md:`).

### Routing
React Router v6. All routes defined in `App.jsx`. Protected routes wrapped with `<ProtectedRoute>` component. Layout (`<Layout>`) is applied per-route, not globally.

---

## API Design Conventions

### URL Structure
- Prefix: `/api/{resource}`
- RESTful resource naming, plural: `/api/transactions`, `/api/auth`, `/api/gmail`
- Resource actions: `POST /api/transactions`, `GET /api/transactions/{tx_id}`, `DELETE /api/transactions/{tx_id}`
- Sub-resources use slashes: `/api/auth/totp/setup`, `/api/auth/totp/verify`
- Health check: `GET /api/health`

### Response Shapes
- List responses: `{ items: [...], total: int, page: int, page_size: int, total_pages: int }`
- Create: returns created object with `status_code=201`
- Delete: `status_code=204`, no body
- Action endpoints: return flat dict with descriptive keys — `{ "status": "done", "emails_fetched": N, ... }`

### Authentication Header
```
Authorization: Bearer <jwt>
```
`get_current_user` dependency used on all protected routes via `Depends(get_current_user)`.

---

## Gaps / Unknowns

- **No ESLint config file committed** — `eslint` is in `devDependencies` and `lint` script exists in `package.json`, but no `eslint.config.js` or `.eslintrc` is present in the repo. Running `npm run lint` will fail or use defaults.
- **No Prettier config** — formatting is unenforced by tooling.
- **No pyproject.toml or setup.cfg** — no `black`, `ruff`, `isort`, or `flake8` configuration. Python formatting is consistent by convention, not by tooling.
- **`frontend/src/hooks/` and `frontend/src/utils/` directories exist** but contain no files — placeholders for future extraction.
- **`backend/app/utils/__init__.py` is empty** — utils module exists as a placeholder.
- **Partial `Optional` usage** — some return types use `Optional[T]` (from `typing`), but newer Python 3.10+ `T | None` syntax is not used. Consistent across the codebase but should be standardized when targeting Python 3.10+.
