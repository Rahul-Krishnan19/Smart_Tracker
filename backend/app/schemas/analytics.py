from __future__ import annotations
"""
Pydantic schemas for the analytics endpoints.
Phase 6, Plan 01 — ANA-03, ANA-04, ANA-05, ANA-06
"""
from datetime import date
from typing import Optional
from pydantic import BaseModel


class TrendItem(BaseModel):
    period_label: str
    period_start: date
    period_end: date
    total: float
    count: int
    category_totals: dict[str, float] = {}


class TrendResponse(BaseModel):
    trend: list[TrendItem]
    granularity: str
    current_total: float
    previous_total: float
    pct_change: Optional[float] = None
