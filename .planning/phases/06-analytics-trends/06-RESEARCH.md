# Phase 6: Analytics & Trends - Research

**Researched:** 2026-04-29
**Domain:** React/Recharts time-series charts, SQLite aggregation, FastAPI route patterns, React Router navigation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Line chart (not bar) using Recharts `LineChart` / `AreaChart`. Recharts is already installed and used on the Analytics page.
- **D-02:** Granularity toggle presented as a pill-style button group above the chart: `[Daily] [Weekly] [Monthly] [Annual]`. One active at a time.
- **D-03:** The trend chart lives on the **existing Analytics page**, above the current pie + bar charts. No new nav item.
- **D-04:** Clicking a data point on the trend chart navigates to `/transactions` with `date_from` and `date_to` pre-applied for that specific period (e.g., clicking "April" applies April 1–30 filter).
- **D-05:** New backend endpoint: `GET /api/transactions/trend?granularity=daily|weekly|monthly|annual&date_from=X&date_to=Y&payment_source=Z` — returns array of `{ period_label, period_start, period_end, total, count }`. Payment source filter passes through from the existing Analytics page filter.
- **D-06:** Projected end-of-period total shown as a KPI card: "At this rate: ₹X by [end of period]". Linear extrapolation: `(spend_so_far / days_elapsed) * total_days_in_period`.
- **D-07:** Spending limit is always visible on the Analytics page next to the burn-rate card — an always-editable input field. When a limit is set, show "₹X of ₹LIMIT (Y%)" with a subtle progress indicator. When no limit is set (empty), the burn-rate card shows projection only.
- **D-08:** Spending limits stored in DB per granularity. New `SpendingLimit` table: `(id, user_id, granularity, amount)` with unique constraint on `(user_id, granularity)`. Backend: `GET /api/spending-limit?granularity=X` and `PUT /api/spending-limit` `{ granularity, amount }`.
- **D-09:** Burn-rate projection only meaningful when viewing a period that is currently in progress. If date range is fully in the past, show actual total only (no projection).

### Claude's Discretion
- Exact visual style of the trend line (smooth curve vs straight segments, fill area vs line-only).
- Empty state for the trend chart when no data exists for the selected period.
- Visual style of the editable spending limit field (pencil icon, underline input, etc.).

### Deferred Ideas (OUT OF SCOPE)
- **D-10:** BUDGET-01 through BUDGET-04 (per-category monthly budgets with progress bars) — deferred to a future phase.
- **D-11:** GOAL-01 through GOAL-03 (monthly savings goals) — replaced by the simpler per-granularity spending limit in D-07/D-08.
- Trend chart comparison mode (e.g., this month vs last month overlay).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support | In Scope |
|----|-------------|------------------|----------|
| ANA-03 | Trend chart with granularity toggle: Daily / Weekly / Monthly / Annual | Recharts AreaChart + SQLite strftime grouping | YES |
| ANA-04 | Category overlay toggle on trend chart | Recharts multi-series Area, stacked by category | YES |
| ANA-05 | Drill-down: clicking trend bar filters transaction table | React Router useNavigate + URL query params | YES |
| ANA-06 | Period comparison callout: "X% more/less vs last period" | Backend computes previous period totals | YES |
| BUDGET-01 | User sets monthly spending limit per category | — | DEFERRED per D-10 |
| BUDGET-02 | Dashboard shows progress bar per budget | — | DEFERRED per D-10 |
| BUDGET-03 | Summary card: "X of Y budgets on track" | — | DEFERRED per D-10 |
| BUDGET-04 | Budgets auto-reset at start of each calendar month | — | DEFERRED per D-10 |
| GOAL-01 | User sets optional monthly savings target | Replaced by SpendingLimit (D-08) | DEFERRED per D-11 |
| GOAL-02 | Dashboard shows projected month-end spend based on burn rate | Burn-rate card (D-06) covers projection | YES (simplified) |
| GOAL-03 | Historical goal achievement shown as win/loss per month | — | DEFERRED per D-11 |
</phase_requirements>

