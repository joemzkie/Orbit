from fastapi import FastAPI, Response, status, HTTPException
from fastapi.params import Body
from pydantic import BaseModel
from typing import Optional
from random import randrange 

import crud

class Post(BaseModel):
    title: str
    content: str
    published: bool = True
    rating: Optional[int] = None

app = FastAPI()


@app.get("/posts")
def get_posts():
    get_all_post = crud.fetch_all_posts()
    return {"DATA": get_all_post}

@app.post("/posts", status_code= status.HTTP_201_CREATED)
def create_posts(post: Post):
    post_dict = post.dict()
    # The CRUD function is named create_post (singular); calling create_posts
    # raises AttributeError and FastAPI returns an internal-server-error response.
    post_create = crud.create_post(post_dict)
    return {"data": post_create}

@app.get("/posts/latest")
def get_latest_posts():
    post = crud.fetch_post_latest()
    if not post:
        return {"Message": "No available posts"}
   
    return {"Details": post}

@app.get("/posts/{id}")
def getpost(id: int, response: Response):
    search_post = crud.fetch_post_by_id(id)
    if not search_post:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND, 
            detail= f"post with id: {id} was not found"
            )
    return {"post_detail": search_post}

@app.delete("/posts/{id}", status_code= status.HTTP_204_NO_CONTENT)
def delete_post(id: int, response: Response):
    
    post = crud.delete_post(id)
    
    if post is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= f"post with id: {id} was not found"
        )

    return Response(status_code= status.HTTP_204_NO_CONTENT)

@app.put("/put/{id}")
def update_post(id: int, post: Post):
    # CRUD indexes data by key, so pass the Pydantic model as a dictionary.
    update_post = crud.update_post(id, post.model_dump())
    
    if update_post is None:
        raise HTTPException(
        status_code= status.HTTP_404_NOT_FOUND,
        detail=f"post with id: {id} was not found"
    )
    
    return {"data": update_post}
    
