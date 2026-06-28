from __future__ import annotations
"""
Merchant normalization agent (Agent 3).

Bank emails spell the same merchant many ways ("AMAZON IN", "Amazon",
"AMAZON.IN PAYMENTS"). This service groups raw merchant strings that look
similar and asks Gemini to pick one canonical display name per group, then
persists the mapping in `merchant_canonical_map`.

Analytics merchant breakdown LEFT JOINs that table so spend rolls up under the
canonical name. Run after each email sync (see email_sync_service post-sync hook).
"""
import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.merchant_canonical import MerchantCanonicalMap
from app.agents.llm_client import ask_text

logger = logging.getLogger(__name__)

# Number of leading characters used for rough similarity grouping.
_GROUP_PREFIX_LEN = 5

_PROMPT_TEMPLATE = """These are merchant name variants from bank transactions:
{names}

Pick the best canonical display name from this list. Return just the name, \
nothing else."""


def _unmapped_merchants(db: Session, user_id: int) -> list[str]:
    """Distinct non-null merchant names for this user lacking a canonical row."""
    mapped_subq = (
        db.query(MerchantCanonicalMap.raw_merchant)
        .filter(MerchantCanonicalMap.user_id == user_id)
        .subquery()
    )
    rows = (
        db.query(Transaction.merchant)
        .filter(
            Transaction.user_id == user_id,
            Transaction.merchant.isnot(None),
            Transaction.merchant.notin_(db.query(mapped_subq.c.raw_merchant)),
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0] and r[0].strip()]


def _group_by_prefix(merchants: list[str]) -> dict[str, list[str]]:
    """Group merchants sharing the same case-insensitive first N characters."""
    groups: dict[str, list[str]] = defaultdict(list)
    for name in merchants:
        key = name.strip().lower()[:_GROUP_PREFIX_LEN]
        groups[key].append(name)
    return groups


def _choose_canonical(variants: list[str]) -> str:
    """Pick the canonical name for a group of 2+ variants via the LLM.

    Falls back to the first variant if the LLM is unavailable or returns
    something not in the candidate list.
    """
    prompt = _PROMPT_TEMPLATE.format(names="\n".join(f"- {v}" for v in variants))
    answer = ask_text(prompt)
    if not answer:
        return variants[0]

    answer = answer.strip().strip("-").strip()
    # Only trust the answer if it matches one of the supplied variants.
    lookup = {v.strip().lower(): v for v in variants}
    return lookup.get(answer.lower(), answer if answer else variants[0])


def normalize_merchants(db: Session, user_id: int) -> int:
    """Build canonical mappings for any unmapped merchants of `user_id`.

    Returns the number of new mapping rows inserted. Never raises — on error it
    rolls back and returns 0 so callers (post-sync hook) are unaffected.
    """
    try:
        candidates = _unmapped_merchants(db, user_id)
        if not candidates:
            return 0

        new_rows: list[MerchantCanonicalMap] = []
        for variants in _group_by_prefix(candidates).values():
            if len(variants) >= 2:
                canonical = _choose_canonical(variants)
            else:
                # Single-member group: it is its own canonical name.
                canonical = variants[0]

            for raw in variants:
                new_rows.append(
                    MerchantCanonicalMap(
                        user_id=user_id,
                        raw_merchant=raw,
                        canonical_merchant=canonical,
                    )
                )

        if new_rows:
            db.bulk_save_objects(new_rows)
            db.commit()
        return len(new_rows)
    except Exception as e:
        logger.error("Merchant normalization failed for user %s: %s", user_id, e)
        db.rollback()
        return 0
