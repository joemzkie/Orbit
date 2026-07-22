from sqlalchemy import ForeignKey, Integer, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class PostLike(Base):
    """Record one user's like for one post."""

    __tablename__ = "post_likes"

    user_email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="RESTRICT"), nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("user_email", "post_id", name="pk_post_likes"),)


class CommentLike(Base):
    """Record one user's like for one comment."""

    __tablename__ = "comment_likes"

    user_email: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="RESTRICT"), nullable=False)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("user_email", "comment_id", name="pk_comment_likes"),)
