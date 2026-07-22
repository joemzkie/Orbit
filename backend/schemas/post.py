from pydantic import BaseModel, ConfigDict


class PostBase(BaseModel):
    """Define the fields shared by all post request and response schemas."""

    # Require a title for every post representation.
    title: str
    # Require the full text content for every post representation.
    content: str
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

    # Allow Pydantic to serialize attributes from SQLAlchemy ORM objects.
    model_config = ConfigDict(from_attributes=True)
