# Phase 7: Pattern Detection & Insights - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 07-pattern-detection-insights
**Areas discussed:** Anomaly detection rules, Recurring charge algorithm, Insights feed content, UI surface

---

## Anomaly Detection Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Large transaction | Amount > N × category monthly average | ✓ |
| Velocity spike | 3+ same-merchant txns in 24h, or 3× daily spend | ✓ |
| New/high-value merchant | Any transaction above a threshold | ✓ |
| Duplicate-like | Same amount + merchant within 48h | ✓ |

**User's choice:** All four rules selected.
**Notes:** Rule 3 clarified — not "first-ever merchant" but ANY transaction above a configurable threshold. Rules must be configurable via a constants file (not hardcoded); no UI needed for MVP. Constants represent thresholds/multipliers; actual "large transaction" baseline is computed from the user's rolling monthly average per category at runtime.

---

## Anomaly DB Schema

| Option | Description | Selected |
|--------|-------------|----------|
| New `anomalies` table, kept until dismissed | Separate table, full status tracking | ✓ |
| Auto-expire after 30 days | Same table but scheduler cleans up after 30 days | |
| Columns on transaction row | is_anomaly + anomaly_reason columns | |

**User's choice:** New `anomalies` table, kept until dismissed.

---

## Recurring Charge Algorithm

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed amount window (±15%) + consecutive months | Same merchant, ≤2 distinct amounts/month, 2+ consecutive months | ✓ |
| Same merchant, any amount | Any merchant in 2+ months | |
| Fixed amount only (±₹50 or ±5%) | Near-identical amounts only | |

**User's choice:** Same merchant in 2+ consecutive months, max 2 distinct amounts per month.
**Notes:** UI term is "Subscriptions" (not "recurring charges"). User can mark a subscription as "canceled" — detection stops until it reappears in 2+ consecutive months, at which point it's re-activated.

---

## Missing Subscription (INS-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Create anomaly row with rule_name='missing_subscription' | Reuses anomaly table | ✓ |
| Separate missing-charge alert list | Separate section | |
| Warning icon on subscriptions list row | Inline warning, no alert | |
| Defer this rule | Skip for now | |

**User's choice:** Anomaly row with `rule_name='missing_subscription'`, with the added condition that users can mark a subscription as canceled to stop tracking.

---

## Subscriptions DB Schema

| Option | Description | Selected |
|--------|-------------|----------|
| New `subscriptions` table | Persistent, supports 'canceled' status | ✓ |
| Compute on the fly | No table, recomputed each time | |

**User's choice:** New `subscriptions` table.

---

## Insights Feed Content

| Option | Description | Selected |
|--------|-------------|----------|
| Category surge | X% more on [Category] vs last month | ✓ |
| Top merchant callout | Top merchant at ₹X (Y% of spend) | ✓ |
| Spend pace warning | On track to exceed last month by Y% | ✓ |
| Quiet month insight | Spending below average — positive signal | ✓ |

**User's choice:** All four types selected.

---

## Insights Regeneration Trigger (INS-08)

| Option | Description | Selected |
|--------|-------------|----------|
| Daily at midnight via scheduler | Nightly job, replaces active insights | |
| After every email sync | Regenerates post-sync (manual + auto) | ✓ |
| Daily + after sync | Both triggers | |

**User's choice:** After every email sync.

---

## UI Surface

| Option | Description | Selected |
|--------|-------------|----------|
| New 'Insights' nav page | One page: Alerts + Subscriptions + Feed | ✓ |
| Embedded across existing pages | No new nav item | |
| Insights page + dashboard widget | New page + summary card on Transactions | |

**User's choice:** New `/insights` page with three stacked sections. Nav badge shows unreviewed anomaly count.

---

## Claude's Discretion

- Severity mapping for anomaly rules (e.g., `duplicate_like` = high)
- Visual styling of alert severity (colors, icons)
- Exact wording for insight titles and body copy

## Deferred Ideas

- Settings UI for anomaly thresholds — edit `insights_config.py` directly for MVP
- LLM-powered insight generation (AI-01) — post-v2
- Push/email notifications for anomalies — in-app only for v1
