"""Post-sync orchestrator — D-19. Called from email_sync_service after a successful sync."""
import logging
from sqlalchemy.orm import Session

from app.services.subscription_service import subscription_service
from app.services.anomaly_service import anomaly_service
from app.services.insight_service import insight_service

logger = logging.getLogger(__name__)


def run_post_sync(db: Session, user_id: int) -> dict:
    """Run subscriptions -> anomalies -> insights in order. Errors logged, never re-raised."""
    out = {"subscriptions": 0, "anomalies": 0, "insights": 0}
    try:
        out["subscriptions"] = len(subscription_service.detect(db, user_id))
    except Exception as e:
        logger.error(f"subscription detection failed for user {user_id}: {e}")
    try:
        out["anomalies"] = len(anomaly_service.detect(db, user_id))
    except Exception as e:
        logger.error(f"anomaly detection failed for user {user_id}: {e}")
    try:
        out["insights"] = len(insight_service.regenerate(db, user_id))
    except Exception as e:
        logger.error(f"insight regeneration failed for user {user_id}: {e}")
    return out
