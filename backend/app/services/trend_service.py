"""
TrendService — time-series aggregation for the analytics trend endpoint.
Phase 6, Plan 01 — ANA-03, ANA-04, ANA-05, ANA-06
"""
import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


# ---------------------------------------------------------------------------
# Granularity format strings (SQLite strftime)
# ---------------------------------------------------------------------------

GRANULARITY_FORMAT: dict[str, str] = {
    "daily":   "%Y-%m-%d",
    "weekly":  "%Y-W%W",
    "monthly": "%Y-%m",
    "annual":  "%Y",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _period_boundaries(
    granularity: str,
    period_key: str,
    min_date: date,
    max_date: date,
) -> tuple[date, date]:
    """Return true calendar start/end for the period.

    For weekly granularity we use data-driven bounds to avoid the SQLite %W vs
    ISO week mismatch (Pitfall 2 from RESEARCH.md).
    """
    if granularity == "daily":
        d = date.fromisoformat(period_key)
        return d, d

    elif granularity == "weekly":
        # Start = Monday of the week containing min_date
        start = min_date - timedelta(days=min_date.weekday())
        end = start + timedelta(days=6)
        return start, end

    elif granularity == "monthly":
        year_str, month_str = period_key.split("-")
        y, m = int(year_str), int(month_str)
        start = date(y, m, 1)
        last_day = calendar.monthrange(y, m)[1]
        end = date(y, m, last_day)
        return start, end

    elif granularity == "annual":
        y = int(period_key)
        return date(y, 1, 1), date(y, 12, 31)

    else:
        raise ValueError(f"Unknown granularity: {granularity}")


def _period_label(granularity: str, period_start: date, period_key: str) -> str:
    """Human-readable label for the period."""
    if granularity == "daily":
        return period_start.strftime("%b %d")       # "Apr 15"
    elif granularity == "weekly":
        return f"Wk {period_start.strftime('%b %d')}"  # "Wk Apr 13"
    elif granularity == "monthly":
        return period_start.strftime("%b %Y")       # "Apr 2026"
    elif granularity == "annual":
        return period_key                            # "2026"
    else:
        raise ValueError(f"Unknown granularity: {granularity}")


# ---------------------------------------------------------------------------
# TrendService
# ---------------------------------------------------------------------------

class TrendService:

    def get_trend(
        self,
        db: Session,
        user_id: int,
        granularity: Literal["daily", "weekly", "monthly", "annual"],
        date_from: Optional[date],
        date_to: Optional[date],
        payment_source: Optional[str],
    ) -> dict:
        """
        Aggregate transactions into time-series periods.

        Returns a dict with keys:
          trend            — list of period dicts (TrendItem-compatible)
          granularity      — echoed back
          current_total    — sum of all amounts in the requested range
          previous_total   — sum for the equivalent prior period
          pct_change       — percentage change (None when previous_total == 0)
        """
        if granularity not in GRANULARITY_FORMAT:
            raise ValueError(
                f"granularity must be one of {list(GRANULARITY_FORMAT.keys())}"
            )

        fmt = GRANULARITY_FORMAT[granularity]

        # ------------------------------------------------------------------
        # Build base filtered query
        # ------------------------------------------------------------------
        base = db.query(Transaction).filter(Transaction.user_id == user_id)
        if date_from:
            base = base.filter(Transaction.transaction_date >= date_from)
        if date_to:
            base = base.filter(Transaction.transaction_date <= date_to)
        if payment_source:
            base = base.filter(Transaction.payment_source == payment_source)

        # ------------------------------------------------------------------
        # Main aggregation query — one row per period
        # ------------------------------------------------------------------
        period_key_col = func.strftime(fmt, Transaction.transaction_date).label("period_key")

        rows = (
            base.with_entities(
                period_key_col,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
                func.min(Transaction.transaction_date).label("min_date"),
                func.max(Transaction.transaction_date).label("max_date"),
            )
            .group_by(func.strftime(fmt, Transaction.transaction_date))
            .order_by(func.strftime(fmt, Transaction.transaction_date))
            .all()
        )

        # ------------------------------------------------------------------
        # Category totals — second pass grouped by (period_key, category)
        # ------------------------------------------------------------------
        cat_rows = (
            base.with_entities(
                func.strftime(fmt, Transaction.transaction_date).label("period_key"),
                Transaction.category,
                func.sum(Transaction.amount).label("cat_total"),
            )
            .group_by(
                func.strftime(fmt, Transaction.transaction_date),
                Transaction.category,
            )
            .all()
        )

        # Build nested dict: period_key -> {category: float}
        cat_totals_map: dict[str, dict[str, float]] = {}
        for crow in cat_rows:
            pk = crow.period_key
            if pk not in cat_totals_map:
                cat_totals_map[pk] = {}
            cat_totals_map[pk][crow.category] = float(crow.cat_total)

        # ------------------------------------------------------------------
        # Build trend items
        # ------------------------------------------------------------------
        trend: list[dict] = []
        for row in rows:
            pk: str = row.period_key
            # SQLite may return date as string or date object — normalise
            min_d = (
                row.min_date
                if isinstance(row.min_date, date)
                else date.fromisoformat(str(row.min_date))
            )
            max_d = (
                row.max_date
                if isinstance(row.max_date, date)
                else date.fromisoformat(str(row.max_date))
            )

            p_start, p_end = _period_boundaries(granularity, pk, min_d, max_d)
            label = _period_label(granularity, p_start, pk)

            trend.append({
                "period_label":    label,
                "period_start":    p_start,
                "period_end":      p_end,
                "total":           float(row.total),
                "count":           row.count,
                "category_totals": cat_totals_map.get(pk, {}),
            })

        # ------------------------------------------------------------------
        # Compute current_total and previous_total
        # ------------------------------------------------------------------
        current_total: float = sum(item["total"] for item in trend)

        previous_total: float = 0.0
        if date_from and date_to:
            delta = (date_to - date_from) + timedelta(days=1)
            prev_to = date_from - timedelta(days=1)
            prev_from = prev_to - delta + timedelta(days=1)

            prev_query = (
                db.query(Transaction)
                .filter(Transaction.user_id == user_id)
                .filter(Transaction.transaction_date >= prev_from)
                .filter(Transaction.transaction_date <= prev_to)
            )
            if payment_source:
                prev_query = prev_query.filter(
                    Transaction.payment_source == payment_source
                )

            prev_sum = prev_query.with_entities(
                func.sum(Transaction.amount)
            ).scalar()
            previous_total = float(prev_sum) if prev_sum is not None else 0.0

        pct_change = self.compute_pct_change(current_total, previous_total)

        return {
            "trend":          trend,
            "granularity":    granularity,
            "current_total":  current_total,
            "previous_total": previous_total,
            "pct_change":     pct_change,
        }

    def compute_pct_change(self, current: float, previous: float) -> Optional[float]:
        """Return percentage change, or None when previous == 0 (avoid div-by-zero)."""
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 2)


trend_service = TrendService()
