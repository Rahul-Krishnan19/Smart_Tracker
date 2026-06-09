# Phase 7: Pattern Detection & Insights - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a new "Insights" page (new nav item) with three sections: anomaly alerts, subscriptions list, and a daily insights feed. All backed by DB-cached results so nothing is recomputed on every page load. Insights regenerate after every email sync (manual or scheduled).

Per-category monthly budgets and savings goals remain deferred (Phase 6 scope decision).

</domain>

<decisions>
## Implementation Decisions

### Anomaly Detection

- **D-01:** Four anomaly rules, all active:
  1. `large_transaction` — amount exceeds `ANOMALY_LARGE_TX_MULTIPLIER` × user's rolling monthly average for that category
  2. `high_value` — any single transaction above `ANOMALY_HIGH_VALUE_THRESHOLD` (regardless of merchant or category)
  3. `velocity_spike` — 3+ transactions at the same merchant within `ANOMALY_VELOCITY_WINDOW_HOURS` hours, OR daily total spend exceeds `ANOMALY_DAILY_SPEND_MULTIPLIER` × rolling daily average
  4. `duplicate_like` — same merchant + amount within `ANOMALY_DUPLICATE_WINDOW_HOURS` hours

- **D-02:** Anomaly rules are configurable via a Python constants file (e.g., `backend/app/services/insights_config.py`). All thresholds live there as module-level constants — no logic changes needed to adjust thresholds. The `large_transaction` baseline is computed from the user's actual rolling monthly average per category (not a hardcoded value). Suggested defaults:
  - `ANOMALY_LARGE_TX_MULTIPLIER = 3.0`
  - `ANOMALY_HIGH_VALUE_THRESHOLD = 5000`  (₹5,000)
  - `ANOMALY_VELOCITY_WINDOW_HOURS = 24`
  - `ANOMALY_VELOCITY_MIN_COUNT = 3`
  - `ANOMALY_DAILY_SPEND_MULTIPLIER = 3.0`
  - `ANOMALY_DUPLICATE_WINDOW_HOURS = 48`
  - `ANOMALY_MIN_HISTORY_MONTHS = 2`  (need ≥2 months of history to compute averages)

- **D-03:** Anomaly detection runs after every sync (both manual `/api/gmail/sync` and scheduler `sync_user_emails()`). New anomalies are appended; existing open anomalies are not re-flagged.

- **D-04:** DB schema — new `anomalies` table:
  ```
  id              INTEGER PK
  user_id         FK → users (CASCADE delete)
  transaction_id  FK → transactions (CASCADE delete)
  rule_name       VARCHAR(50)   -- 'large_transaction' | 'high_value' | 'velocity_spike' | 'duplicate_like' | 'missing_subscription'
  severity        VARCHAR(20)   -- 'low' | 'medium' | 'high'
  status          VARCHAR(20)   -- 'new' | 'dismissed' | 'investigating'
  detected_at     DATETIME
  dismissed_at    DATETIME      -- nullable
  notes           TEXT          -- optional user note
  ```

- **D-05:** INS-02 alerts badge — shows count of `status='new'` anomalies on the Insights nav item.

- **D-06:** INS-03 user actions — dismiss (sets `status='dismissed'`, records `dismissed_at`) or mark as investigating (sets `status='investigating'`). Backend: `PATCH /api/insights/anomalies/{id}` `{status}`.

### Subscriptions (Recurring Charge Detection)

- **D-07:** Subscription detection algorithm:
  - Same merchant appearing in **2+ consecutive calendar months**
  - Max **2 distinct payment amounts** per month for that merchant (filters out habits like Swiggy with many varying amounts)
  - UI term: **"Subscriptions"** (not "recurring charges")

- **D-08:** Detection runs after every sync (same trigger as anomaly detection). Re-evaluates all merchants for the user.

- **D-09:** DB schema — new `subscriptions` table:
  ```
  id                INTEGER PK
  user_id           FK → users (CASCADE delete)
  merchant          VARCHAR(255)
  typical_amount    NUMERIC(10,2)   -- median of seen amounts
  status            VARCHAR(20)     -- 'active' | 'canceled'
  first_seen_month  DATE            -- YYYY-MM-01
  last_seen_month   DATE            -- most recent month with a charge
  canceled_at       DATETIME        -- nullable
  ```
  Unique constraint on `(user_id, merchant)`.

