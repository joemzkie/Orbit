import os
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from dbconn import get_db
from models.user import User


# Read the signing configuration from the environment instead of source control.
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "15"))
AUTH_COOKIE_NAME = "orbit_access_token"


def create_access_token(email: str) -> str:
    """Create a short-lived signed token for an authenticated email address."""

    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be configured before authentication can be used")
    # Include standard subject and expiration claims in the signed token.
    expires_at = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expires_at}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str | None) -> str | None:
    """Return the authenticated email from a valid token or None."""

    if not token or not JWT_SECRET:
        return None
    try:
        # Decode and validate the signed token before trusting its subject claim.
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        subject = payload.get("sub")
        return subject if isinstance(subject, str) else None
    except InvalidTokenError:
        return None


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> User:
    """Load the authenticated user or return a generic unauthorized response."""

    # Resolve the signed token subject before querying the users table.
    email = decode_access_token(access_token)
    user = await db.get(User, email) if email else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required")
    return user


async def get_optional_current_user(
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> User | None:
    """Load the signed-in user when a valid session exists, otherwise return None."""

    email = decode_access_token(access_token)
    return await db.get(User, email) if email else None
