from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommentCreate(BaseModel):
    """Validate a new plain-text comment."""

    comment: str = Field(min_length=1, max_length=5_000)

    @field_validator("comment")
    @classmethod
    def reject_blank_comment(cls, value: str) -> str:
        """Keep intentional whitespace inside comments but reject empty submissions."""

        if not value.strip():
            raise ValueError("Comment cannot be blank")
        return value


class CommentRead(BaseModel):
    """Expose one comment without any author secrets."""

    id: int
    post_id: int
    owner: str
    comment: str
    likes_count: int
    liked_by_current_user: bool = False
    is_owned_by_current_user: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