- **D-10:** INS-06 missing subscription — if a subscription is `active` and no charge has appeared from that merchant in the current calendar month (and we're past day 25 of the month), create an anomaly row with `rule_name='missing_subscription'` pointing to `transaction_id=NULL`.

- **D-11:** User can mark a subscription as `canceled` via the UI. Once canceled:
  - No longer tracked / no missing-charge alerts generated
  - If the merchant reappears in 2+ consecutive months in the future, the detection re-activates it (sets `status='active'` again, clears `canceled_at`)

### Insights Feed

- **D-12:** Four insight types (up to 5 shown per user per sync, priority ordered):
  1. `spend_pace` — "You've spent ₹X this month — on track to exceed last month by Y%" (links to burn-rate from Phase 6)
  2. `category_surge` — "You spent X% more on [Category] this month vs last month" (per category, highest surge first)
  3. `top_merchant` — "Your top merchant this month is [Merchant] at ₹X (Y% of total)"
  4. `quiet_month` — "Your spending is 30% below your monthly average — great month!" (shown when on-pace is below average, not when warning)

- **D-13:** Some insight types can fire multiple times in one batch (e.g., three categories all surged → three `category_surge` rows). When the total candidates exceed 5, keep insights in this priority order and drop from the bottom:

  ```
  1. spend_pace       (max 1)
  2. category_surge   (as many as qualify, highest % surge first)
  3. top_merchant     (max 1)
  4. quiet_month      (max 1)
  ```

  Example — 6 candidates, cap is 5:
  - spend_pace (April pace: +30% vs March) ← kept
  - category_surge: Food & Dining +45%     ← kept
  - category_surge: Shopping +30%          ← kept
  - category_surge: Travel +20%            ← kept
  - top_merchant: Swiggy ₹4,200            ← kept
  - quiet_month                            ← DROPPED (lowest priority, already at 5)

  `spend_pace` and `quiet_month` are mutually exclusive — `spend_pace` fires when you're spending *above* your normal pace; `quiet_month` fires when you're spending *below* it. They can never both be true, so at most one of the two appears in any given batch.

- **D-14:** Regeneration trigger: after every sync. Delete all `status='active'` insights for the user, compute fresh set, insert up to 5. `status='dismissed'` rows are preserved (history).

- **D-15:** DB schema — new `insights` table:
  ```
  id              INTEGER PK
  user_id         FK → users (CASCADE delete)
  insight_type    VARCHAR(50)   -- 'spend_pace' | 'category_surge' | 'top_merchant' | 'quiet_month'
  title           VARCHAR(255)  -- short human-readable headline
  body            TEXT          -- supporting detail (amounts, percentages, merchant name)
  status          VARCHAR(20)   -- 'active' | 'dismissed'
  generated_at    DATETIME
  dismissed_at    DATETIME      -- nullable
  ```

### UI Surface

- **D-16:** New `/insights` page with three sections stacked vertically:
  1. **Alerts** — anomaly cards, each showing transaction detail, rule name, dismiss/investigate actions
  2. **Subscriptions** — table of detected subscriptions with merchant, typical amount, estimated monthly total, cancel action; missing-charge anomalies surfaced inline
  3. **Insights feed** — up to 5 insight cards, each dismissible

- **D-17:** New "Insights" nav item in the top navigation with an unread badge (count of `status='new'` anomalies). Badge disappears when all anomalies are dismissed or marked investigating.

- **D-18:** Clicking an anomaly that has a linked transaction navigates to `/transactions` with that transaction highlighted (or at minimum, filtered to that date).

### Scheduler Integration

- **D-19:** Insights and anomaly detection are triggered as a **post-sync step** inside `email_sync_service.sync()` (or called from `scheduler.sync_user_emails()` after `email_sync_service.sync()` completes). No separate scheduled job needed — piggybacks on the existing sync trigger.

### Insights Extensibility

- **D-20:** `InsightService` uses a **generator registry** pattern. Each insight type is a private `_generate_<type>(self, db, user_id, ctx)` method returning `list[tuple[type, title, body, sort_key]]`. A module-level `_GENERATORS` list of `(insight_type, method_name)` pairs registers them. **Adding a new insight type = one new method + one line in `_GENERATORS` + one entry appended to `INSIGHT_PRIORITY_ORDER` in `insights_config.py`.** No changes to `regenerate()` needed. The cap (`INSIGHTS_MAX_PER_BATCH = 5`) is also in config — increase it to show more.

### Claude's Discretion

- Severity mapping for anomaly rules (which rule → which severity level) — Claude decides sensible defaults (e.g., `duplicate_like` = high, `large_transaction` = medium, `velocity_spike` = medium, `high_value` varies by amount multiple)
- Visual styling of the Insights page sections (card styles, colors for alert severity)
- Exact wording of insight titles and body copy

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing scheduler
- `backend/app/scheduler.py` — APScheduler BackgroundScheduler; `sync_user_emails()` is where post-sync hooks should be added. Follow the existing pattern for session management (`with SessionLocal() as db`).

### Existing sync service
- `backend/app/services/email_sync_service.py` — `sync()` is the entry point for both manual and scheduled sync. Post-sync insights/anomaly computation hooks here.

### Existing transaction model & service
- `backend/app/models/transaction.py` — Transaction ORM; anomaly detection queries run against this table
- `backend/app/services/transaction_service.py` — `_build_filter_query()` helper for any queries that need user/date filtering

### Frontend routing & nav
- `frontend/src/App.jsx` — React Router setup; add `/insights` route here
- The top nav component (Layout) — add "Insights" nav item with badge

### Requirements
- `.planning/REQUIREMENTS.md` — INS-01 through INS-08

### No external specs — all requirements captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `APScheduler BackgroundScheduler` in `scheduler.py` — post-sync hook follows `sync_user_emails()` pattern (open session, call service, commit, log errors without re-raising)
- `get_current_user()` in `auth.py` — reuse as FastAPI `Depends` for all new `/api/insights/*` routes
- `SessionLocal` context manager — all new DB-touching scheduler/service functions use `with SessionLocal() as db`
- `Alembic` — 3 new tables (`anomalies`, `subscriptions`, `insights`) each need their own migration or one combined migration
- `formatINR()` pattern from AnalyticsPage — reuse for all currency display in insights cards
- `date-fns` already in frontend — use for period label formatting in insight copy

### Established Patterns
- Service layer singleton pattern: `insights_service = InsightsService()` at module level
- Route handler: thin — call service, serialize, return Response
- Card-based UI with `className="card"` — all new page sections follow this
- All new DB tables via Alembic migration (not `Base.metadata.create_all`)
- Error handling in scheduler jobs: wrap in try/except, log error, never re-raise

### Integration Points
- `email_sync_service.sync()` — add call to `insights_service.run_post_sync(db, user_id)` at the end of a successful sync
- `App.jsx` — add `<Route path="/insights" element={<ProtectedRoute><Layout><InsightsPage /></Layout></ProtectedRoute>} />`
- Top nav / Layout component — add "Insights" link with badge count from a new `GET /api/insights/summary` endpoint
- `scheduler.sync_user_emails()` — alternatively call `insights_service.run_post_sync()` here after `email_sync_service.sync()` returns

</code_context>

<specifics>
## Specific Implementation Notes

- **Anomaly config file:** `backend/app/services/insights_config.py` — all constants defined at module level. Import in the detection service. No `.env` changes needed (these are logic thresholds, not secrets).
- **Subscription detection timing:** After each sync, re-run detection for the syncing user only. No need to re-scan all users.
- **Missing subscription check:** Only trigger after day 10 of the calendar month (avoids false alerts at the start of the month when the charge simply hasn't arrived yet).
- **Insights priority:** `spend_pace` and `quiet_month` are mutually exclusive — show `quiet_month` only when monthly spend is ≥20% below the rolling average, otherwise show `spend_pace` if applicable.
- **Badge count:** `GET /api/insights/summary` returns `{ anomaly_count: N }` — frontend polls this or fetches on nav load.

</specifics>

<deferred>
## Deferred Ideas

- UI for editing anomaly rule thresholds — users can edit `insights_config.py` directly for now; a Settings UI for thresholds is a future phase
- LLM-powered insight generation (AI-01) — schema is designed to be compatible; rule-based first per PROJECT.md
- Per-category budget alerts as anomalies — deferred until per-category budgets are implemented (Phase 6 deferred them too)
- Push/email notifications for anomalies — in-app only for v1 per PROJECT.md

</deferred>

---

*Phase: 07-pattern-detection-insights*
*Context gathered: 2026-04-29*
