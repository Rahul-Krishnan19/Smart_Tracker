# Phase 6: Analytics & Trends - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 06-analytics-trends
**Areas discussed:** Page structure, Trend chart type, Click behavior, Burn-rate projection, Spending limit UX, Granularity toggle

---

## Page Structure / Chart Type

| Option | Description | Selected |
|--------|-------------|----------|
| Extend Analytics page | Add trend chart to existing page | ✓ |
| New Trends tab/page | New nav item separate from Analytics | |

**User's choice:** Extend existing Analytics page. Also clarified: line chart (not bar), budgets entirely out of scope for this phase.

---

## Trend Chart Click Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Navigate to Transactions | Opens /transactions with date filters pre-applied | ✓ |
| Highlight only | Visual highlight, no navigation | |
| Skip — no click behavior | Read-only chart | |

**User's choice:** Navigate to /transactions with date filters.

---

## Burn-Rate Projection

| Option | Description | Selected |
|--------|-------------|----------|
| Projected end-of-period total | "At this rate: ₹X by month-end" | ✓ |
| Daily allowance remaining | "₹X/day left to stay on track" | |
| Both | Projected total + daily allowance | |

**User's choice:** Projected end-of-period total. Also: user can set a spending limit inline on the Analytics page, persisted per granularity to DB.

---

## Spending Limit UX

| Option | Description | Selected |
|--------|-------------|----------|
| Inline on Analytics page | Editable field next to burn-rate card | ✓ |
| Single global limit | One limit for all granularities | |

**User's choice:** Inline, per-granularity (separate limits for Daily/Weekly/Monthly/Annual).

---

## Granularity Toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Button group | Pill-style toggle buttons | ✓ |
| Dropdown select | Select element | |

**User's choice:** Pill-style button group.

---

## Claude's Discretion

- Visual style of trend line (smooth vs straight, area fill vs bare line)
- Empty state for trend chart
- Spending limit edit trigger (click-to-edit vs always-visible input)

## Deferred Ideas

- Per-category monthly budgets (BUDGET-01–04)
- Savings goals (GOAL-01–03)
- Trend comparison mode (this month vs last month)
