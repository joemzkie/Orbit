from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.user import PasswordUpdate, UserCreate
from security import hash_password


async def create_user(db: AsyncSession, data: UserCreate) -> User | None:
    """Create a user with a hashed password or return None for a duplicate email."""

    # Construct the ORM record without retaining the plaintext request password.
    user = User(email=str(data.email), username=data.username, password=hash_password(data.password))
    # Stage the new user for insertion in the current session.
    db.add(user)
    try:
        # Commit the new record so the email primary-key constraint is enforced.
        await db.commit()
    except IntegrityError:
        # Restore the session after a duplicate-email constraint violation.
        await db.rollback()
        return None
    # Reload the committed record before it is returned to the router.
    await db.refresh(user)
    return user


async def fetch_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return a user account by its email primary key."""

    # Retrieve the account directly by its mapped email primary key.
    return await db.get(User, email)


async def update_username(db: AsyncSession, user: User, username: str) -> User | None:
    """Persist a unique public username, returning None on a uniqueness race."""

    user.username = username
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, data: PasswordUpdate) -> None:
    """Replace the password only after the router verified the current credential."""

    user.password = hash_password(data.new_password)
    await db.commit()
