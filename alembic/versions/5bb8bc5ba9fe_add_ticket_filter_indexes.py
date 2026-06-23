"""add ticket filter indexes

Revision ID: 5bb8bc5ba9fe
Revises: 4bed19a00309
Create Date: 2026-06-22 19:44:09.635350

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5bb8bc5ba9fe'
down_revision: Union[str, Sequence[str], None] = '4bed19a00309'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_tickets_category'), 'tickets', ['category'], unique=False)
    op.create_index(op.f('ix_tickets_created_at'), 'tickets', ['created_at'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)
    op.create_index(op.f('ix_tickets_user_id'), 'tickets', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tickets_user_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_status'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_created_at'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_category'), table_name='tickets')
