from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Define the user fields shared by request and response schemas."""

    # Require a syntactically valid email address for every user representation.
    email: EmailStr


class UserCreate(UserBase):
    """Accept the fields required to create a user account."""

    # Require a password with at least eight characters during registration.
    password: str = Field(min_length=8)


class UserRead(UserBase):
    """Expose the safe user fields returned by the API."""

    # Allow Pydantic to serialize attributes from SQLAlchemy ORM objects.
    model_config = ConfigDict(from_attributes=True)
