"""Create the users table with email as its primary key."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identify this migration and its position at the start of the revision chain.
revision: str = "20260722_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the user account table."""

    # Create a table whose email column uniquely identifies every account.
    op.create_table(
        "users",
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("email"),
    )


def downgrade() -> None:
    """Remove the user account table."""

    # Drop the table created by this migration.
    op.drop_table("users")
