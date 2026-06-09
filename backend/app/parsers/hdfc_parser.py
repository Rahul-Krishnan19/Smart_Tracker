"""
HDFC Bank email parser — supports:
  - UPI debit alerts  ("Rs.X has been debited from account XXXX to VPA ...")
  - Credit card alerts ("Rs.X is debited from your HDFC Bank Credit Card ending XXXX towards ...")
"""
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.parsers.base_parser import BaseEmailParser, ParsedTransaction
from app.parsers.categorizer import categorize


_MERCHANT_FROM_VPA_RE = re.compile(r'^([a-zA-Z]+)')


def _extract_merchant_from_vpa(vpa: str) -> str:
    """rapido522347.rzp@rxaxis → Rapido"""
    local_part = vpa.split('@')[0].split('.')[0]
    m = _MERCHANT_FROM_VPA_RE.match(local_part)
    name = m.group(1) if m else local_part
    return name.capitalize()


def _clean_merchant(name: str) -> str:
    """
    Normalize raw merchant strings from credit card alerts:
      'WWW SWIGGY IN'  → 'Swiggy'
      'BLINKIT'        → 'Blinkit'
      'Swiggy'         → 'Swiggy'
    """
    name = name.strip()
    # Strip leading WWW prefix
    name = re.sub(r'^WWW\s+', '', name, flags=re.IGNORECASE)
    # Strip trailing country suffix like ' IN', ' COM'
    name = re.sub(r'\s+(IN|COM|NET|ORG)$', '', name, flags=re.IGNORECASE)
    return name.title().strip()


def _parse_amount(raw: str) -> Decimal:
    return Decimal(raw.replace(',', ''))


