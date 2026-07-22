from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostBase(BaseModel):
    """Define the fields shared by all post request and response schemas."""

    # Require a title for every post representation.
    title: str = Field(min_length=1, max_length=255)
    # Require the full text content for every post representation.
    content: str = Field(min_length=1, max_length=10_000)
    # Publish posts by default unless the client explicitly disables publication.
    published: bool = True


class PostCreate(PostBase):
    """Accept the fields required to create a new post."""

    pass


class PostUpdate(PostBase):
    """Accept the complete replacement fields for an existing post."""

    pass


class PostRead(PostBase):
    """Expose post fields returned by the API."""

    # Include the database-assigned post identifier in read responses.
    id: int
    # Include the email address of the account that owns the post.
    owner: str
    # Include the database timestamp when the post was created.
    created_at: datetime

    # Allow Pydantic to serialize attributes from SQLAlchemy ORM objects.
    model_config = ConfigDict(from_attributes=True)


class PostPage(BaseModel):
    """Represent one cursor-paginated page of posts."""

    # Return ordered post records for the requested feed page.
    items: list[PostRead]
    # Return the ID cursor for the next page or null when the feed is exhausted.
    next_cursor: int | None
