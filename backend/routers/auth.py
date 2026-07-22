import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import AUTH_COOKIE_NAME, JWT_EXPIRE_MINUTES, create_access_token, get_current_user
from dbconn import get_db
from models.user import User
from schemas.user import PasswordUpdate, UserCreate, UserLogin, UserRead, UsernameUpdate
from security import verify_password
from services import users as users_service


# Group login and session endpoints separately from account registration.
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"description": "Email is already registered"}},
)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create an account while storing only its Argon2 password hash."""

    created_user = await users_service.create_user(db, user)
    if created_user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    return created_user


@router.post("/login", response_model=UserRead)
async def login(credentials: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    """Verify credentials and issue a short-lived HttpOnly session cookie."""

    # Look up the account by its email primary key before verifying its password hash.
    user = await users_service.fetch_user_by_email(db, str(credentials.email))
    if user is None or not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    # Keep the signed token inaccessible to JavaScript to reduce XSS token theft.
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=create_access_token(user.email),
        max_age=JWT_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Clear the browser session cookie."""

    # Expire the cookie using the same key and path used during login.
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's safe profile data."""

    return current_user


@router.patch("/me/profile", response_model=UserRead, responses={status.HTTP_409_CONFLICT: {"description": "Username is already taken"}})
async def update_profile(
    data: UsernameUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the signed-in account's unique public username."""

    updated_user = await users_service.update_username(db, current_user, data.username)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken")
    return updated_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    data: PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a password after verifying the current secret."""

    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    await users_service.change_password(db, current_user, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
