from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class Comment(Base):
    """Map comments made by users on posts."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    # Keep the displayed author label stable even after a username update.
    owner: Mapped[str] = mapped_column(nullable=False)
    # Use the private account identity for permissions and self-like protection.
    author_email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="RESTRICT"), nullable=False, index=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("likes_count >= 0", name="ck_comments_likes_count_nonnegative"),
        Index("ix_comments_post_created_id", "post_id", "created_at", "id"),
        Index("ix_comments_owner", "owner"),
    )
