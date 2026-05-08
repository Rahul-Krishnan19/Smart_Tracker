"""
Email sync service — orchestrates fetching emails from Gmail,
running them through parsers, and saving new transactions to DB.
Skips emails already processed (dedup by Gmail message ID).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.email_metadata import EmailMetadata
from app.models.transaction import Transaction
from app.services.gmail_service import gmail_service
from app.parsers.parser_factory import get_parser, parse_email
from app.services.category_rule_service import apply_user_rules, upsert_rule_if_absent


class EmailSyncService:

    def sync(
        self,
        db: Session,
        user_id: int,
        encrypted_token: str,
        max_emails: int = 200,
    ) -> dict:
        """
        Fetch emails, parse, and store new transactions.
        Returns a summary dict.
        """
        summary = {
            "fetched": 0,
            "skipped_duplicate": 0,
            "parsed_ok": 0,
            "parse_failed": 0,
            "unmatched": 0,
            "transactions_created": 0,
        }

        emails = gmail_service.fetch_transaction_emails(encrypted_token, max_results=max_emails)
        summary["fetched"] = len(emails)

        retention_cutoff = datetime.now(timezone.utc) + timedelta(days=settings.email_retention_days)

        for email in emails:
            gmail_id = email["id"]

            # Skip only emails that were successfully parsed — re-process unmatched/failed ones
            existing = db.query(EmailMetadata).filter(
                EmailMetadata.gmail_message_id == gmail_id
            ).first()
            if existing and existing.parse_status == "success":
                summary["skipped_duplicate"] += 1
                continue

            if existing:
                # Re-process previously failed/unmatched email
                meta = existing
                meta.parse_status = "pending"
                meta.parse_error = None
            else:
                # New email — record metadata
                meta = EmailMetadata(
                    user_id=user_id,
                    gmail_message_id=gmail_id,
                    sender=email["sender"][:255] if email["sender"] else None,
                    subject=email["subject"][:500] if email["subject"] else None,
                    received_at=email["received_at"],
                    parse_status="pending",
                    delete_after=retention_cutoff,
                )
                db.add(meta)

            # Parse — use parse_email(email_dict) which calls get_parser + parser.parse()
            # Separate unmatched (no parser found → returns None) from parse_failed (parser crashed)
            parsed = None
            try:
                parsed = parse_email(email)
            except Exception as e:
                meta.parse_status = "failed"
                meta.parse_error = str(e)[:500]
                summary["parse_failed"] += 1
                db.commit()
                continue

            if parsed is None:
                meta.parse_status = "unmatched"
                meta.parse_error = "No parser matched"
                summary["unmatched"] += 1
                db.commit()
                continue

            # Apply user-defined category rules — overrides parser's category if matched
            user_cat = apply_user_rules(db, user_id, parsed.merchant or "", parsed.description)
            if user_cat:
                parsed.category = user_cat

            # Save transaction — skip if duplicate email_message_id
            existing_tx = db.query(Transaction).filter(
                Transaction.email_message_id == gmail_id
            ).first()
            if not existing_tx:
                tx = Transaction(
                    user_id=user_id,
                    transaction_date=parsed.transaction_date,
                    amount=parsed.amount,
                    description=parsed.description,
                    merchant=parsed.merchant,
                    category=parsed.category,
                    payment_method=parsed.payment_method,
                    payment_source=parsed.payment_source,
                    notes=f"Ref: {parsed.reference_number}" if parsed.reference_number else None,
                    source="email",
                    email_message_id=gmail_id,
                )
                db.add(tx)
                summary["transactions_created"] += 1

                # Auto-persist merchant→category rule so future imports stay
                # categorised even if the parser's heuristic changes.
                if parsed.merchant:
                    upsert_rule_if_absent(db, user_id, parsed.merchant, parsed.category)

            meta.parse_status = "success"
            meta.bank_name = parsed.bank_name
            summary["parsed_ok"] += 1
            db.commit()

        # Phase 7 D-19: post-sync detection hook (insights/anomalies/subscriptions)
        try:
            from app.services import insights_orchestrator as _orch
            insights_summary = _orch.run_post_sync(db, user_id)
            summary["insights"] = insights_summary
        except Exception as e:
            # never break sync because of insights
            import logging
            logging.getLogger(__name__).error(f"post-sync insights hook failed: {e}")

        return summary


email_sync_service = EmailSyncService()