---

## Summary

Phase 6 adds a time-series trend chart and a burn-rate projection card to the existing `AnalyticsPage.jsx`. The scope is tightly bounded by CONTEXT.md decisions: an AreaChart with granularity toggle, click-through navigation to `/transactions`, a burn-rate KPI card with a user-settable spending limit per granularity stored in a new `SpendingLimit` DB table, and period comparison stats. Per-category budgets and savings goals are fully deferred.

**Recharts AreaChart** is the correct chart type. It is already installed (v2.15.0) and used on the Analytics page (PieChart and BarChart are imported). Adding AreaChart requires only new imports. SQLite `strftime` handles all four granularity groupings. The `SpendingLimit` model follows the exact same Alembic migration pattern established by `CategoryRule` (Phase 5). React Router's `useNavigate` handles click-through to `/transactions` — the FilterPanel does NOT currently read URL params on mount, so the plan must wire initial filter state from `useLocation` in TransactionsPage (or use a different propagation strategy — see Open Questions).

**Primary recommendation:** Build in two backend plans (trend endpoint + SpendingLimit CRUD) and one frontend plan (AreaChart component + burn-rate card + URL-param seed for TransactionsPage).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | 2.15.0 (installed) | AreaChart, LineChart, CartesianGrid, XAxis, YAxis, Tooltip, ReferenceLine | Already used on AnalyticsPage |
| date-fns | 4.1.0 (installed) | period_start/period_end computation, label formatting | Already imported in AnalyticsPage |
| react-router-dom | 6.28.0 (installed) | useNavigate for chart click navigation, useLocation for param seeding | Already used throughout app |
| SQLAlchemy | 2.0.36 (installed) | func.strftime for grouping, raw aggregation queries | Already used |
| Alembic | 1.14.0 (installed) | SpendingLimit migration | Established in Phase 3 |
| FastAPI | 0.115.0 (installed) | New /trend and /spending-limit routes | Established pattern |
| Pydantic | 2.12.5 (installed) | Request/response schemas for new endpoints | Established pattern |

### No New Packages Required
All needed libraries are installed. No `npm install` or `pip install` needed for this phase.

---

## Architecture Patterns

### Recommended Project Structure (new files only)
```
backend/
├── app/
│   ├── models/
│   │   └── spending_limit.py          # NEW: SpendingLimit SQLAlchemy model
│   ├── schemas/
│   │   └── spending_limit.py          # NEW: Pydantic schemas
│   ├── services/
│   │   └── trend_service.py           # NEW: get_trend() + get_burn_rate()
│   └── api/routes/
│       └── analytics.py               # NEW: /trend and /spending-limit routes
├── alembic/versions/
│   └── XXXX_add_spending_limit.py     # NEW: Alembic migration
frontend/src/
└── pages/
    └── AnalyticsPage.jsx              # MODIFIED: add TrendChart + BurnRateCard sections
```

### Pattern 1: SQLite strftime Grouping (HIGH confidence)

SQLite's `strftime()` function is the standard way to group by time period. SQLAlchemy exposes it via `func.strftime()`.

**The four granularity formats:**
```python
# Source: SQLite official docs https://www.sqlite.org/lang_datefunc.html
GRANULARITY_FORMAT = {
    "daily":   "%Y-%m-%d",   # 2026-04-15
    "weekly":  "%Y-W%W",     # 2026-W15  (week starts Monday with %W)
    "monthly": "%Y-%m",      # 2026-04
    "annual":  "%Y",         # 2026
}
```

**Important:** SQLite stores `Date` columns as text (`YYYY-MM-DD`). `strftime()` works directly on the column. SQLAlchemy's `func.strftime(format, column)` maps to `strftime(format, column)` in SQL.

