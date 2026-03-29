"""Public Topics API - No Authentication Required"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, DocumentStatus, DocumentVisibility, Topic
from app.schemas.public import PublicTopic, PublicTopicsResponse
from app.utils.topic_normalization import build_topic_lookup, normalize_topic_to_slug

router = APIRouter(prefix="/public", tags=["Public"])


def _published_document_ids_subquery(db: Session):
    from app.models import Version

    return (
        db.query(Version.document_id)
        .filter(Version.is_published.is_(True))
        .group_by(Version.document_id)
        .subquery()
    )


def _public_topic_counts(db: Session, topics: list[Topic]) -> dict[str, int]:
    topic_lookup = build_topic_lookup(topics)
    canonical_slugs = {topic.slug for topic in topics}
    published_doc_ids = _published_document_ids_subquery(db)

    raw_counts = (
        db.query(Document.topic, func.count(Document.id))
        .filter(
            Document.visibility == DocumentVisibility.PUBLIC,
            Document.status == DocumentStatus.ACTIVE,
            Document.deleted_at.is_(None),
            Document.id.in_(db.query(published_doc_ids.c.document_id)),
            Document.topic != None,  # noqa: E711
            Document.topic != "",
        )
        .group_by(Document.topic)
        .all()
    )

    counts: dict[str, int] = {slug: 0 for slug in canonical_slugs}
    for raw_topic, count in raw_counts:
        canonical = normalize_topic_to_slug(raw_topic, topic_lookup)
        if canonical in canonical_slugs:
            counts[canonical] = counts.get(canonical, 0) + int(count)

    return counts


@router.get("/topics", response_model=PublicTopicsResponse)
def list_public_topics(db: Session = Depends(get_db)):
    """
    List all topics with counts of public published documents.
    """
    topics = db.query(Topic).order_by(Topic.name.asc()).all()
    counts = _public_topic_counts(db, topics)

    items = [
        PublicTopic(
            name=topic.name,
            slug=topic.slug,
            description=topic.description,
            image_url=topic.image_url,
            document_count=counts.get(topic.slug, 0) or 0,
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
    count = _public_topic_counts(db, [topic]).get(topic.slug, 0)

    return PublicTopic(
        name=topic.name,
        slug=topic.slug,
        description=topic.description,
        image_url=topic.image_url,
        document_count=count or 0,
    )
