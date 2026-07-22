from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.comment import Comment
from models.like import CommentLike
from schemas.comment import CommentCreate


async def create_comment(db: AsyncSession, post_id: int, data: CommentCreate, owner: str, author_email: str) -> Comment:
    """Store one authenticated user's plain-text comment."""

    comment = Comment(post_id=post_id, owner=owner, author_email=author_email, comment=data.comment)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def fetch_comments_for_post(db: AsyncSession, post_id: int) -> list[Comment]:
    """Return a stable chronological comment thread for one post."""

    statement = select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc(), Comment.id.asc())
    return list((await db.scalars(statement)).all())


async def like_comment(db: AsyncSession, comment_id: int, user_email: str) -> Comment | None:
    """Insert one durable comment like, safely ignoring racing duplicates."""

    statement = (
        insert(CommentLike)
        .values(user_email=user_email, comment_id=comment_id)
        .on_conflict_do_nothing(index_elements=["user_email", "comment_id"])
    )
    await db.execute(statement)
    await db.commit()
    return await db.get(Comment, comment_id)


async def unlike_comment(db: AsyncSession, comment_id: int, user_email: str) -> Comment | None:
    """Delete a comment like when present; an absent row is already unliked."""

    await db.execute(delete(CommentLike).where(CommentLike.comment_id == comment_id, CommentLike.user_email == user_email))
    await db.commit()
    return await db.get(Comment, comment_id)


async def liked_comment_ids_for_user(db: AsyncSession, comment_ids: list[int], user_email: str | None) -> set[int]:
    """Fetch one thread's viewer likes in a single indexed query."""

    if not comment_ids or user_email is None:
        return set()
    statement = select(CommentLike.comment_id).where(CommentLike.user_email == user_email, CommentLike.comment_id.in_(comment_ids))
    return set((await db.scalars(statement)).all())
