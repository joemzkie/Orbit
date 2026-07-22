"""Create comments and durable, race-safe post/comment likes."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_04"
down_revision: Union[str, Sequence[str], None] = "20260722_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add comment storage and like ledgers with trigger-maintained counters."""

    # Existing users already have an Argon2 password hash and created_at timestamp.
    # A server default makes the new counter safe for existing post rows.
    op.add_column(
        "posts",
        sa.Column("likes_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_check_constraint("ck_posts_likes_count_nonnegative", "posts", "likes_count >= 0")

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("likes_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("likes_count >= 0", name="ck_comments_likes_count_nonnegative"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], name="fk_comments_post", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner"], ["users.email"], name="fk_comments_owner_users", ondelete="RESTRICT"),
    )
    # The composite index covers chronological rendering; the owner index supports profile/moderation reads.
    op.create_index("ix_comments_post_created_id", "comments", ["post_id", "created_at", "id"])
    op.create_index("ix_comments_owner", "comments", ["owner"])

    op.create_table(
        "post_likes",
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_email"], ["users.email"], name="fk_post_likes_user", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], name="fk_post_likes_post", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_email", "post_id", name="pk_post_likes"),
    )
    op.create_index("ix_post_likes_post_id", "post_likes", ["post_id"])

    op.create_table(
        "comment_likes",
        sa.Column("user_email", sa.String(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_email"], ["users.email"], name="fk_comment_likes_user", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], name="fk_comment_likes_comment", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_email", "comment_id", name="pk_comment_likes"),
    )
    op.create_index("ix_comment_likes_comment_id", "comment_likes", ["comment_id"])

    # Counter updates occur in the same PostgreSQL transaction as the ledger mutation.
    op.execute("""
        CREATE FUNCTION sync_post_likes_count() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE posts SET likes_count = likes_count + 1 WHERE id = NEW.post_id;
            ELSE
                UPDATE posts SET likes_count = likes_count - 1 WHERE id = OLD.post_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_sync_post_likes_count
        AFTER INSERT OR DELETE ON post_likes
        FOR EACH ROW EXECUTE FUNCTION sync_post_likes_count();
    """)
    op.execute("""
        CREATE FUNCTION sync_comment_likes_count() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE comments SET likes_count = likes_count + 1 WHERE id = NEW.comment_id;
            ELSE
                UPDATE comments SET likes_count = likes_count - 1 WHERE id = OLD.comment_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_sync_comment_likes_count
        AFTER INSERT OR DELETE ON comment_likes
        FOR EACH ROW EXECUTE FUNCTION sync_comment_likes_count();
    """)


def downgrade() -> None:
    """Remove like triggers and tables before their dependencies."""

    op.execute("DROP TRIGGER trg_sync_comment_likes_count ON comment_likes")
    op.execute("DROP FUNCTION sync_comment_likes_count()")
    op.execute("DROP TRIGGER trg_sync_post_likes_count ON post_likes")
    op.execute("DROP FUNCTION sync_post_likes_count()")
    op.drop_index("ix_comment_likes_comment_id", table_name="comment_likes")
    op.drop_table("comment_likes")
    op.drop_index("ix_post_likes_post_id", table_name="post_likes")
    op.drop_table("post_likes")
    op.drop_index("ix_comments_owner", table_name="comments")
    op.drop_index("ix_comments_post_created_id", table_name="comments")
    op.drop_table("comments")
    op.drop_constraint("ck_posts_likes_count_nonnegative", "posts", type_="check")
    op.drop_column("posts", "likes_count")