def _parse_date(raw: str) -> Optional[date]:
    raw = raw.strip().rstrip(',')
    formats = [
        "%d-%m-%y",     # 27-03-26
        "%d-%m-%Y",     # 27-03-2026
        "%d/%m/%Y",     # 27/03/2026
        "%d/%m/%y",     # 27/03/26
        "%d %b %Y",     # 28 Mar 2026
        "%d %b, %Y",    # 28 Mar, 2026
        "%d %B %Y",     # 28 March 2026
        "%d %B, %Y",    # 28 March, 2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


class HDFCParser(BaseEmailParser):

    @property
    def bank_name(self) -> str:
        return "HDFC Bank"

    @property
    def sender_patterns(self) -> list[str]:
        return ["hdfcbank.com", "hdfc.com", "hdfc.bank.in", "hdfcbank.bank.in", "hdfcbank.net"]

    @property
    def subject_patterns(self) -> list[str]:
        return ["transaction alert", "debited", "upi", "credit card"]

    def can_parse(self, sender: str, subject: str, body: str) -> bool:
        sender_match = any(p in sender.lower() for p in self.sender_patterns)
        body_match = "hdfc" in body.lower()
        return sender_match or body_match

    def parse(self, email: dict) -> Optional[ParsedTransaction]:
        body = email.get("body", "")
        received_at = email.get("received_at")
        fallback_date = received_at.date() if received_at else date.today()
        body_clean = ' '.join(body.split())  # normalise whitespace

        result = self._parse_upi_debit(body_clean, fallback_date)
        if result:
            return result

        result = self._parse_credit_card_debit(body_clean, fallback_date)
        if result:
            return result

        return None

    # ------------------------------------------------------------------
    # UPI debit
    # "Rs.40.00 has been debited from account 1399 to VPA
    #  rapido522347.rzp@rxaxis Rapido on 27-03-26.
    #  Your UPI transaction reference number is 608664581748."
    # ------------------------------------------------------------------
    def _parse_upi_debit(self, body: str, fallback_date: date) -> Optional[ParsedTransaction]:
        # If this is a credit card email that happens to use "has been debited", skip it
        if re.search(r'credit card', body, re.IGNORECASE):
            return None

        amount_m = re.search(
            r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s+has been debited',
            body, re.IGNORECASE
        )
        if not amount_m:
            return None

        amount = _parse_amount(amount_m.group(1))

        acc_m = re.search(r'(?:from\s+)?account\s+(\d+)', body, re.IGNORECASE)
        account_last4 = acc_m.group(1)[-4:] if acc_m else None

        # "to VPA <vpa> <Merchant Name> on <date>"
        vpa_block_m = re.search(
            r'to\s+VPA\s+(\S+)\s+([\w\s]+?)\s+on\s+'
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            body, re.IGNORECASE
        )

        vpa = None
        merchant = None
        txn_date = None

        if vpa_block_m:
            vpa = vpa_block_m.group(1)
            merchant_raw = vpa_block_m.group(2).strip()
            date_raw = vpa_block_m.group(3)
            merchant = merchant_raw if merchant_raw else _extract_merchant_from_vpa(vpa)
            txn_date = _parse_date(date_raw)
        else:
            vpa_m = re.search(r'[\w.\-]+@[\w]+', body)
            if vpa_m:
                vpa = vpa_m.group(0)
                merchant = _extract_merchant_from_vpa(vpa)
            date_m = re.search(r'on\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', body, re.IGNORECASE)
            if date_m:
                txn_date = _parse_date(date_m.group(1))

        if txn_date is None:
            txn_date = fallback_date

        merchant = merchant or (vpa or "Unknown")
        description = f"UPI to {vpa}" if vpa else "UPI transaction"

        ref_m = re.search(r'reference\s+number\s+is\s+(\d+)', body, re.IGNORECASE)
        reference = ref_m.group(1) if ref_m else None

        return ParsedTransaction(
            amount=amount,
            description=description,
            merchant=merchant,
            transaction_date=txn_date,
            payment_method="UPI",
            category=categorize(merchant, description),
            reference_number=reference,
            account_last4=account_last4,
            bank_name=self.bank_name,
            payment_source="HDFC UPI",
        )

    # ------------------------------------------------------------------
    # Credit card debit
    # "Rs.1158.00 is debited from your HDFC Bank Credit Card ending 6054
    #  towards WWW SWIGGY IN on 28 Mar, 2026 at 17:40:38."
    # ------------------------------------------------------------------
    def _parse_credit_card_debit(self, body: str, fallback_date: date) -> Optional[ParsedTransaction]:
        amount_m = re.search(
            r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s+(?:is|has been) debited from your HDFC Bank Credit Card',
            body, re.IGNORECASE
        )
        if not amount_m:
            return None

        amount = _parse_amount(amount_m.group(1))

        card_m = re.search(r'Credit Card ending\s+(\d+)', body, re.IGNORECASE)
        account_last4 = card_m.group(1)[-4:] if card_m else None

        # "towards <MERCHANT> on <DD Mon, YYYY> at <HH:MM:SS>"
        merchant_date_m = re.search(
            r'towards\s+(.+?)\s+on\s+(\d{1,2}\s+\w{3},?\s+\d{4})\s+at',
            body, re.IGNORECASE
        )

        merchant = None
        txn_date = None

        if merchant_date_m:
            merchant = _clean_merchant(merchant_date_m.group(1))
            txn_date = _parse_date(merchant_date_m.group(2))
        else:
            # Fallback: find date without time
            date_m = re.search(r'on\s+(\d{1,2}\s+\w{3},?\s+\d{4})', body, re.IGNORECASE)
            if date_m:
                txn_date = _parse_date(date_m.group(1))

        if txn_date is None:
            txn_date = fallback_date

        merchant = merchant or "Unknown"
        description = f"CC purchase at {merchant}"

        return ParsedTransaction(
            amount=amount,
            description=description,
            merchant=merchant,
            transaction_date=txn_date,
            payment_method="Credit Card",
            category=categorize(merchant, description),
            reference_number=None,
            account_last4=account_last4,
            bank_name=self.bank_name,
            payment_source=f"HDFC CC \u2019{account_last4}" if account_last4 else "HDFC CC",
        )
