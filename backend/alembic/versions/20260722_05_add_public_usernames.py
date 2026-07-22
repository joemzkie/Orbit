"""Add public usernames without rewriting legacy content owners."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_05"
down_revision: Union[str, Sequence[str], None] = "20260722_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Separate public display labels from private author identities."""

    op.add_column("users", sa.Column("username", sa.String(length=30), nullable=True))
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_check_constraint(
        "ck_users_username_format",
        "users",
        "username IS NULL OR username ~ '^[a-z0-9_]{3,30}$'",
    )

    op.add_column("posts", sa.Column("author_email", sa.String(), nullable=True))
    op.execute("UPDATE posts SET author_email = owner")
    op.alter_column("posts", "author_email", nullable=False)
    op.create_foreign_key("fk_posts_author_email_users", "posts", "users", ["author_email"], ["email"], ondelete="RESTRICT")
    op.create_index("ix_posts_author_email", "posts", ["author_email"])
    op.drop_constraint("fk_posts_owner_users", "posts", type_="foreignkey")

    op.add_column("comments", sa.Column("author_email", sa.String(), nullable=True))
    op.execute("UPDATE comments SET author_email = owner")
    op.alter_column("comments", "author_email", nullable=False)
    op.create_foreign_key("fk_comments_author_email_users", "comments", "users", ["author_email"], ["email"], ondelete="RESTRICT")
    op.create_index("ix_comments_author_email", "comments", ["author_email"])
    op.drop_constraint("fk_comments_owner_users", "comments", type_="foreignkey")


def downgrade() -> None:
    """Restore the email-owner schema only when all new public owners are reverted."""

    op.drop_index("ix_comments_author_email", table_name="comments")
    op.drop_constraint("fk_comments_author_email_users", "comments", type_="foreignkey")
    op.drop_column("comments", "author_email")
    op.create_foreign_key("fk_comments_owner_users", "comments", "users", ["owner"], ["email"], ondelete="RESTRICT")

    op.drop_index("ix_posts_author_email", table_name="posts")
    op.drop_constraint("fk_posts_author_email_users", "posts", type_="foreignkey")
    op.drop_column("posts", "author_email")
    op.create_foreign_key("fk_posts_owner_users", "posts", "users", ["owner"], ["email"], ondelete="RESTRICT")

    op.drop_constraint("ck_users_username_format", "users", type_="check")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")
