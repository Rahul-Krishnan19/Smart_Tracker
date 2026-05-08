---
phase: 07-pattern-detection-insights
plan: 03
subsystem: frontend-insights
tags: [insights-ui, anomaly-cards, subscriptions-table, insights-feed, nav-badge, react-router]
dependency_graph:
  requires: [07-02]
  provides: [/insights-page, InsightsBadge, insightsApi, AlertsSection, SubscriptionsSection, InsightsFeedSection]
  affects: [App.jsx, api.js]
tech_stack:
  added: []
  patterns: [useCallback-refresh, section-components, nav-badge-polling]
key_files:
  created:
    - frontend/src/services/api.js (insightsApi namespace appended)
    - frontend/src/components/insights/AlertsSection.jsx
    - frontend/src/components/insights/SubscriptionsSection.jsx
    - frontend/src/components/insights/InsightsFeedSection.jsx
    - frontend/src/components/insights/InsightsBadge.jsx
    - frontend/src/pages/InsightsPage.jsx
  modified:
    - frontend/src/App.jsx
decisions:
  - "insightsApi uses axios instance (not apiFetch) matching existing transactionsApi/analyticsApi pattern"
  - "InsightsBadge fetches getSummary on mount only (no polling interval) — badge updates after full page navigation"
  - "AlertsSection filters status!=new client-side — avoids extra endpoint; all anomalies fetched once per refresh"
  - "InsightsFeedSection shows only status=active insights (client-side filter) — dismissed rows excluded from view"
metrics:
  duration: 10min
  completed: "2026-05-08"
  tasks: 2
  files: 7
---

# Phase 7 Plan 03: Insights Frontend UI Summary

**One-liner:** /insights page with three stacked sections (Alerts, Subscriptions, Insights feed), nav badge from anomaly count, and click-through from anomaly cards to /transactions?tx_id=.

## What Was Built

### API Client Extension

`insightsApi` namespace appended to `frontend/src/services/api.js`:

| Method | Endpoint |
|--------|----------|
| `getAnomalies()` | GET /api/insights/anomalies |
| `updateAnomaly(id, status)` | PATCH /api/insights/anomalies/{id} |
| `getSubscriptions()` | GET /api/insights/subscriptions |
| `updateSubscription(id, status)` | PATCH /api/insights/subscriptions/{id} |
| `getInsights()` | GET /api/insights/insights |
| `dismissInsight(id)` | POST /api/insights/insights/{id}/dismiss |
| `getSummary()` | GET /api/insights/summary |

### Components

**AlertsSection** (`props: { anomalies, onUpdate }`)
- Filters `status === 'new'` client-side
- Severity pill: high=red, medium=amber, low=gray
- Two action buttons: Dismiss (sets `dismissed`) + Investigate (sets `investigating`)
- Cards with non-null `transaction_id` are clickable and navigate to `/transactions?tx_id={id}` via `useNavigate` (D-18)
- Empty state: "No alerts — your spending looks normal."

**SubscriptionsSection** (`props: { data, onUpdate }`)
- Table: Merchant | Typical Amount | First Seen | Last Seen | Status | Action
- Subhead shows estimated_monthly_total in INR format
- Active rows: "Cancel" button → PATCH status=canceled
- Canceled rows: "Reactivate" button → PATCH status=active
- Empty state: "No subscriptions detected yet — keep syncing emails."

**InsightsFeedSection** (`props: { insights, onUpdate }`)
- Filters `status === 'active'` and caps at 5 cards
- Each card has title + body + × dismiss button
- Empty state: "Nothing to highlight today."

**InsightsBadge** (standalone, used in nav)
- Fetches `getSummary()` on mount
- Renders red pill `<span>` with count when `anomaly_count > 0`
- Returns null when count is 0 (badge disappears)
- Supports 99+ capping

**InsightsPage** (orchestrator)
- `useCallback` `refresh()` fetches all 3 endpoints in parallel via `Promise.all`
- Passed as `onUpdate` to all 3 sections — any action triggers full refetch
- Loading state shown until first fetch resolves

### Navigation

`App.jsx` changes:
- Insights NavLink added after Analytics in `<nav className="flex gap-1">`
- `<InsightsBadge />` inlined inside the NavLink
- `/insights` route added before catch-all, wrapped in `ProtectedRoute` + `Layout`

## How Badge Updates

The badge fetches once on mount. After a dismiss/investigate action in AlertsSection, `onUpdate()` triggers a full page re-fetch but does NOT re-mount InsightsBadge (it's in Layout). Badge count will decrement on next navigation or page reload. To update badge immediately after dismiss, a global state or context would be needed — deferred for now.

## Click-Through Pattern

`AlertsSection` uses `useNavigate()` from react-router. Cards where `anomaly.transaction_id !== null` receive `onClick={() => navigate('/transactions?tx_id=' + transaction_id)}` on the card container. The action buttons use `e.stopPropagation()` so clicking Dismiss/Investigate doesn't trigger navigation.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All 7 API methods are wired to real Plan 02 endpoints.

## Self-Check: PASSED

Files verified:
- frontend/src/services/api.js — insightsApi present (FOUND)
- frontend/src/pages/InsightsPage.jsx — FOUND
- frontend/src/components/insights/AlertsSection.jsx — FOUND
- frontend/src/components/insights/SubscriptionsSection.jsx — FOUND
- frontend/src/components/insights/InsightsFeedSection.jsx — FOUND
- frontend/src/components/insights/InsightsBadge.jsx — FOUND
- frontend/src/App.jsx — updated (FOUND)

Commits verified:
- b3e6430 — feat(07-03): insightsApi + sections + InsightsPage
- eab87ce — feat(07-03): InsightsBadge + /insights route in App.jsx

## Checkpoint: Awaiting Human Verification

Task 3 is a `checkpoint:human-verify` — manual testing required before plan is marked complete.
