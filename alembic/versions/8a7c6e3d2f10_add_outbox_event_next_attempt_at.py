"""add outbox event next attempt timestamp

Revision ID: 8a7c6e3d2f10
Revises: 4f96c7681647
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a7c6e3d2f10"
down_revision: Union[str, Sequence[str], None] = "4f96c7681647"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_outbox_events_next_attempt_at",
        "outbox_events",
        ["next_attempt_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_events_next_attempt_at",
        table_name="outbox_events",
    )
    op.drop_column("outbox_events", "next_attempt_at")