**Full trend query pattern:**
```python
from sqlalchemy import func
from app.models.transaction import Transaction

def get_trend(db, user_id, granularity, date_from, date_to, payment_source=None):
    fmt = GRANULARITY_FORMAT[granularity]
    base = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
    )
    if date_from:
        base = base.filter(Transaction.transaction_date >= date_from)
    if date_to:
        base = base.filter(Transaction.transaction_date <= date_to)
    if payment_source:
        base = base.filter(Transaction.payment_source == payment_source)

    rows = (
        base.with_entities(
            func.strftime(fmt, Transaction.transaction_date).label("period_key"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
            func.min(Transaction.transaction_date).label("period_start"),
            func.max(Transaction.transaction_date).label("period_end"),
        )
        .group_by(func.strftime(fmt, Transaction.transaction_date))
        .order_by(func.strftime(fmt, Transaction.transaction_date))
        .all()
    )
    return rows
```

**Caution on period_start/period_end from DB:** `func.min/max(transaction_date)` gives the first/last transaction date within the group — NOT the true calendar start/end of the period. For the click-through navigation (D-04), we need true calendar period boundaries. **Compute these in Python, not SQL**, using the `period_key` value.

### Pattern 2: Period Boundary Computation in Python (HIGH confidence)

```python
from datetime import date, timedelta
import calendar

def period_boundaries(granularity: str, period_key: str) -> tuple[date, date]:
    """Return true calendar start and end for the period."""
    if granularity == "daily":
        d = date.fromisoformat(period_key)         # "2026-04-15"
        return d, d
    elif granularity == "weekly":
        year, week = period_key.split("-W")         # "2026-W15"
        # ISO week: find Monday of that week
        # strftime %W = week number with Monday as first day
        d = date.fromisocalendar(int(year), int(week) + 1, 1)  # Caution: see note below
        return d, d + timedelta(days=6)
    elif granularity == "monthly":
        year, month = period_key.split("-")         # "2026-04"
        first = date(int(year), int(month), 1)
        last = date(int(year), int(month), calendar.monthrange(int(year), int(month))[1])
        return first, last
    elif granularity == "annual":
        year = int(period_key)                      # "2026"
        return date(year, 1, 1), date(year, 12, 31)
```

**Week number caution:** SQLite's `%W` counts weeks starting Monday (week 0 = days before first Monday). Python's `date.fromisocalendar()` uses ISO weeks (week 1 = first week with Thursday). These are different systems. The safest approach: when granularity is weekly, use `func.min(transaction_date)` for period_start directly and add 6 days for period_end. This gives the actual range of the data, which is close enough for the filter navigation.

### Pattern 3: SpendingLimit Model (HIGH confidence — mirrors CategoryRule pattern)

```python
# backend/app/models/spending_limit.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

class SpendingLimit(Base):
    __tablename__ = "spending_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    granularity = Column(String(20), nullable=False)   # "daily"|"weekly"|"monthly"|"annual"
    amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "granularity", name="uq_spending_limit_user_granularity"),
    )
```

**Alembic migration command (after model created and registered in `__init__.py` and `env.py`):**
```bash
cd backend
source venv/Scripts/activate
alembic revision --autogenerate -m "add_spending_limit"
# Review generated file then:
alembic upgrade head
```

### Pattern 4: New Route File for Analytics Endpoints (HIGH confidence)

The trend endpoint and spending-limit endpoints are better placed in a new `analytics.py` router than bolted onto the already-long `transactions.py`. This matches the existing pattern of one router per concern (`auth.py`, `transactions.py`, `gmail.py`).

Register in `main.py`:
```python
from app.api.routes import auth, transactions, gmail, analytics

app.include_router(analytics.router, prefix="/api", tags=["analytics"])
```

Routes exposed:
- `GET /api/transactions/trend` — trend aggregation (can stay in transactions.py to keep `/api/transactions/*` consistent, OR move to analytics.py as `/api/analytics/trend`)
- `GET /api/spending-limit` — get limit for granularity
- `PUT /api/spending-limit` — upsert limit

