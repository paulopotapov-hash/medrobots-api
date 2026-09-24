"""Add idempotency_key to contacts and constrain status values.

Revision ID: 0002_idempotency
Revises: 0001_contacts
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_idempotency"
down_revision: str | None = "0001_contacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table so this also works on SQLite (used in tests), which
    # cannot ALTER TABLE to add constraints in place and needs a rebuild.
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(255), nullable=True))
        batch_op.create_unique_constraint("uq_contacts_idempotency_key", ["idempotency_key"])
        batch_op.create_check_constraint(
            "ck_contacts_status", "status IN ('new', 'in_progress', 'resolved')"
        )


def downgrade() -> None:
    with op.batch_alter_table("contacts") as batch_op:
        batch_op.drop_constraint("ck_contacts_status", type_="check")
        batch_op.drop_constraint("uq_contacts_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
