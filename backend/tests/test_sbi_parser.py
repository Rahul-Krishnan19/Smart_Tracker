"""
Tests for SBIParser — RED phase (parser not yet created).

These tests will be SKIPPED until Plan 03 creates SBIParser.
Once Plan 03 is complete they become GREEN.
"""
from decimal import Decimal
from datetime import date

import pytest

try:
    from app.parsers.sbi_parser import SBIParser
    SBI_AVAILABLE = True
except ImportError:
    SBIParser = None
    SBI_AVAILABLE = False


@pytest.fixture
def parser():
    if not SBI_AVAILABLE:
        pytest.skip("SBIParser not yet created")
    return SBIParser()


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_can_parse_sbi(parser, sample_sbi_nach_email):
    """SBIParser recognises SBI debit alerts."""
    result = parser.can_parse(
        sample_sbi_nach_email["sender"],
        sample_sbi_nach_email["subject"],
        sample_sbi_nach_email["body"],
    )
    assert result is True


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_can_parse_rejects_other(parser):
    """SBIParser must not accept HDFC emails."""
    result = parser.can_parse(
        "alerts@hdfcbank.net",
        "Transaction",
        "HDFC debit",
    )
    assert result is False


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_parse_nach_amount(parser, sample_sbi_nach_email):
    parsed = parser.parse(sample_sbi_nach_email)
    assert parsed is not None
    assert parsed.amount == Decimal("35000.00")


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_parse_nach_date(parser, sample_sbi_nach_email):
    parsed = parser.parse(sample_sbi_nach_email)
    assert parsed is not None
    assert parsed.transaction_date == date(2026, 4, 2)


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_parse_description_nach(parser, sample_sbi_nach_email):
    parsed = parser.parse(sample_sbi_nach_email)
    assert parsed is not None
    assert parsed.description == "SBI NACH Debit"


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_parse_description_transfer(parser, sample_sbi_transfer_email):
    parsed = parser.parse(sample_sbi_transfer_email)
    assert parsed is not None
    assert parsed.description == "SBI TRANSFER Debit"


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_payment_source(parser, sample_sbi_nach_email):
    parsed = parser.parse(sample_sbi_nach_email)
    assert parsed is not None
    assert parsed.payment_source == "SBI \u20194599"


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_payment_method(parser, sample_sbi_nach_email):
    parsed = parser.parse(sample_sbi_nach_email)
    assert parsed is not None
    assert parsed.payment_method == "Net Banking"


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_merchant_is_none(parser, sample_sbi_nach_email):
    parsed = parser.parse(sample_sbi_nach_email)
    assert parsed is not None
    assert parsed.merchant is None


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_fd_email_skipped(parser, sample_sbi_fd_email):
    """FD creation emails must be ignored (return None)."""
    parsed = parser.parse(sample_sbi_fd_email)
    assert parsed is None


@pytest.mark.skipif(not SBI_AVAILABLE, reason="SBIParser not yet created")
def test_tds_email_skipped(parser, sample_sbi_tds_email):
    """TDS deduction emails must be ignored (return None)."""
    parsed = parser.parse(sample_sbi_tds_email)
    assert parsed is None
