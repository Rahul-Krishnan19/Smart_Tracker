"""
Shared pytest fixtures for Phase 3 parser and migration tests.
"""
from datetime import datetime, date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


# ---------------------------------------------------------------------------
# Sample email dicts — real bank email bodies captured during validation
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_hdfc_upi_email():
    return {
        "id": "msg_hdfc_upi_1",
        "sender": "alerts@hdfcbank.net",
        "subject": "Transaction Alert",
        "body": (
            "Rs.40.00 has been debited from account 1399 to VPA "
            "rapido522347.rzp@rxaxis Rapido on 27-03-26. "
            "Your UPI transaction reference number is 608664581748."
        ),
        "received_at": datetime(2026, 3, 27, 10, 0, 0),
    }


@pytest.fixture
def sample_hdfc_cc_email():
    return {
        "id": "msg_hdfc_cc_1",
        "sender": "alerts@hdfcbank.net",
        "subject": "Transaction Alert",
        "body": (
            "Rs.1158.00 is debited from your HDFC Bank Credit Card ending 6054 "
            "towards WWW SWIGGY IN on 28 Mar, 2026 at 17:40:38."
        ),
        "received_at": datetime(2026, 3, 28, 17, 40, 38),
    }


@pytest.fixture
def sample_icici_cc_email():
    return {
        "id": "msg_icici_1",
        "sender": "credit_cards@icicibank.com",
        "subject": "ICICI Bank Credit Card Transaction",
        "body": (
            "Your ICICI Bank Credit Card XX6005 has been used for a transaction of "
            "INR 2,009.98 on Apr 03, 2026 at 04:53:52. Info: RAZ*Urbanaut."
        ),
        "received_at": datetime(2026, 4, 3, 4, 53, 52),
    }


@pytest.fixture
def sample_sbi_nach_email():
    return {
        "id": "msg_sbi_1",
        "sender": "cbsalerts.sbi@alerts.sbi.bank.in",
        "subject": "SBI Transaction Alert",
        "body": (
            "Your A/C XXXXX404599 has a debit by NACH of Rs 35,000.00 on 02/04/26. "
            "Avl Bal Rs 22,80,612.96."
        ),
        "received_at": datetime(2026, 4, 2, 8, 0, 0),
    }


@pytest.fixture
def sample_sbi_transfer_email():
    return {
        "id": "msg_sbi_2",
        "sender": "cbsalerts.sbi@alerts.sbi.bank.in",
        "subject": "SBI Transaction Alert",
        "body": (
            "Your A/C XXXXX404599 has a debit by transfer of Rs 215.00 on 06/03/26. "
            "Avl Bal Rs 21,82,299.06."
        ),
        "received_at": datetime(2026, 3, 6, 9, 0, 0),
    }


@pytest.fixture
def sample_sbi_fd_email():
    return {
        "id": "msg_sbi_fd",
        "sender": "cbsalerts.sbi@alerts.sbi.bank.in",
        "subject": "SBI Alert",
        "body": (
            "Multi Option Dep (FD) of Rs 75,000.00 created on 05/03/26 "
            "in your A/C XXXXX404599."
        ),
        "received_at": datetime(2026, 3, 5, 10, 0, 0),
    }


@pytest.fixture
def sample_sbi_tds_email():
    return {
        "id": "msg_sbi_tds",
        "sender": "cbsalerts.sbi@alerts.sbi.bank.in",
        "subject": "SBI Alert",
        "body": "TDS of INR 3.00 deducted for interest paid on A/C No XXXXX404599.",
        "received_at": datetime(2026, 3, 5, 10, 0, 0),
    }


# ---------------------------------------------------------------------------
# In-memory SQLite DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite engine, yield a Session, then drop all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
