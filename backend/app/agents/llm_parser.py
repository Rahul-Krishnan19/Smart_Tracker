from __future__ import annotations
"""
LLM-backed catch-all email parser (Agent 1).

This parser is registered LAST in parser_factory.PARSERS so it only runs when
every bank-specific parser has declined the email. It asks Gemini to extract a
structured transaction from arbitrary bank-alert text, which lets us handle
banks/formats we have not written a dedicated regex parser for yet.

Like all parsers it must never raise: on any failure (no API key, non-transaction
email, malformed model output) `parse` returns None and the email is skipped.
"""
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.parsers.base_parser import BaseEmailParser, ParsedTransaction
from app.parsers.categorizer import categorize
from app.agents.llm_client import ask_json

logger = logging.getLogger(__name__)

# Keep the prompt body bounded so a huge HTML email cannot blow up token usage.
_MAX_BODY_CHARS = 6000

_PROMPT_TEMPLATE = """You are a precise bank-transaction email extractor.

Given the sender, subject, and body of an email, extract the financial \
transaction it describes. Respond with ONLY a single JSON object and nothing else.

If this email is NOT a bank/card/UPI transaction notification (e.g. it is a \
promotion, statement summary, OTP, or newsletter), respond with exactly:
{{"transaction": null}}

Otherwise respond with:
{{
  "transaction": {{
    "amount": <number>,
    "merchant": "<string>",
    "date": "<YYYY-MM-DD>",
    "transaction_type": "<debit|credit>",
    "payment_method": "<string, e.g. UPI / Credit Card / Debit Card / Net Banking>",
    "reference_number": "<string or null>"
  }}
}}

Sender: {sender}
Subject: {subject}
Body:
{body}
"""

# Maps free-form model payment-method strings onto the canonical labels used by
# the rest of the system (see Transaction.PAYMENT_METHODS).
_PAYMENT_METHOD_MAP = {
    "upi": "UPI",
    "credit card": "Credit Card",
    "creditcard": "Credit Card",
    "debit card": "Debit Card",
    "debitcard": "Debit Card",
    "net banking": "Net Banking",
    "netbanking": "Net Banking",
    "cash": "Cash",
}


def _normalize_payment_method(raw: Optional[str]) -> str:
    if not raw:
        return "Others"
    return _PAYMENT_METHOD_MAP.get(raw.strip().lower(), raw.strip().title())


def _parse_amount(raw) -> Optional[Decimal]:
    if raw is None:
        return None
    try:
        # str() handles both numeric and string inputs; strip commas/currency.
        cleaned = str(raw).replace(",", "").replace("Rs.", "").replace("INR", "").strip()
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    return amount if amount > 0 else None


def _parse_date(raw, fallback: date) -> date:
    if not raw:
        return fallback
    try:
        return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return fallback


def _sender_domain(sender: str) -> Optional[str]:
    """Extract the domain from a sender like 'Alerts <alerts@hdfcbank.net>'."""
    if not sender or "@" not in sender:
        return None
    domain = sender.rsplit("@", 1)[-1]
    # Strip any trailing '>' from an RFC-822 style address.
    return domain.split(">")[0].strip().lower() or None


class LLMEmailParser(BaseEmailParser):

    @property
    def bank_name(self) -> str:
        return "LLM"

    @property
    def sender_patterns(self) -> list[str]:
        # Catch-all: no specific senders.
        return []

    @property
    def subject_patterns(self) -> list[str]:
        return []

    def can_parse(self, sender: str, subject: str, body: str) -> bool:
        # Always claims the email; intended as the final fallback in PARSERS.
        return True

    def parse(self, email: dict) -> Optional[ParsedTransaction]:
        sender = email.get("sender", "") or ""
        subject = email.get("subject", "") or ""
        body = (email.get("body", "") or "")[:_MAX_BODY_CHARS]

        prompt = _PROMPT_TEMPLATE.format(sender=sender, subject=subject, body=body)

        result = ask_json(prompt)
        if not result:
            return None

        txn = result.get("transaction")
        if not isinstance(txn, dict):
            # Either {"transaction": null} (not a transaction) or malformed.
            return None

        amount = _parse_amount(txn.get("amount"))
        if amount is None:
            logger.debug("LLM parser: missing/invalid amount, skipping email")
            return None

        received_at = email.get("received_at")
        fallback_date = received_at.date() if received_at else date.today()
        txn_date = _parse_date(txn.get("date"), fallback_date)

        merchant = (txn.get("merchant") or "").strip() or "Unknown"
        payment_method = _normalize_payment_method(txn.get("payment_method"))

        reference = txn.get("reference_number")
        reference = str(reference).strip() if reference else None

        txn_type = (txn.get("transaction_type") or "debit").strip().lower()
        description = f"{txn_type.capitalize()} at {merchant}"

        return ParsedTransaction(
            amount=amount,
            description=description,
            merchant=merchant,
            transaction_date=txn_date,
            payment_method=payment_method,
            category=categorize(merchant, description),
            reference_number=reference,
            account_last4=None,
            bank_name=self.bank_name,
            payment_source=_sender_domain(sender),
        )
