from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

Granularity = Literal["daily", "weekly", "monthly", "annual"]


class SpendingLimitOut(BaseModel):
    granularity: str
    amount: Optional[float] = None


class SpendingLimitUpsert(BaseModel):
    granularity: Granularity
    amount: Decimal = Field(gt=0)
