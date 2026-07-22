from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from dbconn import get_db
from schemas.user import UserCreate, UserRead
from services import users as users_service

# Group user endpoints under a shared URL prefix and documentation tag.
router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"description": "Email is already registered"}},
)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a user account with an email primary key."""

    # Create the user while converting a duplicate email into a client error.
    created_user = await users_service.create_user(db, user)
    if created_user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    # Return only safe user fields defined by the response schema.
    return created_user
