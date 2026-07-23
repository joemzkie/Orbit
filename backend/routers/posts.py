from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, get_optional_current_user
from dbconn import get_db
from models.comment import Comment
from models.user import User
from schemas.comment import CommentCreate, CommentRead, CommentUpdate
from schemas.post import LikeState, PostCreate, PostPage, PostRead, PostUpdate
from services import comments as comments_service
from services import posts as posts_service


# Group post endpoints under the Posts API documentation tag.
router = APIRouter(tags=["Posts"])


def require_username(current_user: User) -> str:
    """Require a public identity before the account can create public content."""

    if current_user.username is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Choose a username in Settings before publishing or commenting")
    return current_user.username


async def post_read(post, db: AsyncSession, viewer_email: str | None) -> PostRead:
    """Add viewer-specific ledger state without persisting it on the post itself."""

    return PostRead.model_validate(post).model_copy(
        update={
            "comments_count": await db.scalar(select(func.count(Comment.id)).where(Comment.post_id == post.id)),
            "liked_by_current_user": await posts_service.is_post_liked_by_user(db, post.id, viewer_email),
            "is_owned_by_current_user": post.author_email == viewer_email,
        }
    )


async def post_reads(posts, db: AsyncSession, viewer_email: str | None) -> list[PostRead]:
    """Serialize a feed page while loading its liked state in one database query."""

    liked_ids = await posts_service.liked_post_ids_for_user(db, [post.id for post in posts], viewer_email)
    return [
        PostRead.model_validate(post).model_copy(
            update={"liked_by_current_user": post.id in liked_ids, "is_owned_by_current_user": post.author_email == viewer_email}
        )
        for post in posts
    ]


async def popular_post_reads(posts_with_counts, db: AsyncSession, viewer_email: str | None) -> list[PostRead]:
    """Serialize the engagement ranking with its pre-aggregated comment counts."""

    posts = [post for post, _comments_count in posts_with_counts]
    liked_ids = await posts_service.liked_post_ids_for_user(db, [post.id for post in posts], viewer_email)
    return [
        PostRead.model_validate(post).model_copy(
            update={
                "comments_count": comments_count,
                "liked_by_current_user": post.id in liked_ids,
                "is_owned_by_current_user": post.author_email == viewer_email,
            }
        )
        for post, comments_count in posts_with_counts
    ]


async def comment_reads(comments, db: AsyncSession, viewer_email: str | None) -> list[CommentRead]:
    """Serialize a comment thread with one batched viewer-like lookup."""

    liked_ids = await comments_service.liked_comment_ids_for_user(db, [comment.id for comment in comments], viewer_email)
    return [
        CommentRead.model_validate(comment).model_copy(
            update={"liked_by_current_user": comment.id in liked_ids, "is_owned_by_current_user": comment.author_email == viewer_email}
        )
        for comment in comments
    ]


@router.get("/posts", response_model=PostPage)
async def get_posts(
    limit: int = Query(default=20, ge=1, le=50),
    cursor: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Return one cursor-paginated feed page ordered from newest to oldest."""

    # Query only a bounded page so a large feed cannot exhaust database resources.
    posts, next_cursor = await posts_service.fetch_posts(db, limit, cursor)
    return PostPage(items=await post_reads(posts, db, current_user.email if current_user else None), next_cursor=next_cursor)


@router.post("/posts", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a post owned by the authenticated account."""

    # Derive ownership from the signed session instead of trusting frontend input.
    return await posts_service.create_post(db, post, require_username(current_user), current_user.email)


@router.get("/posts/latest", response_model=list[PostRead])
async def get_latest_posts(db: AsyncSession = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    """Return up to ten newest posts for small preview displays."""

    posts = await posts_service.fetch_post_latest(db)
    return await post_reads(posts, db, current_user.email if current_user else None)


@router.get("/posts/popular", response_model=list[PostRead])
async def get_popular_posts(db: AsyncSession = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    """Return the ten highest-engagement posts for the discovery panel."""

    posts_with_counts = await posts_service.fetch_popular_posts(db)
    return await popular_post_reads(posts_with_counts, db, current_user.email if current_user else None)


@router.get("/posts/{post_id}", response_model=PostRead)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db), current_user: User | None = Depends(get_optional_current_user)):
    """Return one post by ID or raise an HTTP 404 response."""

    post = await posts_service.fetch_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return await post_read(post, db, current_user.email if current_user else None)


@router.post("/posts/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an authenticated user's comment to an existing post."""

    if await posts_service.fetch_post_by_id(db, post_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return await comments_service.create_comment(db, post_id, data, require_username(current_user), current_user.email)


@router.get("/posts/{post_id}/comments", response_model=list[CommentRead])
async def get_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Return chronological comments for one existing post."""

    if await posts_service.fetch_post_by_id(db, post_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    comments = await comments_service.fetch_comments_for_post(db, post_id)
    return await comment_reads(comments, db, current_user.email if current_user else None)


@router.post("/posts/{post_id}/like", response_model=LikeState)
async def like_post(post_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Like a post exactly once for the authenticated user."""

    post = await posts_service.fetch_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    if post.author_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot like your own post")
    updated_post = await posts_service.like_post(db, post_id, current_user.email)
    return LikeState(likes_count=updated_post.likes_count, liked_by_current_user=True)


@router.delete("/posts/{post_id}/like", response_model=LikeState)
async def unlike_post(post_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Remove the authenticated user's existing post like, if any."""

    post = await posts_service.fetch_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    if post.author_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot like your own post")
    updated_post = await posts_service.unlike_post(db, post_id, current_user.email)
    return LikeState(likes_count=updated_post.likes_count, liked_by_current_user=False)


@router.post("/comments/{comment_id}/like", response_model=LikeState)
async def like_comment(comment_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Like a comment once for the authenticated user."""

    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment was not found")
    if comment.author_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot like your own comment")
    updated_comment = await comments_service.like_comment(db, comment_id, current_user.email)
    return LikeState(likes_count=updated_comment.likes_count, liked_by_current_user=True)


@router.delete("/comments/{comment_id}/like", response_model=LikeState)
async def unlike_comment(comment_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Remove the authenticated user's comment like, if any."""

    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment was not found")
    if comment.author_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot like your own comment")
    updated_comment = await comments_service.unlike_comment(db, comment_id, current_user.email)
    return LikeState(likes_count=updated_comment.likes_count, liked_by_current_user=False)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an authenticated user's own post."""

    if not await posts_service.delete_post(db, post_id, current_user.email):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/posts/{post_id}", response_model=PostRead)
async def update_post(
    post_id: int,
    post: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace fields on an authenticated user's own post."""

    updated_post = await posts_service.update_post(db, post_id, post, current_user.email)
    if updated_post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return await post_read(updated_post, db, current_user.email)


@router.put("/comments/{comment_id}", response_model=CommentRead)
async def update_comment(
    comment_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace a comment only when the authenticated account owns it."""

    updated_comment = await comments_service.update_comment(db, comment_id, data, current_user.email)
    if updated_comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment was not found")
    return (await comment_reads([updated_comment], db, current_user.email))[0]


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment only when the authenticated account owns it."""

    if not await comments_service.delete_comment(db, comment_id, current_user.email):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment was not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
