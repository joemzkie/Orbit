from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from dbconn import get_db
from schemas.post import PostCreate, PostUpdate
from services import posts as posts_service

# Group post endpoints under the Posts API documentation tag.
router = APIRouter(tags=["Posts"])


@router.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    """Return all persisted posts using an injected database session."""

    # Wrap all fetched post records in the endpoint's response payload.
    return {"DATA": posts_service.fetch_all_posts(db)}


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_posts(post: PostCreate, db: Session = Depends(get_db)):
    """Create a post from validated request data and return it."""

    # Persist the request data and expose the newly created post.
    return {"data": posts_service.create_post(db, post)}


@router.get("/posts/latest")
def get_latest_posts(db: Session = Depends(get_db)):
    """Return the ten newest posts or a message when none exist."""

    # Fetch the most recent post records through the service layer.
    posts = posts_service.fetch_post_latest(db)
    # Return a descriptive payload when the collection is empty.
    if not posts:
        return {"Message": "No available posts"}
    # Return the newest posts when at least one record is available.
    return {"Details": posts}


@router.get("/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Return one post by ID or raise an HTTP 404 response."""

    # Look up the requested post through the service layer.
    post = posts_service.fetch_post_by_id(db, post_id)
    # Translate a missing database record into a client-visible 404 error.
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {post_id} was not found")
    # Return the found post in the endpoint's response payload.
    return {"post_detail": post}


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete one post by ID or raise an HTTP 404 response."""

    # Attempt deletion and raise an error when no matching post exists.
    if not posts_service.delete_post(db, post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {post_id} was not found")
    # Return the declared empty success response after deletion.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/put/{post_id}")
def update_post(post_id: int, post: PostUpdate, db: Session = Depends(get_db)):
    """Update a post by ID or raise an HTTP 404 response."""

    # Apply the validated request data through the service layer.
    updated_post = posts_service.update_post(db, post_id, post)
    # Translate a missing database record into a client-visible 404 error.
    if updated_post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {post_id} was not found")
    # Return the refreshed post after its update was committed.
    return {"data": updated_post}
