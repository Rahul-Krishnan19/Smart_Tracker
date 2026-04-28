# Phase 6: Analytics & Trends - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a time-series trend line chart to the existing Analytics page with granularity toggle (Daily/Weekly/Monthly/Annual), click-through navigation to filtered transactions, and a burn-rate projection card with a user-settable spending limit per granularity.

Per-category budgets (BUDGET-01–04) and savings goals (GOAL-01–03) are explicitly DEFERRED — not in scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Trend Chart
- **D-01:** Line chart (not bar) using Recharts `LineChart` / `AreaChart`. Recharts is already installed and used on the Analytics page.
- **D-02:** Granularity toggle presented as a pill-style button group above the chart: `[Daily] [Weekly] [Monthly] [Annual]`. One active at a time.
- **D-03:** The trend chart lives on the **existing Analytics page**, above the current pie + bar charts. No new nav item.
- **D-04:** Clicking a data point on the trend chart navigates to `/transactions` with `date_from` and `date_to` pre-applied for that specific period (e.g., clicking "April" applies April 1–30 filter).
- **D-05:** New backend endpoint: `GET /api/transactions/trend?granularity=daily|weekly|monthly|annual&date_from=X&date_to=Y&payment_source=Z` — returns array of `{ period_label, period_start, period_end, total, count }`. Payment source filter passes through from the existing Analytics page filter.

### Burn-Rate Projection
- **D-06:** Projected end-of-period total shown as a KPI card: "At this rate: ₹X by [end of period]". Linear extrapolation: `(spend_so_far / days_elapsed) * total_days_in_period`.
- **D-07:** Spending limit is always visible on the Analytics page next to the burn-rate card — an always-editable input field (not click-to-reveal). User can change the value at any time; saving is immediate (on blur or Enter). When a limit is set, show "₹X of ₹LIMIT (Y%)" with a subtle progress indicator. When no limit is set (empty), the burn-rate card shows projection only.
- **D-08:** Spending limits are stored in DB per granularity (separate limit for Daily / Weekly / Monthly / Annual). New `SpendingLimit` table: `(id, user_id, granularity, amount)` with a unique constraint on `(user_id, granularity)`. Backend: `GET /api/spending-limit?granularity=X` and `PUT /api/spending-limit` `{ granularity, amount }`.
- **D-09:** Burn-rate projection only meaningful when viewing a period that is currently in progress (e.g., current month). If date range is fully in the past, show actual total only (no projection).

### Deferred
- **D-10:** BUDGET-01 through BUDGET-04 (per-category monthly budgets with progress bars) — deferred to a future phase.
- **D-11:** GOAL-01 through GOAL-03 (monthly savings goals) — replaced by the simpler per-granularity spending limit in D-07/D-08.

### Claude's Discretion
- Exact visual style of the trend line (smooth curve vs straight segments, fill area vs line-only) — Claude picks what looks cleanest with the existing chart style.
- Empty state for the trend chart when no data exists for the selected period.
- Visual style of the editable spending limit field (pencil icon, underline input, etc.).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Analytics page
- `frontend/src/pages/AnalyticsPage.jsx` — Current state: has Recharts PieChart + BarChart, date range picker, payment source filter, merchant breakdown table. Trend chart goes above the existing charts.

### Existing API
- `backend/app/api/routes/transactions.py` — All transaction endpoints. New `/trend` and `/spending-limit` routes follow the same auth/filter patterns.
- `backend/app/services/transaction_service.py` — `_build_filter_query` helper must be reused for the trend query.

### Frontend routing
- `frontend/src/App.jsx` — React Router setup. Clicking trend chart navigates to `/transactions` with query params.

### No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Recharts` (PieChart, BarChart, LineChart, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend) — all available in the installed package, only PieChart and BarChart currently imported. Add LineChart/AreaChart imports.
- `formatINR()` in AnalyticsPage.jsx — reuse for all currency display in new cards.
- `transactionsApi` in `frontend/src/services/api.js` — add `trend(params)` and `getSpendingLimit(granularity)` / `setSpendingLimit(data)` methods.
- `_build_filter_query()` in `transaction_service.py` — reuse as base for the trend aggregation query.
- `date-fns` already imported in AnalyticsPage (`format`, `startOfMonth`, `endOfMonth`) — use for period label formatting and period_start/period_end computation.

### Established Patterns
- Backend filter params: `date_from`, `date_to`, `payment_source` passed as query params — trend endpoint follows same pattern.
- Card-based layout with `className="card"` — all new sections follow this pattern.
- KPI cards: `<div className="card text-center">` with label + large bold number — burn-rate card follows this.
- Alembic for DB migrations — new `SpendingLimit` table needs a migration.

### Integration Points
- AnalyticsPage `handleApply()` triggers both `fetchSummary()` and `fetchMerchantBreakdown()` — add `fetchTrend()` and `fetchBurnRate()` to the same handler.
- Trend chart click: use `useNavigate` from `react-router-dom` and construct `/transactions?date_from=X&date_to=Y` URL.
- FilterPanel on TransactionsPage reads URL query params on mount — confirm it supports pre-applied date params from navigation.

</code_context>

<specifics>
## Specific Ideas

- Line chart should feel like a "time story" — smooth area chart with a subtle fill is preferable to bare lines.
- Granularity toggle should make it obvious which one is active (filled/indigo pill, not just underline).
- Burn-rate card: when projected spend exceeds the limit, flip the accent color to red/amber as a warning signal.

</specifics>

<deferred>
## Deferred Ideas

- Per-category monthly budgets (BUDGET-01–04) — too complex for Phase 6; revisit in a dedicated budget phase.
- Monthly savings goals with target tracking (GOAL-01–03) — replaced by simpler spending limit; full goal tracking deferred.
- Trend chart comparison mode (e.g., this month vs last month overlay) — interesting but out of scope.

</deferred>

---

*Phase: 06-analytics-trends*
*Context gathered: 2026-04-29*
