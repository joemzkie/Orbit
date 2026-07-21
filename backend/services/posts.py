from sqlalchemy import select
from sqlalchemy.orm import Session

from models.post import Post
from schemas.post import PostCreate, PostUpdate


def fetch_all_posts(db: Session) -> list[Post]:
    return list(db.scalars(select(Post)).all())


def fetch_post_by_id(db: Session, post_id: int) -> Post | None:
    return db.get(Post, post_id)


def create_post(db: Session, data: PostCreate) -> Post:
    post = Post(**data.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def fetch_post_latest(db: Session) -> list[Post]:
    statement = select(Post).order_by(Post.id.desc()).limit(10)
    return list(db.scalars(statement).all())


def delete_post(db: Session, post_id: int) -> bool:
    post = db.get(Post, post_id)
    if post is None:
        return False
    db.delete(post)
    db.commit()
    return True


def update_post(db: Session, post_id: int, data: PostUpdate) -> Post | None:
    post = db.get(Post, post_id)
    if post is None:
        return None
    for field, value in data.model_dump().items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post
