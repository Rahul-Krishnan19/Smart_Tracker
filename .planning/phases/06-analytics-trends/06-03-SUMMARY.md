---
phase: 06-analytics-trends
plan: 03
subsystem: ui
tags: [react, recharts, date-fns, react-router-dom, react-hook-form, analytics]

# Dependency graph
requires:
  - phase: 06-01
    provides: GET /api/analytics/trend endpoint with category_totals and pct_change
  - phase: 06-02
    provides: GET/PUT/DELETE /api/analytics/spending-limit endpoints

provides:
  - TrendChart component with click-to-navigate and category overlay stacked Areas
  - GranularityToggle pill-style component [Daily | Weekly | Monthly | Annual]
  - BurnRateCard with frontend-computed projection and always-editable spending-limit input
  - AnalyticsPage extended with trend section above existing pie + bar charts
  - TransactionsPage URL-param seeding so /transactions?date_from=X&date_to=Y pre-fills FilterPanel
  - analyticsApi client namespace in api.js (trend, getSpendingLimit, putSpendingLimit, deleteSpendingLimit)

affects: [07-insights]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frontend-computed burn-rate projection: (spent / days_elapsed) * total_days keeps backend simple"
    - "useSearchParams for URL-param seeding on mount: stable initialFilters via useState(() => {...})"
    - "defaultValues prop on react-hook-form pre-fills controlled date inputs from parent state"
    - "Recharts category overlay via stackId='categories' — chartData flattens category_totals per point"

key-files:
  created:
    - frontend/src/components/analytics/TrendChart.jsx
    - frontend/src/components/analytics/GranularityToggle.jsx
    - frontend/src/components/analytics/BurnRateCard.jsx
  modified:
    - frontend/src/services/api.js
    - frontend/src/pages/AnalyticsPage.jsx
    - frontend/src/pages/TransactionsPage.jsx
    - frontend/src/components/transactions/FilterPanel.jsx

key-decisions:
  - "Burn-rate computed on frontend: backend trend response has current_total; frontend divides by days_elapsed and projects to period_end"
  - "useSearchParams initial value in useState lazy initializer: avoids re-seeding on re-render"
  - "analyticsApi as separate export namespace (not merged into transactionsApi): different route prefix /api/analytics"
  - "GranularityToggle emits onChange immediately; AnalyticsPage useEffect([granularity]) refetches trend"

requirements-completed: [ANA-03, ANA-04, ANA-05, ANA-06, GOAL-02]

# Metrics
duration: ~15min
completed: 2026-04-29
---

# Phase 6 Plan 03: Analytics Frontend — Trend Chart, Burn-Rate Card, Click-Through Summary

**Recharts AreaChart trend chart on /analytics with granularity toggle, category overlay, pct_change badge, burn-rate projection card with spending-limit input, and /transactions click-through that pre-fills FilterPanel from URL params**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-29T00:00:00Z
- **Completed:** 2026-04-29
- **Tasks:** 2 complete + 1 checkpoint (Task 3: human verify pending)
- **Files modified:** 7

## Accomplishments
- TrendChart: Recharts AreaChart with click-to-navigate (period_start/period_end), category overlay via stackId, and empty-state branch
- GranularityToggle: pill-style toggle [daily/weekly/monthly/annual] with active indigo styling
- BurnRateCard: frontend-computed burn-rate projection; spending-limit input PUTs on blur/Enter, DELETEs on clear; red accent when projected > limit
- AnalyticsPage: trend section with pct_change badge, granularity refetch effect, all wired above existing charts
- TransactionsPage + FilterPanel: URL param seeding so chart click-throughs land on pre-filtered list

## Task Commits

1. **Task 1: API client methods + GranularityToggle + TrendChart** - `5ef509e` (feat)
2. **Task 2: BurnRateCard + AnalyticsPage integration + URL-param seeding** - `307bd5a` (feat)
3. **Task 3: Manual verification** - pending checkpoint

## Component Contracts

### TrendChart
```jsx
<TrendChart
  data={Array<{period_label, period_start, period_end, total, category_totals}>}
  categoryOverlay={boolean}  // default false
/>
```
Click on any area point navigates to `/transactions?date_from=X&date_to=Y`.

### GranularityToggle
```jsx
<GranularityToggle
  value={'daily'|'weekly'|'monthly'|'annual'}
  onChange={(g: string) => void}
/>
```
Also exports `GRANULARITIES` array.

### BurnRateCard
```jsx
<BurnRateCard
  granularity={'daily'|'weekly'|'monthly'|'annual'}
  dateFrom={'YYYY-MM-DD'}
  dateTo={'YYYY-MM-DD'}
  currentTotal={number}
/>
```
Internally fetches/saves spending limit for the given granularity. Shows projection when range includes today, "Actual" when range is fully past.

## Files Created/Modified
- `frontend/src/services/api.js` - Added analyticsApi export with trend/getSpendingLimit/putSpendingLimit/deleteSpendingLimit
- `frontend/src/components/analytics/TrendChart.jsx` - AreaChart with click-through, category overlay
- `frontend/src/components/analytics/GranularityToggle.jsx` - Pill-style toggle
- `frontend/src/components/analytics/BurnRateCard.jsx` - Burn-rate KPI + spending-limit input
- `frontend/src/pages/AnalyticsPage.jsx` - Trend section above existing charts; granularity state + effects
- `frontend/src/pages/TransactionsPage.jsx` - useSearchParams, initialFilters state, defaultValues prop pass
- `frontend/src/components/transactions/FilterPanel.jsx` - defaultValues prop + useForm({ defaultValues })

## Decisions Made
- Burn-rate computed on frontend (not backend): backend already returns `current_total`; projection = `currentTotal / daysElapsed * totalDays`. Keeps backend simple and projection stays in sync with visible date range.
- `initialFilters` seeded in `useState(() => {...})` lazy initializer: reads `searchParams` once at mount, stable reference for `useCallback` dependencies.
- `analyticsApi` is a separate named export (not merged into `transactionsApi`) because route prefix is `/api/analytics`.
- `GranularityToggle` fires `onChange` synchronously; parent `AnalyticsPage` uses `useEffect([granularity])` to refetch trend immediately.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- ESLint global config (`C:\Users\rahul\eslint.config.mjs`) imports `eslint-config-next` which is not installed in this project, causing `npm run lint` to fail with `ERR_MODULE_NOT_FOUND`. This is a pre-existing environment issue (global Next.js ESLint config picked up by a non-Next project). Verified code correctness via `npm run build` instead (Vite build exits 0, 1028 modules transformed).

## Known Stubs
None — all components are wired to live API endpoints.

## Manual Verification Result
Task 3 (checkpoint:human-verify) pending — user has not yet confirmed.

## Next Phase Readiness
- Phase 6 frontend complete pending human verification (Task 3)
- Phase 7 (insights/anomaly detection) can begin after Task 3 PASS

## Self-Check: PASSED
- BurnRateCard.jsx: FOUND
- TrendChart.jsx: FOUND
- GranularityToggle.jsx: FOUND
- Commit 307bd5a (Task 2): FOUND
- Commit 5ef509e (Task 1): FOUND

---
*Phase: 06-analytics-trends*
*Completed: 2026-04-29 (Tasks 1-2 done; Task 3 human verify pending)*
