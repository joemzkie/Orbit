import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError
from starlette.middleware.base import BaseHTTPMiddleware

from idempotency import IdempotencyMiddleware
from rate_limit import RateLimitMiddleware
from routers import auth, posts, users


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce the API's maximum request duration."""

    async def dispatch(self, request: Request, call_next):
        """Return a clean gateway timeout when a route exceeds ten seconds."""

        try:
            # Cancel async work that remains after the database's nine-second statement limit.
            async with asyncio.timeout(10):
                return await call_next(request)
        except TimeoutError:
            return JSONResponse(status_code=504, content={"detail": "The request timed out", "code": "request_timeout"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect optional shared infrastructure without crashing application startup."""

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        # Validate the Redis connection once so rate limiting can fail safely when unavailable.
        redis_client = Redis.from_url(redis_url, decode_responses=False)
        await redis_client.ping()
        app.state.redis = redis_client
    except Exception:
        app.state.redis = None
    try:
        yield
    finally:
        redis_client = getattr(app.state, "redis", None)
        if redis_client is not None and hasattr(redis_client, "aclose"):
            await redis_client.aclose()


# Create the FastAPI application that serves the backend API.
app = FastAPI(title="Orbit API", lifespan=lifespan)
# Restrict browser requests to explicit frontend origins instead of allowing every website.
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)
# Apply bounded timing, distributed abuse protection, and mutation retry safety.
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTimeoutMiddleware)
# Register post, user-registration, and authenticated session endpoints.
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)


@app.exception_handler(SQLAlchemyTimeoutError)
async def database_pool_timeout(_request: Request, _error: SQLAlchemyTimeoutError):
    """Return service-unavailable when no database connection can be acquired."""

    return JSONResponse(status_code=503, content={"detail": "Database is temporarily unavailable", "code": "database_unavailable"})


@app.exception_handler(OperationalError)
async def database_operational_error(_request: Request, error: OperationalError):
    """Map PostgreSQL cancellation and outage errors to safe API responses."""

    sqlstate = getattr(error.orig, "sqlstate", None)
    if sqlstate == "57014":
        return JSONResponse(status_code=504, content={"detail": "The database query timed out", "code": "database_timeout"})
    return JSONResponse(status_code=503, content={"detail": "Database is temporarily unavailable", "code": "database_unavailable"})