**Decision note for planner:** Spending-limit routes are user-level settings, not transaction sub-resources. Placing them at `/api/spending-limit` (own router) is cleaner and avoids the static-before-dynamic ordering constraint in transactions.py.

### Pattern 5: Recharts AreaChart with Click Handler (HIGH confidence)

```jsx
// Source: Recharts official docs https://recharts.org/en-US/api/AreaChart
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine
} from 'recharts'
import { useNavigate } from 'react-router-dom'

function TrendChart({ data, onPointClick }) {
  const navigate = useNavigate()

  function handleChartClick(payload) {
    // payload.activePayload[0].payload is the data point
    if (!payload || !payload.activePayload) return
    const point = payload.activePayload[0].payload
    navigate(`/transactions?date_from=${point.period_start}&date_to=${point.period_end}`)
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} onClick={handleChartClick} style={{ cursor: 'pointer' }}>
        <defs>
          <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="period_label" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
        <Tooltip formatter={(v) => formatINR(v)} />
        <Area
          type="monotone"
          dataKey="total"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#colorTotal)"
          dot={{ r: 3, fill: '#6366f1' }}
          activeDot={{ r: 5 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
```

**`type="monotone"`** produces smooth Bezier curves. This is the correct choice per D-01/Specifics "smooth area chart."

### Pattern 6: Seeding FilterPanel from URL Params (CRITICAL — gap found)

**Current state:** FilterPanel does NOT read `window.location.search` or `useSearchParams` on mount. It initializes with empty `react-hook-form` defaults. Navigating to `/transactions?date_from=2026-04-01&date_to=2026-04-30` will update the URL but the filter panel will show blank fields, and the initial fetch will use empty filters (no date range).

**Required fix (two options):**

Option A — Modify TransactionsPage to seed filters from URL params on mount (preferred):
```jsx
// TransactionsPage.jsx — add useSearchParams seeding
import { useSearchParams } from 'react-router-dom'

export default function TransactionsPage() {
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState(() => {
    const initial = {}
    if (searchParams.get('date_from')) initial.date_from = searchParams.get('date_from')
    if (searchParams.get('date_to')) initial.date_to = searchParams.get('date_to')
    return initial
  })
  // Pass initialFilters to FilterPanel so it pre-fills form fields
  // ...
}
```

Option B — Add `defaultValues` prop to FilterPanel and use `useSearchParams` inside it.

**The planner MUST include a task to implement URL-param seeding** — without it, click-through navigation (D-04) will navigate to `/transactions` but show unfiltered results.

### Pattern 7: ANA-04 Category Overlay on Trend Chart

ANA-04 asks for a "category overlay toggle." In the context of an AreaChart, this means rendering multiple `<Area>` series — one per category — stacked or overlaid. Recharts supports this with multiple `<Area>` components sharing the same `AreaChart`.

**Backend implication:** The trend endpoint must support returning per-category breakdown when the overlay is active. Two options:
1. A separate endpoint `GET /api/analytics/trend/by-category` — returns `{ period_key, category, total }` rows.
2. The same trend endpoint with `?breakdown=category` param — returns extended payload.

The simpler approach: always return a `category_totals` object in each trend data point. Frontend ignores it when overlay is off.

**Backend shape with category breakdown:**
```json
[
  {
    "period_label": "Apr 2026",
    "period_start": "2026-04-01",
    "period_end": "2026-04-30",
    "total": 15000.00,
    "count": 23,
    "category_totals": {
      "Food & Dining": 4500.00,
      "Shopping": 6000.00,
      "Transport": 2500.00,
      "Others": 2000.00
    }
  }
]
```

### Pattern 8: Burn-Rate Projection Logic (ANA-06 / D-06 / D-09)

