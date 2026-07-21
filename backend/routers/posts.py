from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from dbconn import get_db
from schemas.post import PostCreate, PostUpdate
from services import posts as posts_service

router = APIRouter(tags=["Posts"])


@router.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    return {"DATA": posts_service.fetch_all_posts(db)}


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_posts(post: PostCreate, db: Session = Depends(get_db)):
    return {"data": posts_service.create_post(db, post)}


@router.get("/posts/latest")
def get_latest_posts(db: Session = Depends(get_db)):
    posts = posts_service.fetch_post_latest(db)
    if not posts:
        return {"Message": "No available posts"}
    return {"Details": posts}


@router.get("/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = posts_service.fetch_post_by_id(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {post_id} was not found")
    return {"post_detail": post}


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    if not posts_service.delete_post(db, post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {post_id} was not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/put/{post_id}")
def update_post(post_id: int, post: PostUpdate, db: Session = Depends(get_db)):
    updated_post = posts_service.update_post(db, post_id, post)
    if updated_post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {post_id} was not found")
    return {"data": updated_post}
