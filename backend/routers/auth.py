import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import AUTH_COOKIE_NAME, JWT_EXPIRE_MINUTES, create_access_token, get_current_user
from dbconn import get_db
from models.user import User
from schemas.user import UserLogin, UserRead
from security import verify_password
from services import users as users_service


# Group login and session endpoints separately from account registration.
router = APIRouter(prefix="/auth", tags=["Authentication"])


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
