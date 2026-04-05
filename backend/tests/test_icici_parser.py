"""
Tests for ICICIParser — RED phase (parser not yet created).

These tests will be SKIPPED until Plan 03 creates ICICIParser.
Once Plan 03 is complete they become GREEN.
"""
from decimal import Decimal
from datetime import date

import pytest

try:
    from app.parsers.icici_parser import ICICIParser
    ICICI_AVAILABLE = True
except ImportError:
    ICICIParser = None
    ICICI_AVAILABLE = False


@pytest.fixture
def parser():
    if not ICICI_AVAILABLE:
        pytest.skip("ICICIParser not yet created")
    return ICICIParser()


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_can_parse_icici(parser, sample_icici_cc_email):
    """ICICIParser recognises ICICI credit card transaction emails."""
    result = parser.can_parse(
        sample_icici_cc_email["sender"],
        sample_icici_cc_email["subject"],
        sample_icici_cc_email["body"],
    )
    assert result is True


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_can_parse_rejects_other(parser):
    """ICICIParser must not accept HDFC emails."""
    result = parser.can_parse(
        "alerts@hdfcbank.net",
        "Transaction",
        "HDFC debit",
    )
    assert result is False


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_parse_amount(parser, sample_icici_cc_email):
    parsed = parser.parse(sample_icici_cc_email)
    assert parsed is not None
    assert parsed.amount == Decimal("2009.98")


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_parse_date(parser, sample_icici_cc_email):
    parsed = parser.parse(sample_icici_cc_email)
    assert parsed is not None
    assert parsed.transaction_date == date(2026, 4, 3)


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_parse_merchant(parser, sample_icici_cc_email):
    parsed = parser.parse(sample_icici_cc_email)
    assert parsed is not None
    assert parsed.merchant == "RAZ*Urbanaut"


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_payment_source(parser, sample_icici_cc_email):
    parsed = parser.parse(sample_icici_cc_email)
    assert parsed is not None
    assert parsed.payment_source == "ICICI CC \u20196005"


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_payment_method(parser, sample_icici_cc_email):
    parsed = parser.parse(sample_icici_cc_email)
    assert parsed is not None
    assert parsed.payment_method == "Credit Card"


@pytest.mark.skipif(not ICICI_AVAILABLE, reason="ICICIParser not yet created")
def test_bank_name(parser, sample_icici_cc_email):
    parsed = parser.parse(sample_icici_cc_email)
    assert parsed is not None
    assert parsed.bank_name == "ICICI Bank"
