"""Add post ownership and durable idempotency records."""

from datetime import UTC, datetime, timedelta
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# Identify this migration as the revision following user timestamp creation.
revision: str = "20260722_03"
down_revision: Union[str, Sequence[str], None] = "20260722_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
BACKFILL_OWNER = "user@example.com"


def upgrade() -> None:
    """Assign every existing post to a valid user and create retry storage."""

    connection = op.get_bind()
    if context.is_offline_mode():
        # Emit the same safety check in generated PostgreSQL SQL without requiring a live bind.
        op.execute(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM users WHERE email = '{BACKFILL_OWNER}') "
            f"THEN RAISE EXCEPTION 'Cannot backfill posts because {BACKFILL_OWNER} does not exist'; END IF; END $$;"
        )
    else:
        # Refuse to create orphaned records when the planned backfill account is absent.
        exists = connection.execute(sa.text("SELECT 1 FROM users WHERE email = :email"), {"email": BACKFILL_OWNER}).scalar()
        if exists is None:
            raise RuntimeError(f"Cannot backfill posts because {BACKFILL_OWNER} does not exist")
    # Add the column as nullable so existing post rows can be safely populated first.
    op.add_column("posts", sa.Column("owner", sa.String(), nullable=True))
    if context.is_offline_mode():
        op.execute(f"UPDATE posts SET owner = '{BACKFILL_OWNER}' WHERE owner IS NULL")
    else:
        connection.execute(sa.text("UPDATE posts SET owner = :email WHERE owner IS NULL"), {"email": BACKFILL_OWNER})
    # Enforce referential integrity and efficient owner-feed lookups after backfill completes.
    op.alter_column("posts", "owner", nullable=False)
    op.create_foreign_key("fk_posts_owner_users", "posts", "users", ["owner"], ["email"], ondelete="RESTRICT")
    op.create_index("ix_posts_owner", "posts", ["owner"])
    # Persist mutation responses so safe client retries can be replayed exactly once.
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(length=512), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("response_headers", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )


def downgrade() -> None:
    """Remove retry records and post ownership metadata."""

    # Remove dependent retry storage before reversing the posts table change.
    op.drop_table("idempotency_keys")
    op.drop_index("ix_posts_owner", table_name="posts")
    op.drop_constraint("fk_posts_owner_users", "posts", type_="foreignkey")
    op.drop_column("posts", "owner")
