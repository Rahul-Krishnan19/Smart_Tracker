"""
Analytics API routes — trend aggregation endpoint.
Phase 6, Plan 01 — ANA-03, ANA-04, ANA-05, ANA-06
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.trend_service import trend_service, GRANULARITY_FORMAT
from app.schemas.analytics import TrendResponse

router = APIRouter()


@router.get("/trend", response_model=TrendResponse)
def get_trend(
    granularity: str = Query("monthly"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    payment_source: Optional[str] = Query(None),
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
    )
