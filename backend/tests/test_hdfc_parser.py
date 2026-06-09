"""
Tests for HDFCParser — RED phase.

These tests verify the updated HDFC parser behaviour introduced in Plan 02:
  - parse() accepts an email dict (new signature)
  - payment_source field is populated on ParsedTransaction
  - Date fallback uses email received_at instead of date.today()

Tests will FAIL (RED) until Plan 02 updates the HDFC parser.
"""
from datetime import datetime, date
from decimal import Decimal

import pytest

from app.parsers.hdfc_parser import HDFCParser


@pytest.fixture
def parser():
    return HDFCParser()


def test_payment_source_upi(parser, sample_hdfc_upi_email):
    """After Plan 02: parse(email_dict) sets payment_source = 'HDFC UPI'."""
    parsed = parser.parse(sample_hdfc_upi_email)
    assert parsed is not None
    assert parsed.payment_source == "HDFC UPI"


def test_payment_source_cc(parser, sample_hdfc_cc_email):
    """After Plan 02: parse(email_dict) sets payment_source = 'HDFC CC ••6054'."""
    parsed = parser.parse(sample_hdfc_cc_email)
    assert parsed is not None
    assert parsed.payment_source == "HDFC CC \u20196054"


def test_date_fallback_uses_received_at(parser):
    """
    When the email body has an unparseable date, the parser should use
    received_at from the email dict rather than date.today().
    """
    email = {
        "id": "msg_hdfc_bad_date",
        "sender": "alerts@hdfcbank.net",
        "subject": "Transaction Alert",
        "body": (
            "Rs.100.00 has been debited from account 1234 to VPA "
            "merchant@upi Unknown on BADDATE. "
            "Your UPI transaction reference number is 999."
        ),
        "received_at": datetime(2026, 1, 15, 12, 0, 0),
    }
    parsed = parser.parse(email)
    assert parsed is not None
    assert parsed.transaction_date == date(2026, 1, 15), (
        f"Expected date(2026, 1, 15) from received_at, got {parsed.transaction_date}"
    )


def test_parse_accepts_email_dict(parser, sample_hdfc_upi_email):
    """parse() should accept an email dict (new unified signature from Plan 02)."""
    parsed = parser.parse(sample_hdfc_upi_email)
    assert parsed is not None
    assert parsed.amount == Decimal("40.00")
    assert parsed.bank_name == "HDFC Bank"


def test_cc_has_been_debited_not_misclassified_as_upi(parser, sample_hdfc_cc_has_been_debited_email):
    """CC emails using 'has been debited' must NOT be tagged as UPI (regression for 661 Rs / 28 Apr)."""
    parsed = parser.parse(sample_hdfc_cc_has_been_debited_email)
    assert parsed is not None
    assert parsed.payment_method == "Credit Card", (
        f"Expected Credit Card, got {parsed.payment_method}"
    )
    assert parsed.account_last4 == "6054"
    assert parsed.payment_source == "HDFC CC ’6054"
    assert parsed.amount == Decimal("661.00")
    assert parsed.transaction_date == date(2026, 4, 28)