```python
from datetime import date

def compute_burn_rate(
    period_start: date,
    period_end: date,
    spend_so_far: float,
) -> dict:
    today = date.today()
    total_days = (period_end - period_start).days + 1
    days_elapsed = min((today - period_start).days + 1, total_days)

    period_in_progress = period_start <= today <= period_end

    if not period_in_progress or days_elapsed == 0:
        return {"projected": None, "in_progress": False}

    daily_rate = spend_so_far / days_elapsed
    projected = daily_rate * total_days

    return {
        "projected": round(projected, 2),
        "in_progress": True,
        "daily_rate": round(daily_rate, 2),
        "days_elapsed": days_elapsed,
        "total_days": total_days,
    }
```

**D-09 compliance:** When `period_in_progress` is False (entire date range is in the past), return `projected: None`. The frontend shows "Actual: ₹X" rather than a projection.

### Pattern 9: ANA-06 — Period Comparison Callout

"X% more/less vs last period" requires computing the equivalent prior period total. The backend trend endpoint can compute this inline, or a separate call can be made.

**Recommended approach:** Include `previous_period_total` in the `/trend` response or as a separate field in the `/summary`-like response. Computing inline in the trend service is cleaner.

```python
def get_previous_period_total(db, user_id, granularity, date_from, date_to, payment_source=None):
    """Compute total for the equivalent previous period."""
    delta = date_to - date_from + timedelta(days=1)  # Duration of current period
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - delta + timedelta(days=1)
    # Run a simple SUM query for prev_from..prev_to
    ...
```

Return in trend response summary: `{ current_total, previous_total, pct_change }`.

### Anti-Patterns to Avoid
- **Putting period boundaries in SQL:** `func.min/max(transaction_date)` gives data bounds, not calendar bounds. Compute calendar boundaries in Python from the period_key.
- **Using `%V` for ISO week numbers in SQLite:** SQLite's `%W` and ISO's `%V` differ in week 0 handling. Stick with `%W` consistently and compute boundaries from `func.min(transaction_date)` for weekly grouping.
- **Modifying FilterPanel to navigate imperatively on mount:** Don't call `navigate()` inside FilterPanel. Seed the form from props passed in from TransactionsPage, which reads URL params once.
- **Adding spending-limit routes to transactions.py:** The static-before-dynamic route ordering constraint in transactions.py is already fragile. Add spending-limit to its own router.
- **Forgetting to add SpendingLimit to `env.py` and `__init__.py`:** Both files must reference the new model for Alembic autogenerate to detect it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Smooth curve on chart | Custom SVG bezier curve | Recharts `type="monotone"` on `<Area>` | Built-in, handles all edge cases |
| Date formatting for chart labels | Custom format function | `date-fns` `format()` already imported | Handles locale, timezone edge cases |
| URL query string construction | Manual string building | `URLSearchParams` or React Router `createSearchParams` | Handles encoding, special chars |
| Week start/end computation | Manual arithmetic | `date-fns` `startOfWeek/endOfWeek` (already installed) | Handles DST, locale week start |
| SQLite week grouping | Custom aggregation | `func.strftime('%Y-W%W', ...)` | Native SQLite function |
| Upsert for SpendingLimit | INSERT + try/except loop | SQLAlchemy `merge()` or query-then-update pattern | Cleaner, leverages unique constraint |

**Key insight:** All new functionality builds on already-installed packages. Zero new dependencies required.

---

## Runtime State Inventory

Step 2.5: SKIPPED — This is not a rename/refactor/migration phase. The `SpendingLimit` table is additive (new table, no data migration).

---

## Common Pitfalls

### Pitfall 1: FilterPanel Does Not Read URL Params
**What goes wrong:** User clicks a trend data point, navigates to `/transactions?date_from=X&date_to=Y`, but the transaction list loads with no filter because FilterPanel initializes from empty `useForm()` defaults, not from the URL.
**Why it happens:** FilterPanel was designed for user-driven filter interaction, not programmatic pre-seeding. It has no `useSearchParams` or `defaultValues` wiring.
**How to avoid:** In TransactionsPage, read `useSearchParams()` during component initialization and pass `initialFilters` as a prop to FilterPanel. FilterPanel uses `defaultValues` in `useForm({ defaultValues: initialFilters })`.
**Warning signs:** Clicking a chart point navigates correctly (URL updates) but transaction list shows all transactions with no date filter applied.

