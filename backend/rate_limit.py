import os

from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from auth import AUTH_COOKIE_NAME, decode_access_token


# Atomically refill and consume a Redis token bucket for one request principal.
TOKEN_BUCKET_SCRIPT = """
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local values = redis.call('HMGET', KEYS[1], 'tokens', 'updated_at')
local tokens = tonumber(values[1]) or capacity
local updated_at = tonumber(values[2]) or now
tokens = math.min(capacity, tokens + ((now - updated_at) * refill))
if tokens < cost then
  redis.call('HMSET', KEYS[1], 'tokens', tokens, 'updated_at', now)
  redis.call('EXPIRE', KEYS[1], 120)
  return {0, math.ceil((cost - tokens) / refill)}
end
tokens = tokens - cost
redis.call('HMSET', KEYS[1], 'tokens', tokens, 'updated_at', now)
redis.call('EXPIRE', KEYS[1], 120)
return {1, 0}
"""


def request_principal(request: Request) -> str:
    """Return an authenticated email or direct client IP for rate-limit scope."""

    # Prefer a validated authenticated identity over an address shared by many users.
    email = decode_access_token(request.cookies.get(AUTH_COOKIE_NAME))
    if email:
        return f"user:{email}"
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply Redis-backed token buckets before route handlers run."""

    async def dispatch(self, request: Request, call_next):
        """Reject requests that exceed the configured bucket allowance."""

        # Skip documentation and CORS preflight traffic because they have no data side effects.
        if request.method == "OPTIONS" or request.url.path in {"/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        is_authentication = request.url.path in {"/auth/login", "/auth/signup", "/auth/me/password"}
        is_mutation = request.method in {"POST", "PUT", "DELETE"}
        capacity = 5 if is_authentication else 20 if is_mutation else 60
        redis_client: Redis | None = getattr(request.app.state, "redis", None)
        if redis_client is None:
            # Fail closed for state-changing traffic when distributed protection is unavailable.
            if is_mutation:
                return JSONResponse(status_code=503, content={"detail": "Rate limiter unavailable", "code": "rate_limiter_unavailable"})
            return await call_next(request)
        try:
            # Use a one-minute refill rate and a bucket key scoped to the caller and route class.
            import time

            principal = request_principal(request)
            bucket = "authentication" if is_authentication else "mutation" if is_mutation else "read"
            allowed, retry_after = await redis_client.eval(
                TOKEN_BUCKET_SCRIPT,
                1,
                f"orbit:rate:{bucket}:{principal}",
                time.time(),
                capacity,
                capacity / 60,
                1,
            )
        except Exception:
            # Never allow unprotected mutations when the distributed limiter cannot be contacted.
            if is_mutation:
                return JSONResponse(status_code=503, content={"detail": "Rate limiter unavailable", "code": "rate_limiter_unavailable"})
            return await call_next(request)
        if not allowed:
            # Tell clients exactly when a compliant retry can be attempted.
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests", "code": "rate_limited"},
                headers={"Retry-After": str(max(1, int(retry_after)))},
            )
        return await call_next(request)
