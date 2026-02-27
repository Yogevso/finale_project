"""Collaboration state and status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.repositories import DocumentRepository
from app.security import get_current_active_user
from app.services.collaboration_service import CollaborationService

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
    db: Session = Depends(get_db),
):
    """
    Get the Yjs state for a document.

    This endpoint is called by the Hocuspocus server to load document state.
    Returns binary data (application/octet-stream).
    """
    collaboration_service = CollaborationService()
    document_repository = DocumentRepository(db)

    # Get the document
    document = document_repository.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = collaboration_service.get_user_permissions_for_document(current_user, document)
    if "read" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Get the state
    state = document.yjs_state
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collaboration state exists for this document",
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
    db: Session = Depends(get_db),
):
    """
    Save the Yjs state for a document.

    This endpoint is called by the Hocuspocus server to persist document state.
    Expects binary data (application/octet-stream).
    """
    collaboration_service = CollaborationService()
    document_repository = DocumentRepository(db)

    # Get the document
    document = document_repository.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = collaboration_service.get_user_permissions_for_document(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this document",
        )

    # Read the binary state from request body
    state = await request.body()

    # Save the state
    success = collaboration_service.save_document_state_for_document(db, document_id, state)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document state",
        )

    return {"message": "State saved successfully", "size": len(state)}


@router.delete("/collaboration/documents/{document_id}/state")
async def clear_document_state(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Clear the Yjs state for a document.

    This resets the document's collaboration state. Use with caution.
    """
    collaboration_service = CollaborationService()
    document_repository = DocumentRepository(db)

    # Get the document
    document = document_repository.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions - only admins and managers can clear state
    permissions = collaboration_service.get_user_permissions_for_document(current_user, document)
    if "write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to clear this document's state",
        )

    # Clear the state
    success = collaboration_service.clear_document_state_for_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear document state",
        )

    return {"message": "State cleared successfully"}


@router.get(
    "/collaboration/documents/{document_id}/status", response_model=CollaborationStatusResponse
)
async def get_collaboration_status(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the collaboration status for a document.

    Returns information about active collaborators and document state.
    """
    collaboration_service = CollaborationService()
    document_repository = DocumentRepository(db)

    # Get the document
    document = document_repository.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Check permissions
    permissions = collaboration_service.get_user_permissions_for_document(current_user, document)
    if not permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this document",
        )

    # Get active collaborators (would query Hocuspocus in production)
    collaborators = collaboration_service.get_active_collaborators(document_id)

    return CollaborationStatusResponse(
        document_id=document_id,
        active_collaborators=[CollaboratorInfo(**c) for c in collaborators],
        is_collaborative_mode=document.yjs_state is not None,
        has_unsaved_changes=False,  # Would be tracked by Hocuspocus
    )