### Pitfall 2: Week Number Mismatch Between SQLite %W and Python
**What goes wrong:** SQLite `strftime('%W', date)` assigns week 0 to days before the first Monday of the year. Python's `date.isocalendar()` uses ISO 8601 weeks (week 1 = contains first Thursday). A period_key of "2026-W00" has no direct ISO equivalent.
**Why it happens:** Two incompatible week-numbering systems.
**How to avoid:** For weekly granularity, use `func.min(Transaction.transaction_date)` as `period_start` directly from the DB query, and add 6 days for `period_end`. Do not attempt to parse the week key back into a calendar date.
**Warning signs:** Week boundaries are off by 1 or 7 days; click-through filter includes wrong transactions.

### Pitfall 3: AlembicRoute Ordering for Spending Limit (Static vs Dynamic)
**What goes wrong:** If spending-limit routes are added as `/api/transactions/spending-limit`, they conflict with the `/api/transactions/{tx_id}` catch-all. FastAPI matches routes top-to-bottom; this was already a known pain point documented in STATE.md.
**Why it happens:** FastAPI path parameters match any string. A route defined after `/{tx_id}` will never be reached.
**How to avoid:** Use a separate router at `/api/spending-limit` (own file). Register it in main.py before or after the transactions router — there's no conflict since the prefix is different.
**Warning signs:** `GET /api/spending-limit?granularity=monthly` returns 422 (tx_id validation error) instead of spending limit data.

### Pitfall 4: Alembic Not Detecting SpendingLimit Model
**What goes wrong:** `alembic revision --autogenerate` produces an empty migration (no table created).
**Why it happens:** The model must be imported in both `alembic/env.py` and `app/models/__init__.py` before autogenerate runs.
**How to avoid:** After creating `spending_limit.py`:
1. Add `from app.models.spending_limit import SpendingLimit` to `app/models/__init__.py`
2. Add `spending_limit` to the `from app.models import ...` line in `alembic/env.py`
3. Then run `alembic revision --autogenerate`
**Warning signs:** Generated migration has `# ### end Alembic commands ###` immediately after `def upgrade(): pass`.

### Pitfall 5: Burn-Rate Showing for Past Periods
**What goes wrong:** A burn-rate projection is shown even when the selected date range is entirely in the past (e.g., January 2026 when today is April 2026), giving a confusing "at this rate" message for a period that has ended.
**Why it happens:** Frontend doesn't check whether the selected `date_to` < today.
**How to avoid:** Implement D-09 check: `if date_to < today: show "Actual: ₹X only"`. The backend can set `in_progress: false` in the burn-rate response, or the frontend can check `dateTo < format(new Date(), 'yyyy-MM-dd')`.
**Warning signs:** Burn-rate card shows "At this rate: ₹X by Dec 31" for a range that ended months ago.

### Pitfall 6: Empty Period Gaps in Trend Chart
**What goes wrong:** If there are no transactions on some days/weeks, the chart has gaps rather than connecting the line (Recharts renders `null` gaps).
**Why it happens:** The DB query only returns periods with transactions. Days/weeks with zero spend are absent.
**How to avoid:** Two strategies:
- **Fill gaps on backend:** Generate all period keys for the range, LEFT JOIN with query results, set total=0 for missing.
- **Fill gaps on frontend:** Use `connectNulls={true}` on `<Area>` to bridge missing data points. Simpler and sufficient for this use case.
**Warning signs:** Trend line has visible breaks/gaps for periods with no spending.

---

## Code Examples

### Trend Endpoint Response Shape
```json
{
  "trend": [
    {
      "period_label": "Apr 1",
      "period_start": "2026-04-01",
      "period_end": "2026-04-01",
      "total": 850.00,
      "count": 3,
      "category_totals": { "Food & Dining": 450.00, "Transport": 400.00 }
    }
  ],
  "current_total": 15000.00,
  "previous_total": 12000.00,
  "pct_change": 25.0,
  "burn_rate": {
    "projected": 18500.00,
    "in_progress": true,
    "daily_rate": 617.00,
    "days_elapsed": 29,
    "total_days": 30
  }
}
```

