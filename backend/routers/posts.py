from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from dbconn import get_db
from models.user import User
from schemas.post import PostCreate, PostPage, PostRead, PostUpdate
from services import posts as posts_service


# Group post endpoints under the Posts API documentation tag.
router = APIRouter(tags=["Posts"])


@router.get("/posts", response_model=PostPage)
async def get_posts(
    limit: int = Query(default=20, ge=1, le=50),
    cursor: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Return one cursor-paginated feed page ordered from newest to oldest."""

    # Query only a bounded page so a large feed cannot exhaust database resources.
    posts, next_cursor = await posts_service.fetch_posts(db, limit, cursor)
    return PostPage(items=posts, next_cursor=next_cursor)


@router.post("/posts", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a post owned by the authenticated account."""

    # Derive ownership from the signed session instead of trusting frontend input.
    return await posts_service.create_post(db, post, current_user.email)


@router.get("/posts/latest", response_model=list[PostRead])
async def get_latest_posts(db: AsyncSession = Depends(get_db)):
    """Return up to ten newest posts for small preview displays."""

    return await posts_service.fetch_post_latest(db)


@router.get("/posts/{post_id}", response_model=PostRead)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """Return one post by ID or raise an HTTP 404 response."""

    post = await posts_service.fetch_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return post


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an authenticated user's own post."""

    post = await posts_service.fetch_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    if post.owner != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this post")
    await posts_service.delete_post(db, post_id, current_user.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/posts/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace fields on an authenticated user's own post."""

    existing_post = await posts_service.fetch_post_by_id(db, post_id)
    if existing_post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    if existing_post.owner != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this post")
    return await posts_service.update_post(db, post_id, post, current_user.email)
