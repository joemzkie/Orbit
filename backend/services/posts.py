from sqlalchemy import select
from sqlalchemy.orm import Session

from models.post import Post
from schemas.post import PostCreate, PostUpdate


def fetch_all_posts(db: Session) -> list[Post]:
    """Return every persisted post from the database."""

    # Execute the post query and materialize its scalar ORM results as a list.
    return list(db.scalars(select(Post)).all())


def fetch_post_by_id(db: Session, post_id: int) -> Post | None:
    """Return the post with the supplied primary key, if it exists."""

    # Look up the post directly by its mapped primary key.
    return db.get(Post, post_id)


def create_post(db: Session, data: PostCreate) -> Post:
    """Persist a new post populated from validated request data."""

    # Convert the Pydantic model into keyword arguments for the ORM model.
    post = Post(**data.model_dump())
    # Stage the new post for insertion in the current session.
    db.add(post)
    # Commit the insert so the generated database values become permanent.
    db.commit()
    # Reload generated or database-managed values onto the ORM object.
    db.refresh(post)
    return post


def fetch_post_latest(db: Session) -> list[Post]:
    """Return up to ten posts ordered from newest to oldest by ID."""

    # Limit the descending primary-key query to the ten most recent rows.
    statement = select(Post).order_by(Post.id.desc()).limit(10)
    return list(db.scalars(statement).all())


def delete_post(db: Session, post_id: int) -> bool:
    """Delete a post by ID and report whether a matching post existed."""

    # Retrieve the target post before attempting to delete it.
    post = db.get(Post, post_id)
    # Signal that no deletion occurred when the target is absent.
    if post is None:
        return False
    # Mark the persisted post for removal in the active session.
    db.delete(post)
    # Permanently apply the deletion to the database.
    db.commit()
    return True


def update_post(db: Session, post_id: int, data: PostUpdate) -> Post | None:
    """Replace a post's mutable fields with validated update data."""

    # Retrieve the target post before modifying its mapped attributes.
    post = db.get(Post, post_id)
    # Return no result when the requested post does not exist.
    if post is None:
        return None
    # Copy each validated field onto the existing ORM instance.
    for field, value in data.model_dump().items():
        setattr(post, field, value)
    # Permanently apply the field changes to the database.
    db.commit()
    # Reload database-managed values before returning the updated post.
    db.refresh(post)
    return post
