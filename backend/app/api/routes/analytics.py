"""
Analytics API routes — trend aggregation and spending-limit endpoints.
Phase 6, Plan 01 — ANA-03, ANA-04, ANA-05, ANA-06
Phase 6, Plan 02 — GOAL-02 (spending limit CRUD)
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.trend_service import trend_service, GRANULARITY_FORMAT
from app.schemas.analytics import TrendResponse
from app.schemas.spending_limit import SpendingLimitOut, SpendingLimitUpsert, Granularity
from app.services.spending_limit_service import (
    get_spending_limit as _get_limit,
    upsert_spending_limit as _upsert_limit,
    delete_spending_limit as _delete_limit,
)

router = APIRouter()


@router.get("/trend", response_model=TrendResponse)
def get_trend(
    granularity: str = Query("monthly"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    payment_source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_amount: Optional[Decimal] = Query(None, ge=0),
    max_amount: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ANA-03 / ANA-04 / ANA-05 / ANA-06: time-series trend with category totals
    and previous-period comparison.

    Query params:
      granularity    — daily | weekly | monthly | annual (default: monthly)
      date_from      — ISO date, inclusive lower bound
      date_to        — ISO date, inclusive upper bound
      payment_source — optional filter by exact payment source string

    Response (TrendResponse):
      trend          — list of TrendItem (period_label, period_start, period_end,
                       total, count, category_totals)
      granularity    — echoed back
      current_total  — sum of amounts in the requested range
      previous_total — sum for the equivalent prior period (ANA-06 callout)
      pct_change     — percentage change vs previous period (None when prev=0)
    """
    if granularity not in GRANULARITY_FORMAT:
        raise HTTPException(
            status_code=422,
            detail=f"granularity must be one of {list(GRANULARITY_FORMAT.keys())}",
        )
    return trend_service.get_trend(
        db=db,
        user_id=current_user.id,
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
        payment_source=payment_source,
        category=category,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
    )


@router.get("/spending-limit", response_model=SpendingLimitOut)
def read_spending_limit(
    granularity: Granularity = Query(..., description="daily | weekly | monthly | annual"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GOAL-02: Retrieve the spending limit for the given granularity.

    Returns {granularity, amount} when a limit is set,
    or {granularity, amount: null} when no limit is configured.
    """
    row = _get_limit(db, current_user.id, granularity)
    return SpendingLimitOut(
        granularity=granularity,
        amount=float(row.amount) if row else None,
    )


@router.put("/spending-limit", response_model=SpendingLimitOut)
def upsert_spending_limit_route(
    data: SpendingLimitUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GOAL-02: Create or update the spending limit for a given granularity.

    Body: {granularity: "daily"|"weekly"|"monthly"|"annual", amount: > 0}
    Returns the persisted SpendingLimitOut.
    """
    row = _upsert_limit(db, current_user.id, data.granularity, data.amount)
    return SpendingLimitOut(granularity=row.granularity, amount=float(row.amount))


@router.delete("/spending-limit", status_code=204)
def delete_spending_limit_route(
    granularity: Granularity = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GOAL-02: Remove the spending limit for the given granularity (idempotent).

    Returns 204 whether or not a limit existed.
    """
    _delete_limit(db, current_user.id, granularity)
    return None
