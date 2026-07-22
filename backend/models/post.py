from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dbconn import Base


class Post(Base):
    """Map blog post records to the posts database table."""

    # Set the physical table name used for blog post records.
    __tablename__ = "posts"

    # Store the unique primary key assigned to each post.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Store the post's short display title.
    title: Mapped[str] = mapped_column(String)
    # Store the post's full text content without a short string limit.
    content: Mapped[str] = mapped_column(Text)
    # Mark posts as public by default unless explicitly set otherwise.
    published: Mapped[bool] = mapped_column(Boolean, default=True)
