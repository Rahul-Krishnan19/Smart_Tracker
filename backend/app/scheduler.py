"""
APScheduler-based background job scheduler.
- Per-user Gmail sync jobs (GMAIL-06)
- Daily EmailMetadata cleanup (INFRA-04)
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models.user import User
from app.models.email_metadata import EmailMetadata
from app.services.gmail_service import gmail_service
from app.services.email_sync_service import email_sync_service

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

JOB_ID_TEMPLATE = "gmail_sync_user_{user_id}"


def sync_user_emails(user_id: int) -> None:
    """Called by APScheduler — opens own DB session. Per D-02, D-14."""
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.gmail_token_encrypted:
                logger.warning(f"Skipping sync for user {user_id}: no token")
                return

            # Get credentials, persist refreshed token if any (GMAIL-05/D-14)
            creds, new_token = gmail_service._get_credentials(user.gmail_token_encrypted)
            if new_token is not None:
                user.gmail_token_encrypted = new_token
                db.commit()

            # Run sync with (potentially updated) token
            email_sync_service.sync(
                db=db,
                user_id=user_id,
                encrypted_token=user.gmail_token_encrypted,
            )

            user.last_synced_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        # GMAIL-08: Log but never re-raise — scheduler must not crash
        logger.error(f"Auto-sync failed for user {user_id}: {e}")


def cleanup_expired_emails() -> None:
    """INFRA-04: Delete EmailMetadata rows past their delete_after date. Runs daily at 03:00."""
    try:
        with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            deleted = db.query(EmailMetadata).filter(
                EmailMetadata.delete_after <= now
            ).delete(synchronize_session=False)
            db.commit()
            if deleted:
                logger.info(f"Cleaned up {deleted} expired email metadata rows")
    except Exception as e:
        logger.error(f"Email cleanup failed: {e}")


def register_sync_job(user_id: int, interval_hours: int) -> None:
    """Register (or update) a per-user sync job. Per D-02, D-04."""
    job_id = JOB_ID_TEMPLATE.format(user_id=user_id)
    scheduler.add_job(
        sync_user_emails,
        trigger=IntervalTrigger(hours=interval_hours),
        id=job_id,
        args=[user_id],
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(f"Registered sync job {job_id} every {interval_hours}h")


def unregister_sync_job(user_id: int) -> None:
    """Remove a user's sync job if it exists."""
    job_id = JOB_ID_TEMPLATE.format(user_id=user_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed sync job {job_id}")


def register_startup_jobs() -> None:
    """Re-register jobs for all users with sync_enabled=True. Called at startup per D-04."""
    with SessionLocal() as db:
        users = db.query(User).filter(
            User.sync_enabled == True,
            User.sync_interval_hours.isnot(None),
        ).all()
        for user in users:
            register_sync_job(user.id, user.sync_interval_hours)
        logger.info(f"Registered sync jobs for {len(users)} user(s) on startup")

    # Register the daily cleanup job (D-17)
    scheduler.add_job(
        cleanup_expired_emails,
        trigger=CronTrigger(hour=3, minute=0),
        id="email_retention_cleanup",
        replace_existing=True,
    )
    logger.info("Registered daily email cleanup job at 03:00")
