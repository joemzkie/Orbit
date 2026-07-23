from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.post import Post
from models.like import PostLike
from models.comment import Comment
from schemas.post import PostCreate, PostUpdate


async def fetch_posts(db: AsyncSession, limit: int, cursor: int | None) -> tuple[list[Post], int | None]:
    """Return one descending ID page of posts and its next cursor."""

    # Fetch one extra record to determine whether another feed page exists.
    statement = select(Post).order_by(Post.id.desc()).limit(limit + 1)
    if cursor is not None:
        statement = statement.where(Post.id < cursor)
    result = await db.scalars(statement)
    posts = list(result.all())
    next_cursor = posts[limit].id if len(posts) > limit else None
    return posts[:limit], next_cursor


async def fetch_post_by_id(db: AsyncSession, post_id: int) -> Post | None:
    """Return the post with the supplied primary key, if it exists."""

    # Look up the post directly by its mapped primary key.
    return await db.get(Post, post_id)


async def create_post(db: AsyncSession, data: PostCreate, owner: str, author_email: str) -> Post:
    """Persist a new post populated from validated request data."""

    # Convert the Pydantic model into keyword arguments for the ORM model.
    post = Post(**data.model_dump(), owner=owner, author_email=author_email)
    # Stage the new post for insertion in the current session.
    db.add(post)
    # Commit the insert so the generated database values become permanent.
    await db.commit()
    # Reload generated or database-managed values onto the ORM object.
    await db.refresh(post)
    return post


async def fetch_post_latest(db: AsyncSession) -> list[Post]:
    """Return up to ten posts ordered from newest to oldest by ID."""

    # Limit the descending primary-key query to the ten most recent rows.
    statement = select(Post).order_by(Post.id.desc()).limit(10)
    return list((await db.scalars(statement)).all())


async def fetch_popular_posts(db: AsyncSession) -> list[tuple[Post, int]]:
    """Return ten posts ranked by engagement without scanning like ledgers."""

    comments_count = func.count(Comment.id).label("comments_count")
    statement = (
        select(Post, comments_count)
        .outerjoin(Comment, Comment.post_id == Post.id)
        .group_by(Post.id)
        .order_by((Post.likes_count + comments_count).desc(), Post.likes_count.desc(), Post.created_at.desc())
        .limit(10)
    )
    return list((await db.execute(statement)).all())


async def delete_post(db: AsyncSession, post_id: int, owner: str) -> bool:
    """Delete only a caller-owned post; PostgreSQL cascades dependent rows."""

    result = await db.execute(
        delete(Post).where(Post.id == post_id, Post.author_email == owner)
    )
    await db.commit()
    return result.rowcount == 1


async def update_post(db: AsyncSession, post_id: int, data: PostUpdate, owner: str) -> Post | None:
    """Replace only a caller-owned post's mutable fields."""

    result = await db.scalars(
        select(Post).where(Post.id == post_id, Post.author_email == owner)
    )
    post = result.one_or_none()
    if post is None:
        return None
    # Copy each validated field onto the existing ORM instance.
    for field, value in data.model_dump().items():
        setattr(post, field, value)
    # Permanently apply the field changes to the database.
    await db.commit()
    # Reload database-managed values before returning the updated post.
    await db.refresh(post)
    return post


async def like_post(db: AsyncSession, post_id: int, user_email: str) -> Post | None:
    """Insert a durable like once, even when duplicate requests race."""

    statement = (
        insert(PostLike)
        .values(user_email=user_email, post_id=post_id)
        .on_conflict_do_nothing(index_elements=["user_email", "post_id"])
    )
    await db.execute(statement)
    await db.commit()
    return await db.get(Post, post_id)


async def unlike_post(db: AsyncSession, post_id: int, user_email: str) -> Post | None:
    """Remove a user's durable like; deleting an absent row is intentionally safe."""

    await db.execute(delete(PostLike).where(PostLike.post_id == post_id, PostLike.user_email == user_email))
    await db.commit()
    return await db.get(Post, post_id)


async def is_post_liked_by_user(db: AsyncSession, post_id: int, user_email: str | None) -> bool:
    """Look up the viewer's single like row with the composite primary key."""

    if user_email is None:
        return False
    return await db.get(PostLike, {"user_email": user_email, "post_id": post_id}) is not None


async def liked_post_ids_for_user(db: AsyncSession, post_ids: list[int], user_email: str | None) -> set[int]:
    """Load a feed page's viewer likes with one indexed query instead of N lookups."""

    if not post_ids or user_email is None:
        return set()
    statement = select(PostLike.post_id).where(PostLike.user_email == user_email, PostLike.post_id.in_(post_ids))
    return set((await db.scalars(statement)).all())
