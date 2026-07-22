import asyncio
import os
import re
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError
from starlette.middleware.base import BaseHTTPMiddleware
from supabase import create_client

from idempotency import IdempotencyMiddleware
from rate_limit import RateLimitMiddleware
from routers import auth, posts, users


def validate_production_settings() -> None:
    """Fail early when a production deployment is missing critical infrastructure."""

    if os.getenv("ENVIRONMENT", "development").lower() != "production":
        return
    required = ("DATABASE_URL", "JWT_SECRET", "CORS_ORIGINS", "REDIS_URL", "SUPABASE_URL", "SUPABASE_KEY")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required production environment variables: {', '.join(missing)}")
    if os.getenv("COOKIE_SECURE", "false").lower() != "true":
        raise RuntimeError("COOKIE_SECURE must be true in production")
    if os.getenv("COOKIE_SAMESITE", "").lower() != "none":
        raise RuntimeError("COOKIE_SAMESITE must be none for Vercel-to-Render cookie sessions")


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

    validate_production_settings()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    # Keep an optional server-only client available for future storage/auth operations.
    app.state.supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
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


def cors_policy() -> tuple[list[str], str | None]:
    """Convert configured Vercel wildcard origins into Starlette's safe regex format."""

    exact_origins: list[str] = []
    wildcard_patterns: list[str] = []
    configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    for origin in (value.strip() for value in configured_origins.split(",")):
        if not origin:
            continue
        if "*" in origin:
            wildcard_patterns.append(re.escape(origin).replace(r"\*", r"[a-z0-9-]+"))
        else:
            exact_origins.append(origin)
    return exact_origins, f"^({'|'.join(wildcard_patterns)})$" if wildcard_patterns else None


# Restrict browser requests to explicit origins; wildcard Vercel previews are regex-matched.
cors_origins, cors_origin_regex = cors_policy()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
)
# Apply bounded timing, distributed abuse protection, and mutation retry safety.
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTimeoutMiddleware)
# Register post, user-registration, and authenticated session endpoints.
app.include_router(posts.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    """Provide a lightweight Render liveness probe that does not require database work."""

    return {"status": "ok"}


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


if __name__ == "__main__":
    # Render supplies PORT dynamically; 8000 remains convenient for local execution.
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
