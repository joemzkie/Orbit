"""Add a creation timestamp to the users table."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identify this migration as the revision following users-table creation.
revision: str = "20260722_02"
down_revision: Union[str, Sequence[str], None] = "20260722_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a non-null creation timestamp to every user record."""

    # Populate existing rows from PostgreSQL's current timestamp during the schema change.
    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the user creation timestamp."""

    # Remove the timestamp column added by this revision.
    op.drop_column("users", "created_at")
