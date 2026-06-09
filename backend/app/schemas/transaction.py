from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from app.models.transaction import PAYMENT_METHODS


class TransactionCreate(BaseModel):
    transaction_date: date
    amount: Decimal
    description: str
    merchant: Optional[str] = None
    category: str = Field("Others", min_length=1, max_length=100)
    payment_method: str = "Others"
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description cannot be empty")
        if len(v) > 500:
            raise ValueError("Description must be 500 characters or less")
        return v

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty")
        return v

    @field_validator("payment_method")
    @classmethod
    def payment_method_valid(cls, v: str) -> str:
        if v not in PAYMENT_METHODS:
            raise ValueError(f"Payment method must be one of: {', '.join(PAYMENT_METHODS)}")
        return v


class TransactionUpdate(BaseModel):
    transaction_date: Optional[date] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("category")
    @classmethod
    def category_not_empty_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty")
        if len(v) > 100:
            raise ValueError("Category must be 100 characters or less")
        return v

    @field_validator("payment_method")
    @classmethod
    def payment_method_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PAYMENT_METHODS:
            raise ValueError(f"Payment method must be one of: {', '.join(PAYMENT_METHODS)}")
        return v


class TransactionOut(BaseModel):
    id: int
    user_id: int
    transaction_date: date
    amount: Decimal
    description: str
    merchant: Optional[str]
    category: str
    payment_method: str
    payment_source: Optional[str] = None
    notes: Optional[str]
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    payment_source: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 50

    @field_validator("page")
    @classmethod
    def page_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def page_size_valid(cls, v: int) -> int:
        if v < 1 or v > 200:
            raise ValueError("Page size must be between 1 and 200")
        return v


class TransactionCategoryUpdate(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty")
        return v


class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[int]
    category: str = Field(..., min_length=1, max_length=100)

    @field_validator("category")
    @classmethod
    def category_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category cannot be empty")
        return v
