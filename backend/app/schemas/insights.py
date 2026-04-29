from datetime import datetime, date
from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict

AnomalyStatus = Literal["new", "dismissed", "investigating"]
AnomalyRule = Literal[
    "large_transaction", "high_value", "velocity_spike", "duplicate_like", "missing_subscription"
]
AnomalySeverity = Literal["low", "medium", "high"]
SubscriptionStatus = Literal["active", "canceled"]
InsightType = Literal["spend_pace", "category_surge", "top_merchant", "quiet_month"]
InsightStatus = Literal["active", "dismissed"]


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transaction_id: Optional[int] = None
    rule_name: AnomalyRule
    severity: AnomalySeverity
    status: AnomalyStatus
    detected_at: datetime
    dismissed_at: Optional[datetime] = None
    notes: Optional[str] = None


class AnomalyStatusUpdate(BaseModel):
    status: Literal["dismissed", "investigating"]  # D-06


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    merchant: str
    typical_amount: float
    status: SubscriptionStatus
    first_seen_month: date
    last_seen_month: date
    canceled_at: Optional[datetime] = None


class SubscriptionStatusUpdate(BaseModel):
    status: SubscriptionStatus  # D-11 user can mark canceled


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    insight_type: InsightType
    title: str
    body: str
    status: InsightStatus
    generated_at: datetime
    dismissed_at: Optional[datetime] = None


class InsightsSummaryOut(BaseModel):
    # GET /api/insights/summary -- used by nav badge (D-05)
    anomaly_count: int  # count of status='new' anomalies


class SubscriptionsListOut(BaseModel):
    items: List[SubscriptionOut]
    estimated_monthly_total: float  # sum of typical_amount where status='active'
