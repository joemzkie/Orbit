from datetime import datetime

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")


class UsernameBase(BaseModel):
    """Validate a stable, public username without exposing account email."""

    username: str = Field(min_length=3, max_length=30)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, username: str) -> str:
        username = username.strip().lower()
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError("Username must be 3-30 lowercase letters, numbers, or underscores")
        return username


class UserBase(BaseModel):
    """Define the user fields shared by request and response schemas."""

    # Require a syntactically valid email address for every user representation.
    email: EmailStr


class UserCreate(UserBase, UsernameBase):
    """Accept the fields required to create a user account."""

    # Require a password with a practical minimum strength during registration.
    password: str = Field(min_length=12, max_length=256)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        """Reject passwords that lack basic character variety."""

        if not any(character.islower() for character in password):
            raise ValueError("Password must include a lowercase letter")
        if not any(character.isupper() for character in password):
            raise ValueError("Password must include an uppercase letter")
        if not any(character.isdigit() for character in password):
            raise ValueError("Password must include a number")
        return password


class UserRead(UserBase):
    """Expose the safe user fields returned by the API."""

    # Include the time when the user account was first created.
    created_at: datetime
    # Public username is safe to display to the signed-in account.
    username: str | None

    # Allow Pydantic to serialize attributes from SQLAlchemy ORM objects.
    model_config = ConfigDict(from_attributes=True)


class UserLogin(UserBase):
    """Accept credentials for an existing user account."""

    # Accept the password that will be verified against the stored Argon2 hash.
    password: str = Field(min_length=8, max_length=256)


class UsernameUpdate(UsernameBase):
    """Accept a new public username for the authenticated account."""

    pass


class PasswordUpdate(BaseModel):
    """Require present credentials before storing a replacement password."""

    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, password: str) -> str:
        return UserCreate.validate_password_strength(password)