### Granularity Pill Toggle (React)
```jsx
const GRANULARITIES = ['daily', 'weekly', 'monthly', 'annual']

function GranularityToggle({ value, onChange }) {
  return (
    <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
      {GRANULARITIES.map(g => (
        <button
          key={g}
          onClick={() => onChange(g)}
          className={`px-3 py-1 rounded-md text-sm font-medium transition-colors capitalize ${
            value === g
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {g.charAt(0).toUpperCase() + g.slice(1)}
        </button>
      ))}
    </div>
  )
}
```

### SpendingLimit Upsert (Backend)
```python
from sqlalchemy.orm import Session
from app.models.spending_limit import SpendingLimit

def upsert_spending_limit(db: Session, user_id: int, granularity: str, amount: float):
    existing = db.query(SpendingLimit).filter_by(
        user_id=user_id, granularity=granularity
    ).first()
    if existing:
        existing.amount = amount
    else:
        db.add(SpendingLimit(user_id=user_id, granularity=granularity, amount=amount))
    db.commit()
```

### URL Navigation from Chart Click
```jsx
import { useNavigate } from 'react-router-dom'
import { createSearchParams } from 'react-router-dom'

// Inside TrendChart component:
const navigate = useNavigate()

function handleChartClick(data) {
  if (!data?.activePayload?.[0]) return
  const { period_start, period_end } = data.activePayload[0].payload
  navigate({
    pathname: '/transactions',
    search: createSearchParams({ date_from: period_start, date_to: period_end }).toString()
  })
}
```

### TransactionsPage URL Param Seeding
```jsx
import { useSearchParams } from 'react-router-dom'

