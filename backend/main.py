from fastapi import FastAPI

from routers import posts, users

# Create the FastAPI application that serves the backend API.
app = FastAPI()
# Register the endpoints that manage blog posts.
app.include_router(posts.router)
# Register the endpoints reserved for user-related features.
app.include_router(users.router)
