"""initial_schema

Revision ID: 7a9eaedc9937
Revises:
Create Date: 2026-04-05 14:20:00.114258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a9eaedc9937'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('totp_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('totp_enrolled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('gmail_token_encrypted', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token'),
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)
    op.create_index(op.f('ix_sessions_session_token'), 'sessions', ['session_token'], unique=True)
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'], unique=False)

    # Create transactions table (WITHOUT payment_source — added by migration 628c6541bc23)
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('merchant', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default=sa.text("'Others'")),
        sa.Column('payment_method', sa.String(length=50), nullable=False, server_default=sa.text("'Others'")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default=sa.text("'manual'")),
        sa.Column('email_message_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_message_id'),
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index('ix_transactions_user_date', 'transactions', ['user_id', 'transaction_date'], unique=False)
    op.create_index('ix_transactions_category', 'transactions', ['category'], unique=False)
    op.create_index('ix_transactions_payment_method', 'transactions', ['payment_method'], unique=False)

    # Create emails table
    op.create_table(
        'emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('gmail_message_id', sa.String(length=255), nullable=False),
        sa.Column('sender', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('parse_status', sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('parse_error', sa.Text(), nullable=True),
        sa.Column('bank_name', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('delete_after', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gmail_message_id'),
    )
    op.create_index(op.f('ix_emails_id'), 'emails', ['id'], unique=False)
    op.create_index('ix_emails_user_received', 'emails', ['user_id', 'received_at'], unique=False)
    op.create_index('ix_emails_parse_status', 'emails', ['parse_status'], unique=False)


def downgrade() -> None:
    # Drop in reverse dependency order (children first)
    op.drop_index('ix_emails_parse_status', table_name='emails')
    op.drop_index('ix_emails_user_received', table_name='emails')
    op.drop_index(op.f('ix_emails_id'), table_name='emails')
    op.drop_table('emails')

    op.drop_index('ix_transactions_payment_method', table_name='transactions')
    op.drop_index('ix_transactions_category', table_name='transactions')
    op.drop_index('ix_transactions_user_date', table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')

    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_index(op.f('ix_sessions_session_token'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
