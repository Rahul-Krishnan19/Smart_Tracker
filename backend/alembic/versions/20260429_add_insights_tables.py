"""add_insights_tables

Revision ID: b1f4e7a2c901
Revises: 866afeee2c98
Create Date: 2026-04-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b1f4e7a2c901'
down_revision: Union[str, None] = '866afeee2c98'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'anomalies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('rule_name', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='new'),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('dismissed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_anomalies_id'), 'anomalies', ['id'], unique=False)
    op.create_index(op.f('ix_anomalies_user_id'), 'anomalies', ['user_id'], unique=False)
    op.create_index(op.f('ix_anomalies_transaction_id'), 'anomalies', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_anomalies_status'), 'anomalies', ['status'], unique=False)

    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('merchant', sa.String(length=255), nullable=False),
        sa.Column('typical_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('first_seen_month', sa.Date(), nullable=False),
        sa.Column('last_seen_month', sa.Date(), nullable=False),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'merchant', name='uq_subscription_user_merchant'),
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)

    op.create_table(
        'insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('dismissed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_insights_id'), 'insights', ['id'], unique=False)
    op.create_index(op.f('ix_insights_user_id'), 'insights', ['user_id'], unique=False)
    op.create_index(op.f('ix_insights_status'), 'insights', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_insights_status'), table_name='insights')
    op.drop_index(op.f('ix_insights_user_id'), table_name='insights')
    op.drop_index(op.f('ix_insights_id'), table_name='insights')
    op.drop_table('insights')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_index(op.f('ix_anomalies_status'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_transaction_id'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_user_id'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_id'), table_name='anomalies')
    op.drop_table('anomalies')
