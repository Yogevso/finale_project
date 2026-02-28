"""Collaboration state and status endpoints."""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.collaboration.dependencies import get_collab_state_manager
from app.collaboration.state_manager import CollabStateManager
from app.models import User
from app.security import get_current_active_user

router = APIRouter()


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
