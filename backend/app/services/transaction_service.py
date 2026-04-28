"""
Transaction CRUD service with filtering, pagination, validation, export, and merchant breakdown.
"""
import math
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilters


class TransactionService:

    def create(self, db: Session, user_id: int, data: TransactionCreate) -> Transaction:
        tx = Transaction(
            user_id=user_id,
            transaction_date=data.transaction_date,
            amount=data.amount,
            description=data.description,
            merchant=data.merchant,
            category=data.category,
            payment_method=data.payment_method,
            notes=data.notes,
            source="manual",
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    def get(self, db: Session, user_id: int, tx_id: int) -> Transaction:
        tx = db.query(Transaction).filter(
            Transaction.id == tx_id,
            Transaction.user_id == user_id,
        ).first()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return tx

    def _build_filter_query(self, db: Session, user_id: int, filters: TransactionFilters):
        """Build a base query with all filter conditions applied."""
        query = db.query(Transaction).filter(Transaction.user_id == user_id)

        if filters.date_from:
            query = query.filter(Transaction.transaction_date >= filters.date_from)
        if filters.date_to:
            query = query.filter(Transaction.transaction_date <= filters.date_to)
        if filters.category:
            query = query.filter(Transaction.category == filters.category)
        if filters.payment_method:
            query = query.filter(Transaction.payment_method == filters.payment_method)
        if filters.payment_source:
            query = query.filter(Transaction.payment_source == filters.payment_source)
        if filters.min_amount is not None:
            query = query.filter(Transaction.amount >= filters.min_amount)
        if filters.max_amount is not None:
            query = query.filter(Transaction.amount <= filters.max_amount)
        if filters.search:
            term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(term),
                    Transaction.merchant.ilike(term),
                    Transaction.notes.ilike(term),
                )
            )

        return query

    def list(self, db: Session, user_id: int, filters: TransactionFilters) -> dict:
        query = self._build_filter_query(db, user_id, filters)

        total = query.count()
        total_pages = math.ceil(total / filters.page_size) if total > 0 else 1
        offset = (filters.page - 1) * filters.page_size

        items = (
            query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
            .all()
        )

        return {
            "items": items,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "total_pages": total_pages,
        }

    def update(self, db: Session, user_id: int, tx_id: int, data: TransactionUpdate) -> Transaction:
        tx = self.get(db, user_id, tx_id)
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(tx, field, value)
        db.commit()
        db.refresh(tx)
        return tx

    def delete(self, db: Session, user_id: int, tx_id: int) -> None:
        tx = self.get(db, user_id, tx_id)
        db.delete(tx)
        db.commit()

    def get_summary(self, db: Session, user_id: int, filters: TransactionFilters) -> dict:
        """Return summary stats respecting all filter params."""
        query = self._build_filter_query(db, user_id, filters)

        total_amount = query.with_entities(
            func.sum(Transaction.amount)
        ).scalar() or Decimal("0")

        count = query.count()

        # Category breakdown
        category_breakdown = query.with_entities(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        ).group_by(Transaction.category).all()

        # Payment method breakdown
        payment_breakdown = query.with_entities(
            Transaction.payment_method,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        ).group_by(Transaction.payment_method).all()

        return {
            "total_amount": float(total_amount),
            "transaction_count": count,
            "category_breakdown": [
                {"category": r.category, "total": float(r.total), "count": r.count}
                for r in category_breakdown
            ],
            "payment_breakdown": [
                {"payment_method": r.payment_method, "total": float(r.total), "count": r.count}
                for r in payment_breakdown
            ],
        }

    def export(self, db: Session, user_id: int, filters: TransactionFilters) -> list:
        """Return all matching transactions (no pagination) for CSV export."""
        query = self._build_filter_query(db, user_id, filters)
        return query.order_by(Transaction.transaction_date.desc()).all()

    def get_merchant_breakdown(
        self,
        db: Session,
        user_id: int,
        filters: TransactionFilters,
        limit: int = 10,
    ) -> dict:
        """Return top N merchants by total spend with percentage of total."""
        base = self._build_filter_query(db, user_id, filters).filter(
            Transaction.merchant.isnot(None)
        )
        total_all = (
            self._build_filter_query(db, user_id, filters)
            .with_entities(func.sum(Transaction.amount))
            .scalar()
        ) or Decimal("0")

        rows = (
            base.with_entities(
                Transaction.merchant,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
                func.avg(Transaction.amount).label("avg"),
            )
            .group_by(Transaction.merchant)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
            .all()
        )

        return {
            "merchants": [
                {
                    "merchant": r.merchant,
                    "total": float(r.total),
                    "count": r.count,
                    "avg": round(float(r.avg), 2),
                    "pct_of_total": (
                        round(float(r.total) / float(total_all) * 100, 1)
                        if float(total_all) > 0
                        else 0
                    ),
                }
                for r in rows
            ],
            "total_amount": float(total_all),
        }

    def bulk_categorize(
        self,
        db: Session,
        user_id: int,
        transaction_ids: list[int],
        category: str,
    ) -> int:
        """Bulk update category for a list of transaction IDs, scoped to user."""
        updated = (
            db.query(Transaction)
            .filter(
                Transaction.id.in_(transaction_ids),
                Transaction.user_id == user_id,
            )
            .update({"category": category}, synchronize_session=False)
        )
        db.commit()
        return updated


transaction_service = TransactionService()
