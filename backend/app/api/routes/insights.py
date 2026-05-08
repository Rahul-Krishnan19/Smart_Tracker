"""/api/insights/* routes — anomalies, subscriptions, insights feed."""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.models.anomaly import Anomaly
from app.models.subscription import Subscription
from app.models.insight import Insight
from app.schemas.insights import (
    AnomalyOut, AnomalyStatusUpdate,
    SubscriptionOut, SubscriptionStatusUpdate, SubscriptionsListOut,
    InsightOut, InsightsSummaryOut,
)

router = APIRouter(prefix="/api/insights", tags=["insights"])


# ---- Anomalies ----
@router.get("/anomalies", response_model=List[AnomalyOut])
def list_anomalies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Anomaly)
        .filter(Anomaly.user_id == current_user.id)
        .order_by(Anomaly.detected_at.desc())
        .all()
    )


@router.patch("/anomalies/{anomaly_id}", response_model=AnomalyOut)
def update_anomaly_status(
    anomaly_id: int,
    body: AnomalyStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(Anomaly).filter(
        Anomaly.id == anomaly_id, Anomaly.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    row.status = body.status
    if body.status == "dismissed":
        row.dismissed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


# ---- Subscriptions ----
@router.get("/subscriptions", response_model=SubscriptionsListOut)
def list_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .order_by(Subscription.merchant.asc())
        .all()
    )
    active_total = sum(float(r.typical_amount) for r in rows if r.status == "active")
    return SubscriptionsListOut(
        items=[SubscriptionOut.model_validate(r) for r in rows],
        estimated_monthly_total=round(active_total, 2),
    )


@router.patch("/subscriptions/{sub_id}", response_model=SubscriptionOut)
def update_subscription_status(
    sub_id: int,
    body: SubscriptionStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(Subscription).filter(
        Subscription.id == sub_id, Subscription.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")
    row.status = body.status
    row.canceled_at = datetime.utcnow() if body.status == "canceled" else None
    db.commit()
    db.refresh(row)
    return row


# ---- Insights feed ----
@router.get("/insights", response_model=List[InsightOut])
def list_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Insight)
        .filter(Insight.user_id == current_user.id, Insight.status == "active")
        .order_by(Insight.generated_at.desc())
        .all()
    )


@router.post("/insights/{insight_id}/dismiss", response_model=InsightOut)
def dismiss_insight(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(Insight).filter(
        Insight.id == insight_id, Insight.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Insight not found")
    row.status = "dismissed"
    row.dismissed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


# ---- Summary (for nav badge) ----
@router.get("/summary", response_model=InsightsSummaryOut)
def insights_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(Anomaly).filter(
        Anomaly.user_id == current_user.id, Anomaly.status == "new"
    ).count()
    return InsightsSummaryOut(anomaly_count=count)
