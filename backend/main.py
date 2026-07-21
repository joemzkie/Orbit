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

my_posts = []

def find_post(id):
    for p in my_posts:
        if p["id"] == id:
            return p
    return None

# FIX 2: Updated to use enumerate so it returns the actual list index (integer)
def find_index(id: int):
    for i, p in enumerate(my_posts):
        if p["id"] == id:
            return i
    return None

@app.get("/")
def root():
    return {"message": "hello world"}

@app.get("/posts")
def get_posts():
    get_all_post = crud.fetch_all_posts()
    return {"DATA": get_all_post}

@app.post("/posts", status_code= status.HTTP_201_CREATED)
def create_posts(post: Post):
    post_dict = post.dict()
    post_dict['id'] = randrange(0, 1000000) 
    my_posts.append(post_dict)
    return {"data": post_dict}

@app.get("/posts/latest")
def get_latest_posts():
    if not my_posts:
        return {"Message": "No available posts"}
    post = my_posts[len(my_posts)-1]
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
    index = find_index(id)
    
    # FIX 3: Changed to 'is None' to avoid bugs when the index is 0
    if index is None:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= f"post with id: {id} was not found"
        )
        
    my_posts.pop(index)
    
    # FIX 1: Replaced () with {} to return a valid dictionary
    return Response(status_code= status.HTTP_204_NO_CONTENT)

@app.put("/put/{id}")
def update_post(id: int, post: Post):
    index = find_index(id)

    if index is None:
        raise HTTPException(
        status_code= status.HTTP_404_NOT_FOUND,
        detail=f"post with id: {id} was not found"
    )
    
    # Call the method to actually generate the dictionary
    post_dict = post.dict() # Use post.model_dump() if using Pydantic v2
    
    # Use a string 'id' for the dictionary key
    post_dict['id'] = id
    my_posts[index] = post_dict
    return {"data": post_dict}
    
