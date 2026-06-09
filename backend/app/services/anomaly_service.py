"""Anomaly detection — D-01 rules. Idempotent via existence checks."""
from __future__ import annotations
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.db_compat import date_format
from sqlalchemy import func, and_

from app.models.anomaly import Anomaly
from app.models.transaction import Transaction
from app.models.subscription import Subscription
from app.services import insights_config as cfg


class AnomalyService:
    def detect(self, db: Session, user_id: int, now: Optional[datetime] = None) -> List[Anomaly]:
        """Run all 5 rules. Append-only: skips (rule_name, transaction_id) pairs already 'new' or 'investigating'."""
        now = now or datetime.utcnow()
        created: List[Anomaly] = []

        # Recent txs only — last 90 days is enough for all rules
        window_start = now - timedelta(days=90)
        recent_txs = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.transaction_date >= window_start.date())
            .order_by(Transaction.transaction_date.desc())
            .all()
        )

        for tx in recent_txs:
            # Rule 1: high_value
            if Decimal(str(tx.amount)) > cfg.ANOMALY_HIGH_VALUE_THRESHOLD:
                created.append(self._maybe_flag(db, user_id, tx.id, "high_value"))

            # Rule 2: large_transaction (per category baseline)
            if self._exceeds_category_baseline(db, user_id, tx, now):
                created.append(self._maybe_flag(db, user_id, tx.id, "large_transaction"))

            # Rule 4: duplicate_like — same merchant+amount within window
            if self._has_duplicate_like(db, user_id, tx):
                created.append(self._maybe_flag(db, user_id, tx.id, "duplicate_like"))

        # Rule 3: velocity_spike — group by merchant within window
        for merchant_id in self._merchants_with_velocity_spike(db, user_id, now):
            # Anchor anomaly to the most recent tx in the spike
            anchor = (
                db.query(Transaction)
                .filter(Transaction.user_id == user_id, Transaction.merchant == merchant_id)
                .order_by(Transaction.transaction_date.desc())
                .first()
            )
            if anchor:
                created.append(self._maybe_flag(db, user_id, anchor.id, "velocity_spike"))

        # Rule 3b: velocity_spike — daily-spend exceeds rolling-average multiplier (D-01 item 3, sub-condition 2)
        anchor_id = self._daily_spend_spike(db, user_id, now)
        if anchor_id is not None:
            created.append(self._maybe_flag(db, user_id, anchor_id, "velocity_spike"))

        # Rule 5: missing_subscription (only after day >= MISSING_SUBSCRIPTION_TRIGGER_DAY)
        if now.day >= cfg.MISSING_SUBSCRIPTION_TRIGGER_DAY:
            month_start = date(now.year, now.month, 1)
            active_subs = (
                db.query(Subscription)
                .filter(Subscription.user_id == user_id, Subscription.status == "active")
                .all()
            )
            for sub in active_subs:
                seen = (
                    db.query(Transaction.id)
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.merchant == sub.merchant,
                        Transaction.transaction_date >= month_start,
                    )
                    .first()
                )
                if not seen:
                    # transaction_id=None for missing_subscription per D-10
                    created.append(
                        self._maybe_flag(db, user_id, None, "missing_subscription", sub_key=sub.id)
                    )

        db.commit()
        return [a for a in created if a is not None]

    # --- helpers ---
    def _maybe_flag(self, db: Session, user_id: int, transaction_id: Optional[int],
                    rule_name: str, sub_key: Optional[int] = None) -> Optional[Anomaly]:
        """Create anomaly if no open one exists for the same (rule_name, transaction_id)."""
        q = db.query(Anomaly).filter(
            Anomaly.user_id == user_id,
            Anomaly.rule_name == rule_name,
            Anomaly.status.in_(("new", "investigating")),
        )
        if transaction_id is None:
            # For missing_subscription, also dedup by sub_key encoded into notes JSON-ish
            q = q.filter(Anomaly.transaction_id.is_(None))
            if sub_key is not None:
                q = q.filter(Anomaly.notes == f"sub:{sub_key}")
        else:
            q = q.filter(Anomaly.transaction_id == transaction_id)
        if q.first():
            return None

        row = Anomaly(
            user_id=user_id,
            transaction_id=transaction_id,
            rule_name=rule_name,
            severity=cfg.ANOMALY_SEVERITY.get(rule_name, "medium"),
            status="new",
            notes=f"sub:{sub_key}" if sub_key is not None else None,
        )
        db.add(row)
        db.flush()
        return row

    def _exceeds_category_baseline(self, db: Session, user_id: int, tx: Transaction, now: datetime) -> bool:
        # Need >= ANOMALY_MIN_HISTORY_MONTHS of history in this category
        history_start = (now - timedelta(days=cfg.ANOMALY_MIN_HISTORY_MONTHS * 31)).date()
        history = (
            db.query(func.avg(Transaction.amount))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category == tx.category,
                Transaction.transaction_date >= history_start,
                Transaction.transaction_date < tx.transaction_date,
                Transaction.id != tx.id,
            )
            .scalar()
        )
        distinct_months = (
            db.query(func.count(func.distinct(date_format("%Y-%m", Transaction.transaction_date))))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category == tx.category,
                Transaction.transaction_date < tx.transaction_date,
            )
            .scalar()
        ) or 0
        if distinct_months < cfg.ANOMALY_MIN_HISTORY_MONTHS or not history:
            return False
        return float(tx.amount) > cfg.ANOMALY_LARGE_TX_MULTIPLIER * float(history)

    def _has_duplicate_like(self, db: Session, user_id: int, tx: Transaction) -> bool:
        window = timedelta(hours=cfg.ANOMALY_DUPLICATE_WINDOW_HOURS)
        earliest = (datetime.combine(tx.transaction_date, datetime.min.time()) - window).date()
        return db.query(Transaction.id).filter(
            Transaction.user_id == user_id,
            Transaction.merchant == tx.merchant,
            Transaction.amount == tx.amount,
            Transaction.id != tx.id,
            Transaction.transaction_date >= earliest,
            Transaction.transaction_date <= tx.transaction_date,
        ).first() is not None

    def _merchants_with_velocity_spike(self, db: Session, user_id: int, now: datetime) -> List[str]:
        window_start = (now - timedelta(hours=cfg.ANOMALY_VELOCITY_WINDOW_HOURS)).date()
        rows = (
            db.query(Transaction.merchant, func.count(Transaction.id).label("c"))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= window_start,
                Transaction.merchant.isnot(None),
            )
            .group_by(Transaction.merchant)
            .having(func.count(Transaction.id) >= cfg.ANOMALY_VELOCITY_MIN_COUNT)
            .all()
        )
        return [r[0] for r in rows]

    def _daily_spend_spike(self, db: Session, user_id: int, now: datetime) -> Optional[int]:
        """D-01 sub-condition: today's total spend > multiplier x rolling daily avg over last 30 days (excluding today).
        Returns the id of the largest tx on today (anchor) or None if rule does not fire.
        Requires >= ANOMALY_MIN_HISTORY_MONTHS x 30 days of history.
        """
        today = now.date()
        history_days = cfg.ANOMALY_MIN_HISTORY_MONTHS * 30
        history_start = today - timedelta(days=history_days)
        # Need enough history: count distinct days with any tx in the window
        distinct_days = (
            db.query(func.count(func.distinct(Transaction.transaction_date)))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= history_start,
                Transaction.transaction_date < today,
            )
            .scalar()
        ) or 0
        if distinct_days < history_days // 2:  # require at least half the days to have data
            return None

        today_total = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id, Transaction.transaction_date == today)
            .scalar()
        ) or 0
        if float(today_total) <= 0:
            return None

        # Rolling daily average over last 30 days excluding today
        rolling_start = today - timedelta(days=30)
        history_total = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= rolling_start,
                Transaction.transaction_date < today,
            )
            .scalar()
        ) or 0
        rolling_avg = float(history_total) / 30.0
        if rolling_avg <= 0:
            return None
        if float(today_total) <= cfg.ANOMALY_DAILY_SPEND_MULTIPLIER * rolling_avg:
            return None

        # Anchor on the largest tx of the day
        anchor = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id, Transaction.transaction_date == today)
            .order_by(Transaction.amount.desc())
            .first()
        )
        return anchor.id if anchor else None


anomaly_service = AnomalyService()
