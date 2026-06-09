"""
Global bank registry — single source of truth for all supported banks.

To add a new bank:
  1. Create backend/app/parsers/{bank}_parser.py  (subclass BaseEmailParser)
  2. Add an entry to BANK_REGISTRY below
  3. Import and instantiate the parser in parser_factory.py

Each entry: (bank_name, sender_pattern)
Multiple entries per bank are fine — one per distinct sender domain/address.
"""
from typing import NamedTuple


class BankEntry(NamedTuple):
    bank_name: str
    sender_pattern: str  # substring matched against sender email (lowercase)


# ---------------------------------------------------------------------------
# Add new banks here — these become the default sources seeded for every user
# ---------------------------------------------------------------------------
BANK_REGISTRY: list[BankEntry] = [
    # HDFC Bank
    BankEntry("HDFC Bank", "hdfcbank.com"),
    BankEntry("HDFC Bank", "hdfc.com"),
    BankEntry("HDFC Bank", "hdfcbank.bank.in"),

    # ICICI Bank
    BankEntry("ICICI Bank", "icicibank.com"),

    # State Bank of India
    BankEntry("SBI", "alerts.sbi.bank.in"),

    # --- Add parsers + entries below as new banks are onboarded ---

    # Axis Bank                 → create axis_parser.py first
    # BankEntry("Axis Bank",   "axisbank.com"),

    # Kotak Mahindra Bank       → create kotak_parser.py first
    # BankEntry("Kotak Bank",  "kotak.com"),
    # BankEntry("Kotak Bank",  "kotakbank.com"),

    # IDFC First Bank           → create idfc_parser.py first
    # BankEntry("IDFC First",  "idfcfirstbank.com"),

    # Yes Bank                  → create yes_parser.py first
    # BankEntry("Yes Bank",    "yesbank.in"),

    # IndusInd Bank             → create indusind_parser.py first
    # BankEntry("IndusInd",    "indusind.com"),
]
