"""
Tests for CategoryRule model, apply_user_rules service, and extended CATEGORIES.
Phase 5, Plan 01 - Task 1
"""
import pytest
from datetime import date, datetime
from decimal import Decimal

from app.models.transaction import CATEGORIES, Transaction
from app.models.user import User


class TestExtendedCategories:
    def test_categories_extended(self):
        """CAT-03: CATEGORIES must include Subscriptions, Utilities, Travel."""
        assert "Subscriptions" in CATEGORIES
        assert "Utilities" in CATEGORIES
        assert "Travel" in CATEGORIES

    def test_others_still_present(self):
        """Others must remain as a valid category."""
        assert "Others" in CATEGORIES

    def test_original_categories_preserved(self):
        """Original 9 categories must still be present."""
        for cat in ["Rent", "Groceries", "Shopping", "Electricity",
                    "Food & Dining", "Transport", "Entertainment", "Healthcare"]:
            assert cat in CATEGORIES

    def test_total_category_count(self):
        """Should have 12 categories (9 original + 3 new)."""
        assert len(CATEGORIES) == 12


class TestCategoryRuleModel:
    def test_category_rule_can_be_created(self, in_memory_db):
        """CategoryRule model can be persisted to DB."""
        from app.models.category_rule import CategoryRule
        rule = CategoryRule(
            user_id=1,
            keyword="swiggy",
            match_type="contains",
            category="Food & Dining",
        )
        in_memory_db.add(rule)
        in_memory_db.commit()
        in_memory_db.refresh(rule)
        assert rule.id is not None
        assert rule.user_id == 1
        assert rule.keyword == "swiggy"
        assert rule.match_type == "contains"
        assert rule.category == "Food & Dining"

    def test_category_rule_default_match_type(self, in_memory_db):
        """match_type defaults to 'contains'."""
        from app.models.category_rule import CategoryRule
        rule = CategoryRule(
            user_id=1,
            keyword="amazon",
            category="Shopping",
        )
        in_memory_db.add(rule)
        in_memory_db.commit()
        in_memory_db.refresh(rule)
        assert rule.match_type == "contains"


class TestApplyUserRules:
    def test_user_rule_takes_precedence(self, in_memory_db):
        """CAT-04: User-defined rule overrides default categorization."""
        from app.models.category_rule import CategoryRule
        from app.services.category_rule_service import apply_user_rules

        rule = CategoryRule(
            user_id=1,
            keyword="swiggy",
            match_type="contains",
            category="Subscriptions",
        )
        in_memory_db.add(rule)
        in_memory_db.commit()

        result = apply_user_rules(in_memory_db, 1, "Swiggy", "food order")
        assert result == "Subscriptions"

    def test_no_rule_match_returns_none(self, in_memory_db):
        """CAT-04: Returns None when no rule matches."""
        from app.services.category_rule_service import apply_user_rules

        result = apply_user_rules(in_memory_db, 1, "UnknownMerchant", "some desc")
        assert result is None

    def test_rule_matches_in_description(self, in_memory_db):
        """apply_user_rules checks both merchant and description."""
        from app.models.category_rule import CategoryRule
        from app.services.category_rule_service import apply_user_rules

        rule = CategoryRule(
            user_id=1,
            keyword="netflix",
            match_type="contains",
            category="Subscriptions",
        )
        in_memory_db.add(rule)
        in_memory_db.commit()

        result = apply_user_rules(in_memory_db, 1, "", "netflix monthly subscription")
        assert result == "Subscriptions"

    def test_rule_is_user_scoped(self, in_memory_db):
        """Rules for user_id=2 should not match for user_id=1."""
        from app.models.category_rule import CategoryRule
        from app.services.category_rule_service import apply_user_rules

        rule = CategoryRule(
            user_id=2,
            keyword="swiggy",
            match_type="contains",
            category="Subscriptions",
        )
        in_memory_db.add(rule)
        in_memory_db.commit()

        result = apply_user_rules(in_memory_db, 1, "Swiggy", "food order")
        assert result is None


