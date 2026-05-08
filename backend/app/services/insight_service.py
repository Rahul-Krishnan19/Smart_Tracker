"""Insights feed regeneration — D-12 types, D-13 priority cap, D-14 active-only delete."""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.insight import Insight
from app.models.transaction import Transaction
from app.services import insights_config as cfg

# Generator registry (D-20). Each entry: (insight_type, generator_method_name).
# Priority is controlled by cfg.INSIGHT_PRIORITY_ORDER — not this list.
# To add a new insight type:
#   1. Add a _generate_<type>(self, db, user_id, ctx) -> list[tuple[str,str,str,float]] method
#   2. Register it here: _GENERATORS.append(("my_type", "_generate_my_type"))
#   3. Append "my_type" to INSIGHT_PRIORITY_ORDER in insights_config.py
# No changes to regenerate() are needed.
_GENERATORS: list[tuple[str, str]] = [
    ("spend_pace",     "_generate_spend_pace"),
    ("quiet_month",    "_generate_quiet_month"),
    ("category_surge", "_generate_category_surge"),
    ("top_merchant",   "_generate_top_merchant"),
]


class InsightService:
    def regenerate(self, db: Session, user_id: int, today: datetime | None = None) -> List[Insight]:
        today = today or datetime.utcnow()
        # D-14: delete active insights only, preserve dismissed
        db.query(Insight).filter(
            Insight.user_id == user_id, Insight.status == "active"
        ).delete(synchronize_session=False)

        # Shared context computed once and passed to each generator
        month_start = date(today.year, today.month, 1)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        this_month_total = self._sum_in_range(db, user_id, month_start, today.date() + timedelta(days=1))
        ctx = {
            "today": today,
            "month_start": month_start,
            "prev_month_start": prev_month_start,
            "this_month_total": this_month_total,
        }

        # Collect candidates from every registered generator
        # Each generator returns list[tuple[str, str, str, float]] = [(type, title, body, sort_key)]
        raw_candidates: list[tuple[str, str, str, float]] = []
        for insight_type, method_name in _GENERATORS:
            try:
                raw_candidates.extend(getattr(self, method_name)(db, user_id, ctx))
            except Exception:
                pass  # one broken generator must not block the others

        # Apply priority cap using cfg.INSIGHT_PRIORITY_ORDER (D-13, D-20)
        kept: list[tuple[str, str, str, float]] = []
        for prio in cfg.INSIGHT_PRIORITY_ORDER:
            group = sorted([c for c in raw_candidates if c[0] == prio], key=lambda x: x[3])
            for c in group:
                if len(kept) < cfg.INSIGHTS_MAX_PER_BATCH:
                    kept.append(c)

        created: List[Insight] = []
        for itype, title, body, _ in kept:
            row = Insight(user_id=user_id, insight_type=itype, title=title, body=body, status="active")
            db.add(row)
            created.append(row)
        db.commit()
        return created

    # --- Individual generators (one method per insight type) ---
    # Each receives (db, user_id, ctx) and returns list of (type, title, body, sort_key).
    # sort_key: lower = shown first within the type group (use -pct for "largest first").

    def _generate_spend_pace(self, db, user_id, ctx) -> list[tuple[str, str, str, float]]:
        """spend_pace: projected month-end > last month total (mutually exclusive with quiet_month)."""
        month_start = ctx["month_start"]
        prev_month_start = ctx["prev_month_start"]
        today = ctx["today"]
        this_month_total = ctx["this_month_total"]
        prev_month_total = self._sum_in_range(db, user_id, prev_month_start, month_start)
        days_in_month = (date(today.year + (today.month // 12), (today.month % 12) + 1, 1) - month_start).days
        days_elapsed = max((today.date() - month_start).days, 1)
        projected = float(this_month_total) / days_elapsed * days_in_month
        if prev_month_total > 0 and projected > float(prev_month_total):
            pct_more = round((projected / float(prev_month_total) - 1) * 100)
            return [("spend_pace",
                     f"On track to spend {pct_more}% more this month",
                     f"Projected Rs.{int(projected):,} vs Rs.{int(prev_month_total):,} last month.",
                     0.0)]
        return []

    def _generate_quiet_month(self, db, user_id, ctx) -> list[tuple[str, str, str, float]]:
        """quiet_month: projected month-end >= 20% below rolling average (mutually exclusive with spend_pace)."""
        month_start = ctx["month_start"]
        today = ctx["today"]
        this_month_total = ctx["this_month_total"]
        avg_monthly = self._rolling_avg_monthly(db, user_id, today)
        days_in_month = (date(today.year + (today.month // 12), (today.month % 12) + 1, 1) - month_start).days
        days_elapsed = max((today.date() - month_start).days, 1)
        projected = float(this_month_total) / days_elapsed * days_in_month
        if avg_monthly > 0 and projected < avg_monthly * (1 - cfg.QUIET_MONTH_BELOW_AVG_THRESHOLD):
            pct_below = round((1 - projected / avg_monthly) * 100)
            return [("quiet_month",
                     f"Quiet month — {pct_below}% below your average",
                     f"Projected Rs.{int(projected):,} vs Rs.{int(avg_monthly):,} average. Great month!",
                     0.0)]
        return []

    def _generate_category_surge(self, db, user_id, ctx) -> list[tuple[str, str, str, float]]:
        """category_surge: any category up >20% vs prior month, returned sorted by largest surge."""
        month_start = ctx["month_start"]
        prev_month_start = ctx["prev_month_start"]
        results = []
        cat_rows = (
            db.query(Transaction.category, func.sum(Transaction.amount).label("cur"))
            .filter(Transaction.user_id == user_id, Transaction.transaction_date >= month_start)
            .group_by(Transaction.category).all()
        )
        for cat, cur in cat_rows:
            prev = (
                db.query(func.sum(Transaction.amount))
                .filter(Transaction.user_id == user_id,
                        Transaction.category == cat,
                        Transaction.transaction_date >= prev_month_start,
                        Transaction.transaction_date < month_start)
                .scalar() or 0
            )
            if float(prev) > 0 and float(cur) > float(prev) * 1.2:
                surge_pct = round((float(cur) / float(prev) - 1) * 100)
                results.append(("category_surge",
                                f"{cat} up {surge_pct}% this month",
                                f"Rs.{int(cur):,} this month vs Rs.{int(prev):,} last month.",
                                -surge_pct))  # negative -> largest surge first
        return results

    def _generate_top_merchant(self, db, user_id, ctx) -> list[tuple[str, str, str, float]]:
        """top_merchant: single highest-spend merchant this month."""
        month_start = ctx["month_start"]
        this_month_total = ctx["this_month_total"]
        top_row = (
            db.query(Transaction.merchant, func.sum(Transaction.amount).label("total"))
            .filter(Transaction.user_id == user_id,
                    Transaction.transaction_date >= month_start,
                    Transaction.merchant.isnot(None))
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc()).first()
        )
        if top_row and this_month_total > 0:
            merchant, total = top_row
            pct = round(float(total) / float(this_month_total) * 100)
            return [("top_merchant",
                     f"Top merchant: {merchant} (Rs.{int(total):,})",
                     f"{pct}% of this month's spend.",
                     0.0)]
        return []

    def _sum_in_range(self, db: Session, user_id: int, start: date, end: date) -> Decimal:
        v = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id,
                    Transaction.transaction_date >= start,
                    Transaction.transaction_date < end).scalar()
        )
        return Decimal(str(v or 0))

    def _rolling_avg_monthly(self, db: Session, user_id: int, today: datetime) -> float:
        since = today.date() - timedelta(days=180)
        rows = (
            db.query(func.strftime("%Y-%m", Transaction.transaction_date),
                     func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id,
                    Transaction.transaction_date >= since)
            .group_by(func.strftime("%Y-%m", Transaction.transaction_date)).all()
        )
        if not rows:
            return 0.0
        return sum(float(r[1] or 0) for r in rows) / len(rows)


insight_service = InsightService()