export default function TransactionsPage() {
  const [searchParams] = useSearchParams()

  const [filters, setFilters] = useState(() => {
    const init = {}
    const df = searchParams.get('date_from')
    const dt = searchParams.get('date_to')
    if (df) init.date_from = df
    if (dt) init.date_to = dt
    return init
  })

  // Pass to FilterPanel:
  // <FilterPanel onFilter={handleFilter} loading={loading} initialValues={filters} />
  // FilterPanel uses: useForm({ defaultValues: initialValues ?? {} })
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|----------------------|
| Bar chart for time series | AreaChart with smooth monotone curve | Recharts supports both; use AreaChart as decided |
| Manual SQLite date queries | `func.strftime()` via SQLAlchemy | Established in project; use same pattern |
| Global filter state in URL | React Router `useSearchParams` | Available in react-router-dom 6.x; seed TransactionsPage from it |

---

## Open Questions

1. **ANA-04 scope: does "category overlay toggle" mean stacked areas or separate lines?**
   - What we know: ANA-04 says "category overlay toggle on trend chart"
   - What's unclear: Stacked areas (each category stacked on top) vs overlaid lines (multiple lines on same chart) — they look very different. Stacked areas require `stackId="a"` on all `<Area>` components.
   - Recommendation: Planner should pick stacked areas (cleaner for spending data; shows proportion over time). If only 1-2 categories, overlaid lines are fine too.

2. **Weekly period_start/period_end for click-through — data-driven or calendar-driven?**
   - What we know: SQLite's `%W` doesn't map cleanly to ISO weeks.
   - What's unclear: If we click "Week 15" and pass `period_start = func.min(date)`, the filter covers only days with actual transactions, not Mon–Sun.
   - Recommendation: For weekly granularity, compute true Mon–Sun bounds from `func.min(transaction_date)` (use that date's Monday via `date-fns` `startOfWeek`) and add 6 days. This is more accurate for the user.

3. **Spending limit delete (clear) flow**
   - What we know: D-07 says "always-editable input field, saving on blur or Enter"
   - What's unclear: If user clears the field and blurs — does that delete the spending limit from DB or leave the old value?
   - Recommendation: If field is cleared/empty on blur, call `DELETE /api/spending-limit?granularity=X` (or `PUT` with `amount: null`). Add a `DELETE` endpoint or allow `PUT` with `amount: 0` as "no limit."

---

## Environment Availability

All dependencies are already installed. No external services or new runtimes required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| recharts | TrendChart, AreaChart | Yes | 2.15.0 | — |
| date-fns | Period label formatting | Yes | 4.1.0 | — |
| react-router-dom | useNavigate, useSearchParams | Yes | 6.28.0 | — |
| SQLAlchemy | func.strftime grouping | Yes | 2.0.36 | — |
| Alembic | SpendingLimit migration | Yes | 1.14.0 | — |
| FastAPI | New route endpoints | Yes | 0.115.0 | — |
| Pydantic | Request/response schemas | Yes | 2.12.5 | — |

**No missing dependencies.**

---

## Validation Architecture

`workflow.nyquist_validation` is not set to `false` in `.planning/config.json` (key absent) — validation section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (established in project) |
| Config file | none (pytest discovers `backend/tests/` automatically) |
| Quick run command | `cd backend && source venv/Scripts/activate && pytest tests/test_trend_service.py -x -q` |
| Full suite command | `cd backend && source venv/Scripts/activate && pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANA-03 | `get_trend()` returns correct grouping for daily/weekly/monthly/annual | unit | `pytest tests/test_trend_service.py -x -q` | Wave 0 |
| ANA-03 | Trend endpoint returns 200 with correct shape | integration | `pytest tests/test_trend_service.py -x -q` | Wave 0 |
| ANA-04 | `get_trend()` returns category_totals in each period | unit | `pytest tests/test_trend_service.py::test_trend_category_totals -x` | Wave 0 |
| ANA-05 | Frontend URL navigation — manual verify | manual | navigate to `/transactions?date_from=X&date_to=Y` | n/a |
| ANA-06 | `compute_pct_change()` returns correct percentage | unit | `pytest tests/test_trend_service.py::test_pct_change -x` | Wave 0 |
| D-08 | `upsert_spending_limit()` inserts new and updates existing | unit | `pytest tests/test_spending_limit.py -x -q` | Wave 0 |
| D-08 | `GET /api/spending-limit` returns correct row | unit | `pytest tests/test_spending_limit.py -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_trend_service.py tests/test_spending_limit.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_trend_service.py` — covers ANA-03, ANA-04, ANA-06
- [ ] `backend/tests/test_spending_limit.py` — covers D-08 CRUD

*(Frontend is Vite/React with no test runner configured; frontend tests are manual verification only — consistent with all prior phases.)*

---

## Sources

### Primary (HIGH confidence)
- Recharts official docs (https://recharts.org/en-US/api/AreaChart) — AreaChart props, click handlers, type="monotone"
- SQLite official docs (https://www.sqlite.org/lang_datefunc.html) — strftime format strings
- React Router v6 docs (https://reactrouter.com/en/6.28.0/hooks/use-search-params) — useSearchParams, createSearchParams
- SQLAlchemy 2.0 docs — func.strftime usage
- Direct codebase reading — all patterns verified against existing files

### Secondary (MEDIUM confidence)
- Recharts GitHub examples — gradient fill pattern for AreaChart

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified by reading `package.json` and `pip list` output
- Architecture: HIGH — all patterns derived from existing codebase files and official docs
- SQLite strftime: HIGH — verified against official SQLite docs
- FilterPanel URL-param gap: HIGH — confirmed by reading FilterPanel.jsx source (no useSearchParams)
- Pitfalls: HIGH — all identified from direct code inspection and known SQLite/React Router behaviors

**Research date:** 2026-04-29
**Valid until:** 2026-06-01 (stable ecosystem — recharts, react-router, SQLite strftime are not fast-moving)
