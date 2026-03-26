"""Collaboration state and status endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters import CollaborationContractAdapter
from app.collaboration.dependencies import get_collab_state_manager
from app.collaboration.state_manager import CollabStateManager
from app.db import get_db
from app.dependencies.services import get_collaboration_service
from app.models import Document, User
from app.services.collaboration_service import CollaborationService
from app.security import get_current_active_user
from app.auth_context import CollaborationAuthService

router = APIRouter()
collaboration_bearer = HTTPBearer(auto_error=False)


class CollaboratorInfo(BaseModel):
    """Information about a collaborator."""

    user_id: int
    username: str
    color: str
    is_editing: bool = False


class CollaborationStatusResponse(BaseModel):
    """Response containing collaboration status for a document."""

    document_id: int
    active_collaborators: list[CollaboratorInfo]
    is_collaborative_mode: bool
    has_unsaved_changes: bool


class CollaborationAuthorizationResponse(BaseModel):
    """Response confirming collab token authorization for a document."""

    document_id: int
    user_id: int
    tenant_id: int
    permissions: list[str]


def _get_verified_collaboration_payload(
    document_id: int,
    credentials: HTTPAuthorizationCredentials | None = Depends(collaboration_bearer),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Collaboration token required",
        )

    payload = CollaborationAuthService().verify_collab_token(credentials.credentials)
    if payload is None or payload.get("document_id") != str(document_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collaboration token",
        )
    return payload


# Note: The /auth/collab-token endpoint is in auth.py (the canonical endpoint).
@router.get("/collaboration/documents/{document_id}/state")
async def get_document_state(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    state_manager: CollabStateManager = Depends(get_collab_state_manager),
):
    """
    Get the Yjs state for a document.

    This endpoint is called by the Hocuspocus server to load document state.
    Returns binary data (application/octet-stream).
    """
    state = state_manager.get_document_state(
        document_id=document_id,
        current_user=current_user,
    )

    return Response(
        content=state,
        media_type="application/octet-stream",
    )


@router.put("/collaboration/documents/{document_id}/state")
async def save_document_state(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    state_manager: CollabStateManager = Depends(get_collab_state_manager),
):
    """
    Save the Yjs state for a document.

    This endpoint is called by the Hocuspocus server to persist document state.
    Expects binary data (application/octet-stream).
    """
    state = await request.body()
    return state_manager.save_document_state(
        document_id=document_id,
        current_user=current_user,
        state=state,
    )


@router.delete("/collaboration/documents/{document_id}/state")
async def clear_document_state(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    state_manager: CollabStateManager = Depends(get_collab_state_manager),
):
    """
    Clear the Yjs state for a document.

    This resets the document's collaboration state. Use with caution.
    """
    return state_manager.clear_document_state(
        document_id=document_id,
        current_user=current_user,
    )


@router.get(
    "/collaboration/documents/{document_id}/status", response_model=CollaborationStatusResponse
)
async def get_collaboration_status(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    state_manager: CollabStateManager = Depends(get_collab_state_manager),
):
    """
    Get the collaboration status for a document.

    Returns information about active collaborators and document state.
    """
    payload = state_manager.get_collaboration_status(
        document_id=document_id,
        current_user=current_user,
    )
    return CollaborationStatusResponse(
        document_id=payload["document_id"],
        active_collaborators=[CollaboratorInfo(**c) for c in payload["active_collaborators"]],
        is_collaborative_mode=payload["is_collaborative_mode"],
        has_unsaved_changes=payload["has_unsaved_changes"],
    )


@router.get(
    "/collaboration/documents/{document_id}/verify-access",
    response_model=CollaborationAuthorizationResponse,
)
async def verify_collaboration_access(
    document_id: int,
    token_payload: dict[str, Any] = Depends(_get_verified_collaboration_payload),
    db: Session = Depends(get_db),
    collab_service: CollaborationService = Depends(get_collaboration_service),
):
    """Re-validate a collaboration token against current backend tenant rules."""
    raw_user_id = token_payload.get("sub")
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collaboration token",
        ) from exc

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collaboration token",
        )

    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    token_tenant_id = token_payload.get("tenant_id")
    if not isinstance(token_tenant_id, int) or user.tenant_id != token_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collaboration token tenant mismatch",
        )

    if document.tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant collaboration is not allowed",
        )

    permissions = collab_service.get_user_permissions_for_document(user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    requested_permissions = CollaborationContractAdapter().normalize_permissions(
        token_payload.get("permissions", [])
    )
    if not requested_permissions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid collaboration token",
        )
    if any(permission not in permissions for permission in requested_permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collaboration token permissions are no longer valid",
        )

    return CollaborationAuthorizationResponse(
        document_id=document_id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        permissions=permissions,
    )
