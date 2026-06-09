"""
SBI Bank debit email parser.
Parses debit alerts from cbsalerts.sbi@alerts.sbi.bank.in.
Skips non-spending emails (FD, TDS).

Sample emails:
  Your A/C XXXXX404599 has a debit by NACH of Rs 35,000.00 on 02/04/26.
  Your A/C XXXXX404599 has a debit by transfer of Rs 215.00 on 06/03/26.
"""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.parsers.base_parser import BaseEmailParser, ParsedTransaction
from app.parsers.categorizer import categorize


class SBIParser(BaseEmailParser):

    @property
    def bank_name(self) -> str:
        return "SBI"

    @property
    def sender_patterns(self) -> list[str]:
        return ["alerts.sbi.bank.in"]

    @property
    def subject_patterns(self) -> list[str]:
        return ["sbi"]

    def can_parse(self, sender: str, subject: str, body: str) -> bool:
        return "has a debit by" in (body or "").lower()

    def parse(self, email: dict) -> Optional[ParsedTransaction]:
        body = email.get("body", "")
        received_at = email.get("received_at")
        fallback_date = received_at.date() if received_at else date.today()

        # Normalize whitespace
        body_clean = ' '.join(body.split())

        # Skip non-spending emails
        if "Multi Option Dep" in body_clean or "TDS of" in body_clean:
            return None

        # Skip NACH debits — these are investments/SIPs/loan EMIs, not expenditures
        type_check = re.search(r'debit by\s+(\w+)', body_clean, re.IGNORECASE)
        if type_check and type_check.group(1).upper() == "NACH":
            return None

        # Account number: "A/C XXXXX404599" → capture digits after XXXXX, take last 4
        acc_m = re.search(r'A/C\s*XXXXX(\d{4,})', body_clean)
        if not acc_m:
            return None
        account_digits = acc_m.group(1)
        last4 = account_digits[-4:]

        # Debit type: "debit by NACH" or "debit by transfer"
        type_m = re.search(r'debit by\s+(\w+)', body_clean, re.IGNORECASE)
        debit_type = type_m.group(1).upper() if type_m else "UNKNOWN"

        # Amount: "Rs 35,000.00"
        amount_m = re.search(r'Rs\s+([\d,]+\.?\d*)', body_clean)
        if not amount_m:
            return None
        amount = Decimal(amount_m.group(1).replace(',', ''))

        # Date: "02/04/26" → DD/MM/YY
        date_m = re.search(r'on\s+(\d{2}/\d{2}/\d{2})', body_clean)
        txn_date = fallback_date
        if date_m:
            try:
                txn_date = datetime.strptime(date_m.group(1), "%d/%m/%y").date()
            except ValueError:
                txn_date = fallback_date

        description = f"SBI {debit_type} Debit"
        payment_source = f"SBI \u2019{last4}"

        return ParsedTransaction(
            amount=amount,
            description=description,
            merchant=None,
            transaction_date=txn_date,
            payment_method="Net Banking",
            category=categorize("", description),
            reference_number=None,
            account_last4=last4,
            bank_name=self.bank_name,
            payment_source=payment_source,
        )
