"""add_user_sync_columns

Revision ID: a3f7c92d1b45
Revises: 628c6541bc23
Create Date: 2026-04-05 15:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c92d1b45'
down_revision: Union[str, None] = '628c6541bc23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('sync_interval_hours', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_synced_at')
    op.drop_column('users', 'sync_interval_hours')
    op.drop_column('users', 'sync_enabled')