class TestUpsertRuleAndBulkUpdate:
    def _make_user(self, db, user_id=1):
        """Create a minimal User for FK constraints."""
        from app.models.user import User
        user = User(
            id=user_id,
            username=f"testuser{user_id}",
            email=f"test{user_id}@example.com",
            password_hash="hashedpassword",
            totp_secret_encrypted=None,
            totp_enrolled=False,
        )
        db.add(user)
        db.flush()
        return user

    def _make_transaction(self, db, user_id, merchant, category):
        """Create a minimal Transaction row."""
        tx = Transaction(
            user_id=user_id,
            transaction_date=date(2026, 1, 1),
            amount=Decimal("100.00"),
            description=f"Payment to {merchant}",
            merchant=merchant,
            category=category,
            payment_method="UPI",
            source="manual",
        )
        db.add(tx)
        db.flush()
        return tx

    def test_upsert_creates_rule_and_updates_transactions(self, in_memory_db):
        """TXN-11: upsert creates rule and bulk-updates all matching transactions."""
        from app.services.category_rule_service import upsert_rule_and_bulk_update
        from app.models.category_rule import CategoryRule

        self._make_user(in_memory_db)
        tx1 = self._make_transaction(in_memory_db, 1, "Swiggy", "Food & Dining")
        tx2 = self._make_transaction(in_memory_db, 1, "Swiggy", "Food & Dining")
        tx3 = self._make_transaction(in_memory_db, 1, "Swiggy", "Food & Dining")
        in_memory_db.commit()

        updated = upsert_rule_and_bulk_update(in_memory_db, 1, "Swiggy", "Subscriptions")

        assert updated == 3
        in_memory_db.refresh(tx1)
        in_memory_db.refresh(tx2)
        in_memory_db.refresh(tx3)
        assert tx1.category == "Subscriptions"
        assert tx2.category == "Subscriptions"
        assert tx3.category == "Subscriptions"

        rule = in_memory_db.query(CategoryRule).filter(
            CategoryRule.user_id == 1,
            CategoryRule.keyword == "swiggy",
        ).first()
        assert rule is not None
        assert rule.category == "Subscriptions"

    def test_upsert_updates_existing_rule(self, in_memory_db):
        """upsert_rule_and_bulk_update updates category of existing rule."""
        from app.services.category_rule_service import upsert_rule_and_bulk_update
        from app.models.category_rule import CategoryRule

        self._make_user(in_memory_db)
        existing_rule = CategoryRule(
            user_id=1, keyword="swiggy", match_type="contains", category="Food & Dining"
        )
        in_memory_db.add(existing_rule)
        in_memory_db.commit()

        upsert_rule_and_bulk_update(in_memory_db, 1, "Swiggy", "Subscriptions")

        in_memory_db.refresh(existing_rule)
        assert existing_rule.category == "Subscriptions"
        count = in_memory_db.query(CategoryRule).filter(
            CategoryRule.user_id == 1,
            CategoryRule.keyword == "swiggy",
        ).count()
        assert count == 1  # No duplicate rules created

    def test_upsert_only_affects_specified_merchant(self, in_memory_db):
        """Bulk update does not change transactions for other merchants."""
        from app.services.category_rule_service import upsert_rule_and_bulk_update

        self._make_user(in_memory_db)
        self._make_transaction(in_memory_db, 1, "Swiggy", "Food & Dining")
        tx_amazon = self._make_transaction(in_memory_db, 1, "Amazon", "Shopping")
        in_memory_db.commit()
        amazon_id = tx_amazon.id

        upsert_rule_and_bulk_update(in_memory_db, 1, "Swiggy", "Subscriptions")

        amazon_tx = in_memory_db.query(Transaction).filter(Transaction.id == amazon_id).first()
        assert amazon_tx.category == "Shopping"


class TestSchemaExtensions:
    def test_transaction_out_has_payment_source(self):
        """PAY-02: TransactionOut schema includes payment_source field."""
        from app.schemas.transaction import TransactionOut
        fields = TransactionOut.model_fields
        assert "payment_source" in fields

    def test_transaction_filters_has_payment_source(self):
        """TXN-05: TransactionFilters accepts payment_source."""
        from app.schemas.transaction import TransactionFilters
        fields = TransactionFilters.model_fields
        assert "payment_source" in fields

    def test_transaction_filters_has_amount_range(self):
        """TXN-05: TransactionFilters accepts min_amount and max_amount."""
        from app.schemas.transaction import TransactionFilters
        fields = TransactionFilters.model_fields
        assert "min_amount" in fields
        assert "max_amount" in fields

    def test_transaction_category_update_exists(self):
        """TransactionCategoryUpdate schema exists with correct fields.

        Note: `apply_to_merchant` was removed — rules are now ALWAYS persisted
        whenever the transaction has a merchant.
        """
        from app.schemas.transaction import TransactionCategoryUpdate
        fields = TransactionCategoryUpdate.model_fields
        assert "category" in fields
        assert "apply_to_merchant" not in fields

    def test_transaction_category_update_rejects_empty_category(self):
        """TransactionCategoryUpdate rejects empty/whitespace categories.

        Custom categories are allowed (any non-empty string up to 100 chars),
        so we no longer reject names that aren't in the predefined CATEGORIES list.
        """
        from app.schemas.transaction import TransactionCategoryUpdate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            TransactionCategoryUpdate(category="")
        with pytest.raises(pydantic.ValidationError):
            TransactionCategoryUpdate(category="   ")

    def test_transaction_category_update_accepts_valid_category(self):
        """TransactionCategoryUpdate accepts valid categories including new ones."""
        from app.schemas.transaction import TransactionCategoryUpdate
        obj = TransactionCategoryUpdate(category="Subscriptions")
        assert obj.category == "Subscriptions"
        obj2 = TransactionCategoryUpdate(category="Utilities")
        assert obj2.category == "Utilities"
        obj3 = TransactionCategoryUpdate(category="Travel")
        assert obj3.category == "Travel"

    def test_bulk_categorize_request_exists(self):
        """BulkCategorizeRequest schema exists with correct fields."""
        from app.schemas.transaction import BulkCategorizeRequest
        fields = BulkCategorizeRequest.model_fields
        assert "transaction_ids" in fields
        assert "category" in fields

    def test_bulk_categorize_request_rejects_empty_category(self):
        """BulkCategorizeRequest rejects empty categories.

        Custom categories are allowed (any non-empty string), so the schema
        only enforces non-emptiness rather than membership in CATEGORIES.
        """
        from app.schemas.transaction import BulkCategorizeRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            BulkCategorizeRequest(transaction_ids=[1, 2], category="")
