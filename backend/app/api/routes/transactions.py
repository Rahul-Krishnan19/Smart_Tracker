"""
Transaction CRUD API routes with filtering, pagination, new endpoints, and CSV export.
"""
import csv
import io
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionOut,
    TransactionListResponse, TransactionFilters,
    TransactionCategoryUpdate, BulkCategorizeRequest,
)
from app.services.transaction_service import transaction_service
from app.services.category_rule_service import upsert_rule_and_bulk_update
from app.api.routes.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_service.create(db, current_user.id, data)


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    payment_source: Optional[str] = Query(None),
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        category=category,
        payment_method=payment_method,
        payment_source=payment_source,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
        page=page,
        page_size=page_size,
    )
    return transaction_service.list(db, current_user.id, filters)


@router.get("/summary")
def get_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    payment_source: Optional[str] = Query(None),
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        category=category,
        payment_method=payment_method,
        payment_source=payment_source,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )
    return transaction_service.get_summary(db, current_user.id, filters)


# ---------------------------------------------------------------------------
# New static-path routes (MUST come before /{tx_id})
# ---------------------------------------------------------------------------

@router.get("/payment-sources")
def list_payment_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """PAY-05: Return distinct non-null payment_source values for the user."""
    rows = (
        db.query(Transaction.payment_source)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.payment_source.isnot(None),
        )
        .distinct()
        .all()
    )
    return {"payment_sources": sorted([r[0] for r in rows])}


@router.get("/merchants")
def search_merchants(
    q: str = Query("", max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ANA-09: Return up to 10 merchant names matching the query string."""
    if not q:
        return {"merchants": []}
    term = f"%{q}%"
    rows = (
        db.query(Transaction.merchant)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.merchant.isnot(None),
            Transaction.merchant.ilike(term),
        )
        .distinct()
        .limit(10)
        .all()
    )
    return {"merchants": [r[0] for r in rows]}


@router.get("/merchant-breakdown")
def get_merchant_breakdown(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    payment_source: Optional[str] = Query(None),
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ANA-07: Return top 10 merchants by spend with pct_of_total."""
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        category=category,
        payment_method=payment_method,
        payment_source=payment_source,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )
    return transaction_service.get_merchant_breakdown(db, current_user.id, filters)


@router.get("/export")
def export_transactions(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    payment_source: Optional[str] = Query(None),
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """TXN-08: Export all matching transactions as a CSV download."""
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        category=category,
        payment_method=payment_method,
        payment_source=payment_source,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )
    rows = transaction_service.export(db, current_user.id, filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Amount", "Description", "Merchant", "Category",
        "Payment Method", "Payment Source", "Notes",
    ])
    for tx in rows:
        writer.writerow([
            str(tx.transaction_date),
            float(tx.amount),
            tx.description,
            tx.merchant or "",
            tx.category,
            tx.payment_method,
            tx.payment_source or "",
            tx.notes or "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.post("/bulk-categorize")
def bulk_categorize(
    data: BulkCategorizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """TXN-12: Bulk-update category for selected transactions (user-scoped)."""
    updated = transaction_service.bulk_categorize(
        db, current_user.id, data.transaction_ids, data.category
    )
    return {"updated": updated}


@router.get("/categories")
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return system categories + any custom categories the user has used."""
    from app.models.transaction import CATEGORIES
    custom = db.query(Transaction.category).filter(
        Transaction.user_id == current_user.id,
        Transaction.category.notin_(CATEGORIES),
    ).distinct().all()
    custom_list = [r[0] for r in custom if r[0]]
    return {"categories": CATEGORIES + sorted(custom_list)}


# ---------------------------------------------------------------------------
# Per-transaction routes (/{tx_id} — must stay after all static routes)
# ---------------------------------------------------------------------------

@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_service.get(db, current_user.id, tx_id)


@router.put("/{tx_id}", response_model=TransactionOut)
def update_transaction(
    tx_id: int,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_service.update(db, current_user.id, tx_id, data)


@router.put("/{tx_id}/category", response_model=TransactionOut)
def update_transaction_category(
    tx_id: int,
    data: TransactionCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """TXN-11: Inline category re-assign.

    Whenever the transaction has a merchant, we ALWAYS persist a merchant→category
    rule (via upsert_rule_and_bulk_update) so future imports respect the user's
    correction and existing transactions from that merchant are bulk-updated.
    """
    tx = transaction_service.get(db, current_user.id, tx_id)
    tx.category = data.category
    if tx.merchant:
        upsert_rule_and_bulk_update(db, current_user.id, tx.merchant, data.category)
    else:
        db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction_service.delete(db, current_user.id, tx_id)
