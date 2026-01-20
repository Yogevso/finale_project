"""Engagement API - Bookmarks, Feedback, Reading Progress"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import get_current_user
from app.models import User, Document, Bookmark, Feedback, ReadingProgress

router = APIRouter(prefix="/engagement", tags=["Engagement"])


# ============ SCHEMAS ============

class BookmarkResponse(BaseModel):
    id: int
    document_id: int
    document_title: str
    document_number: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    is_helpful: bool
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    document_id: int
    is_helpful: bool
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    document_id: int
    helpful_count: int
    not_helpful_count: int
    total_count: int
    helpful_percentage: float


class ReadingProgressUpdate(BaseModel):
    progress_percent: int  # 0-100


class ReadingProgressResponse(BaseModel):
    id: int
    document_id: int
    document_title: str
    progress_percent: int
    last_read_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============ BOOKMARKS ============

@router.get("/bookmarks", response_model=List[BookmarkResponse])
def list_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's bookmarked documents"""
    bookmarks = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id
    ).order_by(Bookmark.created_at.desc()).all()
    
    return [
        BookmarkResponse(
            id=b.id,
            document_id=b.document_id,
            document_title=b.document.title,
            document_number=b.document.document_number,
            created_at=b.created_at,
        )
        for b in bookmarks
    ]


@router.post("/bookmarks/{document_id}", response_model=BookmarkResponse)
def add_bookmark(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bookmark a document"""
    # Check document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if already bookmarked
    existing = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.document_id == document_id
    ).first()
    
    if existing:
        return BookmarkResponse(
            id=existing.id,
            document_id=existing.document_id,
            document_title=document.title,
            document_number=document.document_number,
            created_at=existing.created_at,
        )
    
    bookmark = Bookmark(
        user_id=current_user.id,
        document_id=document_id,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    
    return BookmarkResponse(
        id=bookmark.id,
        document_id=bookmark.document_id,
        document_title=document.title,
        document_number=document.document_number,
        created_at=bookmark.created_at,
    )


@router.delete("/bookmarks/{document_id}")
def remove_bookmark(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a bookmark"""
    bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.document_id == document_id
    ).first()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    return {"message": "Bookmark removed"}


@router.get("/bookmarks/{document_id}/status")
def check_bookmark_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if document is bookmarked"""
    bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.document_id == document_id
    ).first()
    
    return {"is_bookmarked": bookmark is not None}


# ============ FEEDBACK / RATINGS ============

@router.post("/feedback/{document_id}", response_model=FeedbackResponse)
def submit_feedback(
    document_id: int,
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback for a document (helpful/not helpful)"""
    # Check document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if user already submitted feedback
    existing = db.query(Feedback).filter(
        Feedback.user_id == current_user.id,
        Feedback.document_id == document_id
    ).first()
    
    if existing:
        # Update existing feedback
        existing.is_helpful = data.is_helpful
        existing.comment = data.comment
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new feedback
    feedback = Feedback(
        user_id=current_user.id,
        document_id=document_id,
        is_helpful=data.is_helpful,
        comment=data.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    
    return feedback


@router.get("/feedback/{document_id}/stats", response_model=FeedbackStats)
def get_feedback_stats(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Get feedback statistics for a document (public)"""
    helpful = db.query(func.count(Feedback.id)).filter(
        Feedback.document_id == document_id,
        Feedback.is_helpful == True
    ).scalar() or 0
    
    not_helpful = db.query(func.count(Feedback.id)).filter(
        Feedback.document_id == document_id,
        Feedback.is_helpful == False
    ).scalar() or 0
    
    total = helpful + not_helpful
    percentage = (helpful / total * 100) if total > 0 else 0
    
    return FeedbackStats(
        document_id=document_id,
        helpful_count=helpful,
        not_helpful_count=not_helpful,
        total_count=total,
        helpful_percentage=round(percentage, 1),
    )


@router.get("/feedback/{document_id}/my")
def get_my_feedback(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's feedback for a document"""
    feedback = db.query(Feedback).filter(
        Feedback.user_id == current_user.id,
        Feedback.document_id == document_id
    ).first()
    
    if not feedback:
        return {"has_feedback": False, "is_helpful": None}
    
    return {
        "has_feedback": True,
        "is_helpful": feedback.is_helpful,
        "comment": feedback.comment,
    }


# ============ READING PROGRESS ============

@router.get("/progress", response_model=List[ReadingProgressResponse])
def list_reading_progress(
    completed_only: bool = Query(False, description="Show only completed documents"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's reading progress"""
    query = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id
    )
    
    if completed_only:
        query = query.filter(ReadingProgress.completed_at.isnot(None))
    
    progress_list = query.order_by(ReadingProgress.last_read_at.desc()).all()
    
    return [
        ReadingProgressResponse(
            id=p.id,
            document_id=p.document_id,
            document_title=p.document.title,
            progress_percent=p.progress_percent,
            last_read_at=p.last_read_at,
            completed_at=p.completed_at,
        )
        for p in progress_list
    ]


@router.put("/progress/{document_id}", response_model=ReadingProgressResponse)
def update_reading_progress(
    document_id: int,
    data: ReadingProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update reading progress for a document"""
    # Validate progress
    if data.progress_percent < 0 or data.progress_percent > 100:
        raise HTTPException(status_code=400, detail="Progress must be 0-100")
    
    # Check document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find or create progress record
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.document_id == document_id
    ).first()
    
    now = datetime.utcnow()
    
    if progress:
        progress.progress_percent = data.progress_percent
        progress.last_read_at = now
        if data.progress_percent >= 100 and not progress.completed_at:
            progress.completed_at = now
    else:
        progress = ReadingProgress(
            user_id=current_user.id,
            document_id=document_id,
            progress_percent=data.progress_percent,
            last_read_at=now,
            completed_at=now if data.progress_percent >= 100 else None,
        )
        db.add(progress)
    
    db.commit()
    db.refresh(progress)
    
    return ReadingProgressResponse(
        id=progress.id,
        document_id=progress.document_id,
        document_title=document.title,
        progress_percent=progress.progress_percent,
        last_read_at=progress.last_read_at,
        completed_at=progress.completed_at,
    )


@router.get("/progress/{document_id}")
def get_document_progress(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reading progress for a specific document"""
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.document_id == document_id
    ).first()
    
    if not progress:
        return {
            "has_progress": False,
            "progress_percent": 0,
            "is_completed": False,
        }
    
    return {
        "has_progress": True,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.completed_at is not None,
        "last_read_at": progress.last_read_at,
    }


@router.get("/stats")
def get_engagement_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get engagement stats for current user"""
    bookmark_count = db.query(func.count(Bookmark.id)).filter(
        Bookmark.user_id == current_user.id
    ).scalar() or 0
    
    feedback_count = db.query(func.count(Feedback.id)).filter(
        Feedback.user_id == current_user.id
    ).scalar() or 0
    
    reading_count = db.query(func.count(ReadingProgress.id)).filter(
        ReadingProgress.user_id == current_user.id
    ).scalar() or 0
    
    completed_count = db.query(func.count(ReadingProgress.id)).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.completed_at.isnot(None)
    ).scalar() or 0
    
    return {
        "bookmarks": bookmark_count,
        "feedbacks_given": feedback_count,
        "documents_started": reading_count,
        "documents_completed": completed_count,
    }
