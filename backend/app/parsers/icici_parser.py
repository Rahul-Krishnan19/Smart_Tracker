from __future__ import annotations
"""
ICICI Bank Credit Card email parser.
Parses transaction alerts from credit_cards@icicibank.com.

Sample email:
  Your ICICI Bank Credit Card XX6005 has been used for a transaction of INR 2,009.98
  on Apr 03, 2026 at 04:53:52. Info: RAZ*Urbanaut.
"""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.parsers.base_parser import BaseEmailParser, ParsedTransaction
from app.parsers.categorizer import categorize


class ICICIParser(BaseEmailParser):

    @property
    def bank_name(self) -> str:
        return "ICICI Bank"

    @property
    def sender_patterns(self) -> list[str]:
        return ["credit_cards@icicibank.com"]

    @property
    def subject_patterns(self) -> list[str]:
        return ["icici bank credit card"]

    def can_parse(self, sender: str, subject: str, body: str) -> bool:
        text = (body or "").lower()
        return (
            "icici bank credit card" in text
            and "has been used for a transaction" in text
        )

    def parse(self, email: dict) -> Optional[ParsedTransaction]:
        body = email.get("body", "")
        received_at = email.get("received_at")
        fallback_date = received_at.date() if received_at else date.today()

        # Normalize whitespace
        body_clean = ' '.join(body.split())

        # Card last 4: "Credit Card XX6005"
        card_m = re.search(r'Credit Card XX(\d{4})', body_clean)
        last4 = card_m.group(1) if card_m else None

        # Amount: "INR 2,009.98"
        amount_m = re.search(r'INR\s+([\d,]+\.?\d*)', body_clean)
        if not amount_m:
            return None
        amount = Decimal(amount_m.group(1).replace(',', ''))

        # Date: "on Apr 03, 2026"
        date_m = re.search(r'on\s+(\w{3}\s+\d{2},?\s+\d{4})', body_clean)
        txn_date = fallback_date
        if date_m:
            raw_date = date_m.group(1).replace(',', '')
            try:
                txn_date = datetime.strptime(raw_date, "%b %d %Y").date()
            except ValueError:
                txn_date = fallback_date

        # Merchant: "Info: RAZ*Urbanaut."
        merchant_m = re.search(r'Info:\s*(.+?)\.', body_clean)
        merchant = merchant_m.group(1).strip() if merchant_m else None

        description = f"CC purchase at {merchant}" if merchant else "ICICI CC transaction"
        payment_source = f"ICICI CC \u2019{last4}" if last4 else "ICICI CC"

        return ParsedTransaction(
            amount=amount,
            description=description,
            merchant=merchant,
            transaction_date=txn_date,
            payment_method="Credit Card",
            category=categorize(merchant or "", description),
            reference_number=None,
            account_last4=last4,
            bank_name=self.bank_name,
            payment_source=payment_source,
        )
