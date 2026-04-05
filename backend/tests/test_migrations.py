"""
Tests for Alembic migrations.

These tests verify that:
  - alembic upgrade head runs cleanly on a fresh DB
  - the alembic_version table is created
  - the payment_source column exists in the transactions table
  - payment_source is nullable (allows NULL inserts)
"""
import os
import sqlite3
import tempfile

import pytest


def _get_alembic_ini_path():
    """Locate alembic.ini relative to this file (backend/alembic.ini)."""
    tests_dir = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(tests_dir, "..", "alembic.ini"))


def test_alembic_upgrade_head():
    """
    Run alembic upgrade head against a fresh temp SQLite DB and verify:
    - alembic_version table exists (confirms Alembic is managing the schema)
    - transactions table contains a payment_source column
    """
    from alembic.config import Config
    from alembic import command

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_migration.db")
        db_url = f"sqlite:///{db_path}"

        ini_path = _get_alembic_ini_path()
        cfg = Config(ini_path)
        cfg.set_main_option("sqlalchemy.url", db_url)

        # Run all migrations on the fresh DB
        command.upgrade(cfg, "head")

        # Inspect the resulting schema
        conn = sqlite3.connect(db_path)
        try:
            # alembic_version table must exist
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "alembic_version" in tables, (
                f"alembic_version table missing; found tables: {tables}"
            )
            assert "transactions" in tables, (
                f"transactions table missing; found tables: {tables}"
            )

            # payment_source column must exist in transactions
            cols = [
                row[1]
                for row in conn.execute("PRAGMA table_info(transactions)").fetchall()
            ]
            assert "payment_source" in cols, (
                f"payment_source column missing from transactions; found: {cols}"
            )
        finally:
            conn.close()


def test_payment_source_column_nullable():
    """
    After upgrade head, inserting a transaction row with payment_source=NULL
    must succeed (column is nullable).
    """
    from alembic.config import Config
    from alembic import command

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_nullable.db")
        db_url = f"sqlite:///{db_path}"

        ini_path = _get_alembic_ini_path()
        cfg = Config(ini_path)
        cfg.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(cfg, "head")

        conn = sqlite3.connect(db_path)
        try:
            # Insert a minimal user first (FK constraint)
            conn.execute(
                "INSERT INTO users (id, email, hashed_password, is_active, is_verified) "
                "VALUES (1, 'test@example.com', 'hash', 1, 1)"
            )
            # Insert transaction with payment_source explicitly NULL
            conn.execute(
                "INSERT INTO transactions "
                "(user_id, transaction_date, amount, description, category, payment_method, source, payment_source) "
                "VALUES (1, '2026-04-01', 100.00, 'Test', 'Others', 'UPI', 'manual', NULL)"
            )
            conn.commit()

            row = conn.execute(
                "SELECT payment_source FROM transactions WHERE user_id=1"
            ).fetchone()
            assert row is not None
            assert row[0] is None, f"Expected NULL payment_source, got {row[0]}"
        finally:
            conn.close()
