from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, UploadFile, status

from app.schemas.chat import SupportTicketMessageResponse
from app.services.support_service import SupportTicketService


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    if normalized in {"", "0", "false", "no", "off"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"{field_name} must be a boolean",
    )


async def parse_support_message_request(
    request: Request,
    *,
    allow_internal_note: bool,
) -> tuple[str, bool, UploadFile | None]:
    content_type = (request.headers.get("content-type") or "").lower()
    content = ""
    is_internal_note = False
    upload: UploadFile | None = None

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception as exc:  # policy: BOUNDARY — invalid request parsing becomes a client-facing request error
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        content = str(payload.get("content") or "")
        is_internal_note = _coerce_bool(
            payload.get("is_internal_note"),
            field_name="is_internal_note",
        )
    elif (
        "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type
    ):
        form = await request.form()
        content = str(form.get("content") or "")
        is_internal_note = _coerce_bool(
            form.get("is_internal_note"),
            field_name="is_internal_note",
        )
        maybe_file = form.get("file")
        if (
            maybe_file is not None
            and hasattr(maybe_file, "filename")
            and hasattr(maybe_file, "read")
            and getattr(maybe_file, "filename", None)
        ):
            upload = maybe_file
    else:
        raise HTTPException(status_code=415, detail="Unsupported media type")

    if len(content) > 10000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="content must be at most 10000 characters",
        )
    if is_internal_note and not allow_internal_note:
        raise HTTPException(status_code=403, detail="Customers cannot create internal notes")
    return content, is_internal_note, upload


def support_message_to_response(message) -> SupportTicketMessageResponse:
    sender = getattr(message, "sender", None)
    return SupportTicketMessageResponse(
        id=message.id,
        ticket_id=message.ticket_id,
        sender_id=message.sender_id,
        sender_type=message.sender_type,
        content=message.content,
        is_internal_note=message.is_internal_note,
        file_url=(
            SupportTicketService.build_message_file_url(message.ticket_id, message.id)
            if message.file_storage_key
            else None
        ),
        file_name=message.file_name,
        file_size=message.file_size,
        file_mime_type=message.file_mime_type,
        created_at=message.created_at,
        sender_full_name=sender.full_name if sender else None,
    )
