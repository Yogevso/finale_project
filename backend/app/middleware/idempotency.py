"""Idempotency-key middleware for retry-safe write endpoints."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.db import SessionLocal
from app.models import IdempotencyKeyRecord
from app.security import verify_token


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Deduplicate selected write operations using persisted idempotency keys."""

    _TARGET_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
    _TARGET_PATH_PATTERNS = (
        re.compile(r"^/api/v1/documents/upload$"),
        re.compile(r"^/api/v1/documents/\d+/versions/\d+/publish$"),
        re.compile(r"^/api/v1/invitations$"),
        re.compile(r"^/api/v1/invitations/\d+/resend$"),
        re.compile(r"^/api/v1/documents/\d+/comments$"),
        re.compile(r"^/api/v1/documents/\d+/companies/batch$"),
        re.compile(r"^/api/v1/reviews/documents/\d+/submit$"),
        re.compile(r"^/api/v1/reviews/\d+/(approve|reject|cancel)$"),
    )
    _PROCESSING_TIMEOUT = timedelta(minutes=5)

    @classmethod
    def _is_target_endpoint(cls, *, method: str, path: str) -> bool:
        if method not in cls._TARGET_METHODS:
            return False
        return any(pattern.match(path) for pattern in cls._TARGET_PATH_PATTERNS)

    @staticmethod
    def _extract_user_scope(request: Request) -> tuple[str, int | None]:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return ("anon", None)

        payload = verify_token(auth_header[7:].strip())
        if not payload:
            return ("anon", None)

        raw_user_id = payload.get("sub")
        if raw_user_id is None:
            return ("anon", None)

        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            return ("anon", None)
        return (f"user:{user_id}", user_id)

    @staticmethod
    def _request_hash(request: Request, body: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(request.method.encode("utf-8"))
        digest.update(b"|")
        digest.update(request.url.path.encode("utf-8"))
        digest.update(b"|")
        digest.update(request.url.query.encode("utf-8"))
        digest.update(b"|")
        digest.update(body)
        return digest.hexdigest()

    @staticmethod
    async def _extract_response_body(response: Response) -> bytes:
        body = bytearray()
        async for chunk in response.body_iterator:
            body.extend(chunk)
        return bytes(body)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        if not self._is_target_endpoint(method=method, path=path):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)
        idempotency_key = idempotency_key.strip()
        if not idempotency_key:
            return JSONResponse(status_code=400, content={"detail": "Idempotency-Key cannot be blank"})

        body = await request.body()
        request_hash = self._request_hash(request, body)
        user_scope, user_id = self._extract_user_scope(request)

        record_id: int | None = None
        now = datetime.utcnow()
        db = SessionLocal()
        try:
            record = (
                db.query(IdempotencyKeyRecord)
                .filter(
                    IdempotencyKeyRecord.idempotency_key == idempotency_key,
                    IdempotencyKeyRecord.method == method,
                    IdempotencyKeyRecord.path == path,
                    IdempotencyKeyRecord.user_scope == user_scope,
                )
                .first()
            )

            if record:
                if record.request_hash != request_hash:
                    return JSONResponse(
                        status_code=409,
                        content={"detail": "Idempotency-Key already used with different request payload"},
                    )

                if record.status == "completed" and record.response_status is not None:
                    replay_headers = {}
                    if record.response_content_type:
                        replay_headers["content-type"] = record.response_content_type
                    replay = Response(
                        content=(record.response_body or "").encode("utf-8"),
                        status_code=record.response_status,
                        headers=replay_headers,
                    )
                    replay.headers["X-Idempotent-Replay"] = "true"
                    return replay

                if record.status == "processing":
                    started_at = record.processing_started_at or record.updated_at or record.created_at
                    if started_at and started_at > now - self._PROCESSING_TIMEOUT:
                        return JSONResponse(
                            status_code=409,
                            content={"detail": "Request with this Idempotency-Key is already in progress"},
                        )

                record.status = "processing"
                record.processing_started_at = now
                record.last_error = None
                record.response_status = None
                record.response_body = None
                record.response_content_type = None
                db.commit()
                record_id = record.id
            else:
                record = IdempotencyKeyRecord(
                    idempotency_key=idempotency_key,
                    method=method,
                    path=path,
                    user_scope=user_scope,
                    user_id=user_id,
                    request_hash=request_hash,
                    status="processing",
                    processing_started_at=now,
                )
                db.add(record)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    return JSONResponse(
                        status_code=409,
                        content={"detail": "Concurrent request detected for this Idempotency-Key"},
                    )
                db.refresh(record)
                record_id = record.id
        finally:
            db.close()

        try:
            response = await call_next(request)
        except Exception as exc:  # policy: BOUNDARY — idempotency middleware converts storage errors into stable responses
            update_db = SessionLocal()
            try:
                record = update_db.query(IdempotencyKeyRecord).filter(IdempotencyKeyRecord.id == record_id).first()
                if record:
                    record.status = "failed"
                    record.last_error = str(exc)
                    record.processing_started_at = None
                    update_db.commit()
            finally:
                update_db.close()
            raise

        response_body = await self._extract_response_body(response)
        response_headers = dict(response.headers)
        response_content_type = response_headers.get("content-type")
        if not response_content_type:
            response_content_type = response.media_type

        update_db = SessionLocal()
        try:
            record = update_db.query(IdempotencyKeyRecord).filter(IdempotencyKeyRecord.id == record_id).first()
            if record:
                if response.status_code >= 500:
                    record.status = "failed"
                    record.last_error = f"http_{response.status_code}"
                    record.processing_started_at = None
                else:
                    record.status = "completed"
                    record.response_status = response.status_code
                    record.response_body = response_body.decode("utf-8", errors="replace")
                    record.response_content_type = response_content_type
                    record.processing_started_at = None
                    record.last_error = None
                update_db.commit()
        finally:
            update_db.close()

        replayable_response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=response_headers,
            background=response.background,
        )
        return replayable_response
