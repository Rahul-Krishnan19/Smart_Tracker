"""
Parser factory — routes emails to the correct bank parser.
To add a new bank: instantiate its parser here and add to PARSERS list.
"""
from typing import Optional
from app.parsers.base_parser import BaseEmailParser, ParsedTransaction
from app.parsers.hdfc_parser import HDFCParser

PARSERS: list[BaseEmailParser] = [
    HDFCParser(),
    # ICICIParser(),   # Phase 3
    # SBIParser(),     # Phase 3
    # FlashParser(),   # Phase 3
]


def get_parser(sender: str, subject: str, body: str) -> Optional[BaseEmailParser]:
    """Return the first parser that claims it can handle this email."""
    for parser in PARSERS:
        if parser.can_parse(sender, subject, body):
            return parser
    return None


def parse_email(email: dict) -> Optional[ParsedTransaction]:
    """Convenience: get parser and parse in one call. Returns None if no parser matches."""
    parser = get_parser(
        sender=email.get("sender", ""),
        subject=email.get("subject", ""),
        body=email.get("body", ""),
    )
    if parser is None:
        return None
    return parser.parse(email)
