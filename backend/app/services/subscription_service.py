"""Subscription detection per D-07. Re-activates canceled subs per D-11."""
from datetime import datetime, date
from decimal import Decimal
from statistics import median
from collections import defaultdict
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.services import insights_config as cfg


class SubscriptionService:
    def detect(self, db: Session, user_id: int) -> List[Subscription]:
        # Fetch all txs grouped by (merchant, year-month)
        rows = (
            db.query(
                Transaction.merchant,
                func.strftime("%Y-%m", Transaction.transaction_date).label("ym"),
                Transaction.amount,
            )
            .filter(Transaction.user_id == user_id, Transaction.merchant.isnot(None))
            .all()
        )
        buckets: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
        for merchant, ym, amount in rows:
            buckets[merchant][ym].append(Decimal(str(amount)))

        results: List[Subscription] = []
        for merchant, by_month in buckets.items():
            # Filter months that satisfy max-distinct-amounts rule
            qualifying_months = sorted(
                ym for ym, amounts in by_month.items()
                if len(set(amounts)) <= cfg.SUBSCRIPTION_MAX_DISTINCT_AMOUNTS_PER_MONTH
            )
            if len(qualifying_months) < cfg.SUBSCRIPTION_MIN_CONSECUTIVE_MONTHS:
                continue
            # Check that the qualifying months include at least N CONSECUTIVE
            if not self._has_consecutive(qualifying_months, cfg.SUBSCRIPTION_MIN_CONSECUTIVE_MONTHS):
                continue

            all_amounts = [a for amounts in by_month.values() for a in amounts]
            typical = Decimal(str(round(float(median(all_amounts)), 2)))
            first_ym = min(qualifying_months)
            last_ym = max(qualifying_months)

            first_seen = date(int(first_ym[:4]), int(first_ym[5:7]), 1)
            last_seen = date(int(last_ym[:4]), int(last_ym[5:7]), 1)

            existing = (
                db.query(Subscription)
                .filter(Subscription.user_id == user_id, Subscription.merchant == merchant)
                .first()
            )
            if existing:
                existing.typical_amount = typical
                existing.last_seen_month = last_seen
                if existing.status == "canceled":
                    # D-11: re-activate
                    existing.status = "active"
                    existing.canceled_at = None
                results.append(existing)
            else:
                sub = Subscription(
                    user_id=user_id, merchant=merchant, typical_amount=typical,
                    status="active", first_seen_month=first_seen, last_seen_month=last_seen,
                )
                db.add(sub)
                results.append(sub)

        db.commit()
        return results

    def _has_consecutive(self, months: list[str], n: int) -> bool:
        """months is sorted YYYY-MM strings — return True if any run of n consecutive months exists."""
        ds = [date(int(m[:4]), int(m[5:7]), 1) for m in months]
        run = 1
        for i in range(1, len(ds)):
            prev, cur = ds[i-1], ds[i]
            # consecutive: cur is exactly next month after prev
            next_m = (prev.month % 12) + 1
            next_y = prev.year + (1 if prev.month == 12 else 0)
            if cur.year == next_y and cur.month == next_m:
                run += 1
                if run >= n:
                    return True
            else:
                run = 1
        return False


subscription_service = SubscriptionService()
