"""
Abstract base class for all bank email parsers.
To add a new bank: subclass BaseEmailParser and register in parser_factory.py.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class ParsedTransaction:
    amount: Decimal
    description: str
    merchant: Optional[str]
    transaction_date: date
    payment_method: str          # "UPI" | "Credit Card" | "Debit Card"
    category: str                # auto-categorized
    reference_number: Optional[str]
    account_last4: Optional[str]
    bank_name: str
    payment_source: Optional[str] = None   # e.g. "HDFC UPI", "ICICI CC ••6005"


class BaseEmailParser(ABC):

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Human-readable bank name, e.g. 'HDFC Bank'"""

    @property
    @abstractmethod
    def sender_patterns(self) -> list[str]:
        """List of sender email substrings that identify this bank."""

    @property
    @abstractmethod
    def subject_patterns(self) -> list[str]:
        """List of subject substrings that identify transaction emails."""

    @abstractmethod
    def can_parse(self, sender: str, subject: str, body: str) -> bool:
        """Return True if this parser can handle the given email."""

    @abstractmethod
    def parse(self, body: str, subject: str) -> Optional[ParsedTransaction]:
        """Parse the email body and return a ParsedTransaction, or None if parsing fails."""
