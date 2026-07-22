from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate
from security import hash_password


def create_user(db: Session, data: UserCreate) -> User | None:
    """Create a user with a hashed password or return None for a duplicate email."""

    # Construct the ORM record without retaining the plaintext request password.
    user = User(email=str(data.email), password=hash_password(data.password))
    # Stage the new user for insertion in the current session.
    db.add(user)
    try:
        # Commit the new record so the email primary-key constraint is enforced.
        db.commit()
    except IntegrityError:
        # Restore the session after a duplicate-email constraint violation.
        db.rollback()
        return None
    # Reload the committed record before it is returned to the router.
    db.refresh(user)
    return user
