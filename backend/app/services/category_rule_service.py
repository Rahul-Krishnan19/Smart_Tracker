"""
Category rule service — user-defined DB keyword rules for transaction categorization.

Per D-04: categorize() in categorizer.py remains stateless (pure function).
User rules are applied as a separate override step (apply_user_rules) after parsing.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.category_rule import CategoryRule
from app.models.transaction import Transaction


def apply_user_rules(
    db: Session,
    user_id: int,
    merchant: str,
    description: str,
) -> Optional[str]:
    """
    Check user's DB-backed keyword rules.

    Searches combined merchant + description text for any matching keyword
    using 'contains' match type.

    Returns the matched category string if a rule matches, else None.
    Caller should override parsed.category only if result is not None.
    """
    text = ((merchant or "") + " " + (description or "")).lower()
    rules = db.query(CategoryRule).filter(
        CategoryRule.user_id == user_id,
        CategoryRule.match_type == "contains",
    ).all()
    for rule in rules:
        if rule.keyword.lower() in text:
            return rule.category
    return None


def upsert_rule_and_bulk_update(
    db: Session,
    user_id: int,
    merchant: str,
    new_category: str,
) -> int:
    """
    Create or update a CategoryRule for this merchant keyword AND bulk-update
    all of the user's transactions from this merchant to the new category.

    Uses a single commit to keep rule + transaction updates atomic.

    Returns the count of transactions updated.
    """
    existing = db.query(CategoryRule).filter(
        CategoryRule.user_id == user_id,
        CategoryRule.keyword == merchant.lower(),
        CategoryRule.match_type == "contains",
    ).first()

    if existing:
        existing.category = new_category
    else:
        rule = CategoryRule(
            user_id=user_id,
            keyword=merchant.lower(),
            match_type="contains",
            category=new_category,
        )
        db.add(rule)

    updated = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.merchant == merchant,
    ).update({"category": new_category}, synchronize_session=False)

    db.commit()
    return updated
