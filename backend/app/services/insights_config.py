"""Phase 07 — Anomaly + insights detection thresholds (D-02).
Edit values here to adjust detection sensitivity. No code changes elsewhere required.
"""
from decimal import Decimal

# --- Anomaly thresholds ---
ANOMALY_LARGE_TX_MULTIPLIER: float = 3.0
ANOMALY_HIGH_VALUE_THRESHOLD: Decimal = Decimal("5000")
ANOMALY_VELOCITY_WINDOW_HOURS: int = 24
ANOMALY_VELOCITY_MIN_COUNT: int = 3
ANOMALY_DAILY_SPEND_MULTIPLIER: float = 3.0
ANOMALY_DUPLICATE_WINDOW_HOURS: int = 48
ANOMALY_MIN_HISTORY_MONTHS: int = 2

# --- Subscription detection (D-07) ---
SUBSCRIPTION_MIN_CONSECUTIVE_MONTHS: int = 2
SUBSCRIPTION_MAX_DISTINCT_AMOUNTS_PER_MONTH: int = 2

# --- Missing-subscription anomaly trigger (specifics, day-of-month gate) ---
MISSING_SUBSCRIPTION_TRIGGER_DAY: int = 10  # only fire after this day-of-month (D-10)

# --- Insights feed (D-12, D-13, D-20) ---
INSIGHTS_MAX_PER_BATCH: int = 5
QUIET_MONTH_BELOW_AVG_THRESHOLD: float = 0.20  # >=20% below avg -> quiet_month per specifics

# Priority order for the generator registry in InsightService (D-20).
# To add a new insight type: (1) add a _generate_<type> method to InsightService,
# (2) append its insight_type string here. Lower index = higher priority.
INSIGHT_PRIORITY_ORDER: list[str] = [
    "spend_pace",
    "category_surge",
    "top_merchant",
    "quiet_month",
]

# --- Severity mapping (Claude's discretion per CONTEXT) ---
ANOMALY_SEVERITY = {
    "duplicate_like": "high",
    "high_value": "high",
    "large_transaction": "medium",
    "velocity_spike": "medium",
    "missing_subscription": "low",
}
