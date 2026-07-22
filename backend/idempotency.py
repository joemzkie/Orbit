import hashlib
import json
from datetime import UTC, datetime, timedelta

from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from auth import AUTH_COOKIE_NAME, decode_access_token
from dbconn import SessionLocal
from models.idempotency import IdempotencyKey


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Persist successful mutation responses for safe client retries."""

    async def dispatch(self, request: Request, call_next):
        """Require, register, replay, and finalize idempotency keys for mutations."""

        if request.method not in {"POST", "PUT", "DELETE"}:
            return await call_next(request)
        key = request.headers.get("Idempotency-Key")
        if not key or len(key) > 255:
            return JSONResponse(status_code=400, content={"detail": "A valid Idempotency-Key header is required", "code": "idempotency_key_required"})
        body = await request.body()
        request_hash = hashlib.sha256(body).hexdigest()
        subject = decode_access_token(request.cookies.get(AUTH_COOKIE_NAME))
        client_ip = request.client.host if request.client else "unknown"
        principal = f"user:{subject}" if subject else f"ip:{client_ip}"
        scope = f"{request.method}:{request.url.path}:{principal}"
        created_new = False
        async with SessionLocal() as db:
            # Read an existing record before attempting to reserve a new key.
            record = await db.scalar(select(IdempotencyKey).where(IdempotencyKey.scope == scope, IdempotencyKey.key == key))
            if record is None:
                created_new = True
                record = IdempotencyKey(
                    scope=scope,
                    key=key,
                    request_hash=request_hash,
                    state="processing",
                    expires_at=datetime.now(UTC) + timedelta(hours=24),
                )
                db.add(record)
                try:
                    await db.commit()
                except IntegrityError:
                    # Resolve the unique-key race by reading the request that won it.
                    await db.rollback()
                    record = await db.scalar(select(IdempotencyKey).where(IdempotencyKey.scope == scope, IdempotencyKey.key == key))
                    created_new = False
            if record is None:
                return JSONResponse(status_code=503, content={"detail": "Unable to reserve idempotency key", "code": "idempotency_unavailable"})
            if record.request_hash != request_hash:
                return JSONResponse(status_code=409, content={"detail": "Idempotency key was reused with a different request", "code": "idempotency_conflict"})
            if record.state == "completed":
                # Restore session cookies as well as the response body for a retried login request.
                replay = Response(content=record.response_body or b"", status_code=record.response_status or 200, media_type="application/json", headers={"Idempotency-Replayed": "true"})
                for set_cookie in json.loads(record.response_headers or "[]"):
                    replay.headers.append("set-cookie", set_cookie)
                return replay
            if not created_new:
                return JSONResponse(status_code=409, content={"detail": "An identical request is still processing", "code": "idempotency_in_progress"})
            record_id = record.id
        response = await call_next(request)
        # Buffer the small JSON API response so an identical retry can receive the same result.
        content = b"".join([chunk async for chunk in response.body_iterator])
        if response.status_code < 500:
            async with SessionLocal() as db:
                record = await db.get(IdempotencyKey, record_id)
                if record is not None:
                    record.state = "completed"
                    record.response_status = response.status_code
                    record.response_body = content.decode("utf-8")
                    record.response_headers = json.dumps(response.headers.getlist("set-cookie"))
                    await db.commit()
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(content=content, status_code=response.status_code, headers=headers, media_type=response.media_type)
