from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class Post(Base):
    """Map blog post records to the posts database table."""

    # Set the physical table name used for blog post records.
    __tablename__ = "posts"

    # Store the unique primary key assigned to each post.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Store the post's short display title.
    title: Mapped[str] = mapped_column(String(255))
    # Store the post's full text content without a short string limit.
    content: Mapped[str] = mapped_column(Text)
    # Mark posts as public by default unless explicitly set otherwise.
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    # Store the email address of the user who created this post.
    owner: Mapped[str] = mapped_column(ForeignKey("users.email", ondelete="RESTRICT"), index=True)
    # Record the database time when the post was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
