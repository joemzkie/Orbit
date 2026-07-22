from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.post import Post
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


async def create_post(db: AsyncSession, data: PostCreate, owner: str) -> Post:
    """Persist a new post populated from validated request data."""

    # Convert the Pydantic model into keyword arguments for the ORM model.
    post = Post(**data.model_dump(), owner=owner)
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


async def delete_post(db: AsyncSession, post_id: int, owner: str) -> bool:
    """Delete a post by ID and report whether a matching post existed."""

    # Retrieve the target post before attempting to delete it.
    post = await db.get(Post, post_id)
    # Signal that no deletion occurred when the target is absent.
    if post is None or post.owner != owner:
        return False
    # Mark the persisted post for removal in the active session.
    db.delete(post)
    # Permanently apply the deletion to the database.
    await db.commit()
    return True


async def update_post(db: AsyncSession, post_id: int, data: PostUpdate, owner: str) -> Post | None:
    """Replace a post's mutable fields with validated update data."""

    # Retrieve the target post before modifying its mapped attributes.
    post = await db.get(Post, post_id)
    # Return no result when the requested post does not exist.
    if post is None or post.owner != owner:
        return None
    # Copy each validated field onto the existing ORM instance.
    for field, value in data.model_dump().items():
        setattr(post, field, value)
    # Permanently apply the field changes to the database.
    await db.commit()
    # Reload database-managed values before returning the updated post.
    await db.refresh(post)
    return post
