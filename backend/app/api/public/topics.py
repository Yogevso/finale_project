"""Public Topics API - No Authentication Required"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, DocumentStatus, DocumentVisibility, Topic
from app.schemas.public import PublicTopic, PublicTopicsResponse

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/topics", response_model=PublicTopicsResponse)
def list_public_topics(db: Session = Depends(get_db)):
    """
    List all topics with counts of public published documents.
    """
    topics = db.query(Topic).order_by(Topic.name.asc()).all()

    counts = dict(
        db.query(Document.topic, func.count(Document.id))
        .filter(
            Document.visibility == DocumentVisibility.PUBLIC,
            Document.status == DocumentStatus.ACTIVE,
            Document.topic != None,  # noqa: E711
            Document.topic != "",
        )
        .group_by(Document.topic)
        .all()
    )

    items = [
        PublicTopic(
            name=topic.name,
            slug=topic.slug,
            description=topic.description,
            image_url=topic.image_url,
            document_count=counts.get(topic.slug, 0),
        )
        for topic in topics
    ]

    return PublicTopicsResponse(items=items, total=len(items))


@router.get("/topics/{slug}", response_model=PublicTopic)
def get_public_topic(slug: str, db: Session = Depends(get_db)):
    """
    Get a single topic by slug with public document count.
    """
    topic = db.query(Topic).filter(Topic.slug == slug).first()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found")

    count = (
        db.query(func.count(Document.id))
        .filter(
            Document.visibility == DocumentVisibility.PUBLIC,
            Document.status == DocumentStatus.ACTIVE,
            Document.topic == topic.slug,
        )
        .scalar()
    )

    return PublicTopic(
        name=topic.name,
        slug=topic.slug,
        description=topic.description,
        image_url=topic.image_url,
        document_count=count or 0,
    )
