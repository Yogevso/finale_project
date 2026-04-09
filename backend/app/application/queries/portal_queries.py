"""Application query handlers for customer-portal document read models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.domain.specifications import VisibilitySpec
from app.errors import NotFoundError
from app.feature_flags import BackendFeatureFlag, is_backend_feature_enabled
from app.models import (
    Attachment,
    Document,
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    FeedbackStatus,
    Platform,
    User,
    Version,
)
from app.projections import ProjectionCache, execute_cached_projection, get_projection_cache
from app.repositories import DocumentRepository
from app.schemas.portal import (
    FacetItem,
    PortalAttachment,
    PortalDashboardStats,
    PortalDocumentDetail,
    PortalDocumentTocItem,
    PortalDocumentListResponse,
    PortalDocumentSummary,
    PortalFacetsResponse,
)
from app.services.attachment_service import AttachmentService


@dataclass(frozen=True, slots=True)
class ListPortalDocumentsQuery:
    """List customer-visible documents query."""

    page: int
    per_page: int
    category: Optional[str]
    search: Optional[str]
    current_user: User
    topic: Optional[str] = None
    platform: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GetPortalDocumentQuery:
    """Get one customer-visible document query."""

    document_id: int
    current_user: User


@dataclass(frozen=True, slots=True)
class GetPortalAttachmentQuery:
    """Get one customer-visible attachment query."""

    document_id: int
    attachment_id: int
    current_user: User


@dataclass(frozen=True, slots=True)
class ListPortalCategoriesQuery:
    """List customer-visible categories query."""

    current_user: User


@dataclass(frozen=True, slots=True)
class PortalDashboardStatsQuery:
    """Portal dashboard stats query."""

    current_user: User


@dataclass(frozen=True, slots=True)
class SearchPortalDocumentsQuery:
    """Search customer-visible documents query."""

    q: str
    category: Optional[str]
    page: int
    per_page: int
    current_user: User


@dataclass(frozen=True, slots=True)
class ListPortalFacetsQuery:
    """Get facet counts for portal sidebar."""

    current_user: User


@dataclass(frozen=True, slots=True)
class RelatedDocumentsQuery:
    """Get documents related to a given document."""

    document_id: int
    current_user: User
    limit: int = 5


class PortalDocumentsQueryHandler:
    """Read-handler facade for customer portal document queries."""

    def __init__(
        self,
        db: Session,
        *,
        projection_cache: ProjectionCache | None = None,
    ):
        self.db = db
        self.projection_cache = projection_cache or get_projection_cache()

    @staticmethod
    def _customer_visibility_spec(user: User) -> VisibilitySpec:
        return VisibilitySpec.customer_portal(customer_tenant_id=user.tenant_id)

    def _ensure_customer_document_access(self, document: Document, user: User) -> None:
        """AF-005: Delegate to the central DocumentAccessPolicy."""
        from app.application.policies.access_policies import DocumentAccessPolicy
        policy = DocumentAccessPolicy()
        if not policy.can_view_document(user, document):
            raise NotFoundError("Document not found")

    def _customer_documents_query(self, user: User):
        repository = DocumentRepository(self.db)
        base = self._customer_visibility_spec(user).apply(repository.query(), Document)
        # H-23: Only include documents that have at least one published version
        published_doc_ids = (
            self.db.query(Version.document_id)
            .filter(Version.is_published.is_(True))
            .subquery()
        )
        return base.filter(Document.id.in_(published_doc_ids), Document.deleted_at.is_(None))

    @staticmethod
    def _tenant_scope(user: User) -> str:
        return f"tenant:{user.tenant_id}"

    def _execute_cached(
        self,
        *,
        projection_name: str,
        key_parts: tuple[object, ...],
        loader,
        ttl_seconds: int = 45,
        validator=None,
    ):
        if not is_backend_feature_enabled(BackendFeatureFlag.PROJECTION_CACHE):
            return loader()
        return execute_cached_projection(
            cache=self.projection_cache,
            namespace=f"portal.{projection_name}",
            key_parts=key_parts,
            scopes={"portal"},
            loader=loader,
            ttl_seconds=ttl_seconds,
            validator=validator,
        )

    @staticmethod
    def _portal_visible_version(document: Document) -> Version | None:
        """Return latest published version only — never fall back to draft (AF-001)."""
        if not document.versions:
            return None

        published_versions = [version for version in document.versions if version.is_published]
        if not published_versions:
            return None
        return max(published_versions, key=lambda version: version.version_number)

    def execute_list_documents(self, query: ListPortalDocumentsQuery) -> PortalDocumentListResponse:
        def load_projection() -> PortalDocumentListResponse:
            docs_query = self._customer_documents_query(query.current_user)
            if query.category:
                docs_query = docs_query.filter(Document.category == query.category)
            if query.topic:
                docs_query = docs_query.filter(Document.topic == query.topic)
            if query.platform:
                docs_query = docs_query.join(Platform, Document.platform_id == Platform.id).filter(Platform.name == query.platform)
            if query.date_from:
                docs_query = docs_query.filter(Document.updated_at >= query.date_from)
            if query.date_to:
                docs_query = docs_query.filter(Document.updated_at <= query.date_to)
            if query.search:
                search_term = f"%{query.search}%"
                docs_query = docs_query.filter(
                    or_(
                        Document.title.ilike(search_term),
                        Document.description.ilike(search_term),
                        Document.tags.ilike(search_term),
                    )
                )

            total = docs_query.count()
            pages = (total + query.per_page - 1) // query.per_page
            offset = (query.page - 1) * query.per_page
            documents = (
                docs_query.order_by(Document.updated_at.desc())
                .offset(offset)
                .limit(query.per_page)
                .all()
            )

            items: list[PortalDocumentSummary] = []
            for doc in documents:
                attachment_count = (
                    self.db.query(func.count(Attachment.id))
                    .filter(Attachment.document_id == doc.id)
                    .scalar()
                )
                visible_version = self._portal_visible_version(doc)
                version_number = visible_version.version_number if visible_version else 1
                published_at = visible_version.published_at if visible_version else None
                items.append(
                    PortalDocumentSummary(
                        id=doc.id,
                        document_number=doc.document_number,
                        title=doc.title,
                        description=doc.description,
                        category=doc.category,
                        topic=doc.topic,
                        platform=doc.platform_name,
                        release_branch=doc.release_branch,
                        tags=doc.tags,
                        visibility=doc.visibility.value if doc.visibility else "internal",
                        version=version_number,
                        created_at=doc.created_at,
                        updated_at=doc.updated_at,
                        published_at=published_at,
                        has_attachments=attachment_count > 0,
                    )
                )

            return PortalDocumentListResponse(
                items=items,
                total=total,
                page=query.page,
                per_page=query.per_page,
                total_pages=pages,
            )

        return self._execute_cached(
            projection_name="documents.list",
            key_parts=(
                self._tenant_scope(query.current_user),
                query.page,
                query.per_page,
                query.category,
                query.search,
                query.topic,
                query.platform,
                query.date_from,
                query.date_to,
            ),
            loader=load_projection,
            validator=lambda payload: isinstance(payload, PortalDocumentListResponse),
        )

    def execute_get_document(self, query: GetPortalDocumentQuery) -> PortalDocumentDetail:
        def load_projection() -> PortalDocumentDetail:
            document = (
                self.db.query(Document)
                .filter(Document.id == query.document_id, Document.deleted_at.is_(None))
                .first()
            )
            if not document:
                raise NotFoundError("Document not found")
            self._ensure_customer_document_access(document, query.current_user)
            visible_version = self._portal_visible_version(document)
            if visible_version is None:
                raise NotFoundError("Document not found")

            attachments = (
                self.db.query(Attachment).filter(Attachment.document_id == query.document_id).all()
            )
            toc_items: list[PortalDocumentTocItem] = []
            for attachment in attachments:
                stored_items = AttachmentService._get_stored_reader_toc_items(attachment)
                if not stored_items:
                    continue
                toc_items = [PortalDocumentTocItem(**item) for item in stored_items]
                break
            tags = [tag.strip() for tag in (document.tags or "").split(",") if tag.strip()]
            content = visible_version.content
            version_number = visible_version.version_number
            published_at = visible_version.published_at

            return PortalDocumentDetail(
                id=document.id,
                document_number=document.document_number,
                title=document.title,
                description=document.description,
                content=content,
                category=document.category,
                topic=document.topic,
                platform=document.platform_name,
                release_branch=document.release_branch,
                tags=tags,
                visibility=document.visibility.value if document.visibility else "internal",
                version=version_number,
                created_at=document.created_at,
                updated_at=document.updated_at,
                published_at=published_at,
                toc_items=toc_items,
                attachments=[
                    PortalAttachment(
                        id=att.id,
                        filename=att.filename,
                        file_size=att.file_size,
                        mime_type=att.mime_type,
                        created_at=att.uploaded_at,
                        download_url=(
                            f"/api/v1/portal/documents/{document.id}/attachments/{att.id}/download"
                        ),
                    )
                    for att in attachments
                ],
            )

        return self._execute_cached(
            projection_name="documents.detail",
            key_parts=(self._tenant_scope(query.current_user), query.document_id),
            loader=load_projection,
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, PortalDocumentDetail),
        )

    def execute_get_attachment(self, query: GetPortalAttachmentQuery) -> dict:
        document = (
            self.db.query(Document)
            .filter(Document.id == query.document_id, Document.deleted_at.is_(None))
            .first()
        )
        if not document:
            raise NotFoundError("Document not found")
        self._ensure_customer_document_access(document, query.current_user)

        # C6: Only serve attachments present at publish time
        from app.services.published_attachment_resolver import is_attachment_in_published_snapshot

        if not is_attachment_in_published_snapshot(self.db, query.document_id, query.attachment_id):
            raise NotFoundError("Attachment not found")

        attachment = (
            self.db.query(Attachment)
            .filter(
                Attachment.id == query.attachment_id,
                Attachment.document_id == query.document_id,
            )
            .first()
        )
        if not attachment:
            raise NotFoundError("Attachment not found")

        return {
            "id": attachment.id,
            "filename": attachment.filename,
            "file_size": attachment.file_size,
            "mime_type": attachment.mime_type,
            "download_url": (
                f"/api/v1/portal/documents/{query.document_id}/attachments/{attachment.id}/download"
            ),
        }

    def execute_categories(self, query: ListPortalCategoriesQuery) -> list[dict]:
        return self._execute_cached(
            projection_name="categories",
            key_parts=(self._tenant_scope(query.current_user),),
            loader=lambda: self._load_categories(query),
            ttl_seconds=60,
            validator=lambda payload: isinstance(payload, list),
        )

    def _load_categories(self, query: ListPortalCategoriesQuery) -> list[dict]:
        docs_query = self._customer_documents_query(query.current_user)
        results = (
            docs_query.with_entities(Document.category, func.count(Document.id).label("count"))
            .filter(Document.category.isnot(None), Document.category != "")
            .group_by(Document.category)
            .all()
        )
        return [{"category": category, "count": count} for category, count in results if category]

    def execute_facets(self, query: ListPortalFacetsQuery) -> PortalFacetsResponse:
        return self._execute_cached(
            projection_name="facets",
            key_parts=(self._tenant_scope(query.current_user),),
            loader=lambda: self._load_facets(query),
            ttl_seconds=60,
            validator=lambda payload: isinstance(payload, PortalFacetsResponse),
        )

    def _load_facets(self, query: ListPortalFacetsQuery) -> PortalFacetsResponse:
        base = self._customer_documents_query(query.current_user)

        categories = (
            base.with_entities(Document.category, func.count(Document.id))
            .filter(Document.category.isnot(None), Document.category != "")
            .group_by(Document.category)
            .order_by(func.count(Document.id).desc())
            .all()
        )
        topics = (
            base.with_entities(Document.topic, func.count(Document.id))
            .filter(Document.topic.isnot(None), Document.topic != "")
            .group_by(Document.topic)
            .order_by(func.count(Document.id).desc())
            .all()
        )
        platforms = (
            base.join(Platform, Document.platform_id == Platform.id)
            .with_entities(Platform.name, func.count(Document.id))
            .filter(Platform.name.isnot(None), Platform.name != "")
            .group_by(Platform.name)
            .order_by(func.count(Document.id).desc())
            .all()
        )

        return PortalFacetsResponse(
            categories=[FacetItem(name=n, count=c) for n, c in categories if n],
            topics=[FacetItem(name=n, count=c) for n, c in topics if n],
            platforms=[FacetItem(name=n, count=c) for n, c in platforms if n],
        )

    def execute_dashboard_stats(self, query: PortalDashboardStatsQuery) -> PortalDashboardStats:
        return self._execute_cached(
            projection_name="dashboard.stats",
            key_parts=(self._tenant_scope(query.current_user), query.current_user.id),
            loader=lambda: self._load_dashboard_stats(query),
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, PortalDashboardStats),
        )

    def _load_dashboard_stats(self, query: PortalDashboardStatsQuery) -> PortalDashboardStats:
        visible_documents_query = self._customer_documents_query(query.current_user)
        visibility_counts = dict(
            visible_documents_query.with_entities(Document.visibility, func.count(Document.id))
            .group_by(Document.visibility)
            .all()
        )

        public_count = visibility_counts.get(DocumentVisibility.PUBLIC, 0)
        company_count = visibility_counts.get(DocumentVisibility.COMPANY, 0)
        total_documents = public_count + company_count

        pending_feedback = (
            self.db.query(Feedback)
            .filter(
                Feedback.user_id == query.current_user.id,
                Feedback.is_helpful.is_(None),
                Feedback.status == FeedbackStatus.PENDING,
            )
            .count()
        )
        responded_feedback = (
            self.db.query(Feedback)
            .filter(
                Feedback.user_id == query.current_user.id,
                Feedback.is_helpful.is_(None),
                Feedback.status == FeedbackStatus.RESPONDED,
            )
            .count()
        )

        return PortalDashboardStats(
            total_documents=total_documents,
            public_documents=public_count,
            company_documents=company_count,
            pending_feedback=pending_feedback,
            responded_feedback=responded_feedback,
        )

    def execute_search_documents(self, query: SearchPortalDocumentsQuery) -> dict:
        return self._execute_cached(
            projection_name="documents.search",
            key_parts=(
                self._tenant_scope(query.current_user),
                query.q,
                query.category,
                query.page,
                query.per_page,
            ),
            loader=lambda: self._load_search_documents(query),
            ttl_seconds=30,
            validator=lambda payload: isinstance(payload, dict)
            and "results" in payload
            and "total" in payload,
        )

    def _load_search_documents(self, query: SearchPortalDocumentsQuery) -> dict:
        docs_query = self._customer_documents_query(query.current_user)
        search_term = f"%{query.q}%"
        docs_query = docs_query.filter(
            or_(
                Document.title.ilike(search_term),
                Document.description.ilike(search_term),
                Document.tags.ilike(search_term),
            )
        )
        if query.category:
            docs_query = docs_query.filter(Document.category == query.category)

        total = docs_query.count()
        pages = (total + query.per_page - 1) // query.per_page
        offset = (query.page - 1) * query.per_page
        documents = (
            docs_query.order_by(Document.updated_at.desc())
            .offset(offset)
            .limit(query.per_page)
            .all()
        )

        results: list[dict] = []
        for doc in documents:
            snippet = ""
            visible_version = self._portal_visible_version(doc)
            content = visible_version.content if visible_version else ""

            if content:
                content_lower = content.lower()
                q_lower = query.q.lower()
                pos = content_lower.find(q_lower)
                if pos >= 0:
                    start = max(0, pos - 50)
                    end = min(len(content), pos + len(query.q) + 100)
                    snippet = content[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(content):
                        snippet = snippet + "..."
                else:
                    snippet = content[:150] + "..." if len(content) > 150 else content

            results.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "description": doc.description,
                    "category": doc.category,
                    "snippet": snippet,
                    "updated_at": doc.updated_at.isoformat(),
                }
            )

        return {
            "query": query.q,
            "results": results,
            "total": total,
            "page": query.page,
            "per_page": query.per_page,
            "pages": pages,
        }

    def execute_related_documents(self, query: RelatedDocumentsQuery) -> list[dict]:
        """Find documents related to the given document by shared attributes."""
        source = self.db.query(Document).filter(Document.id == query.document_id).first()
        if not source:
            return []

        base_query = self._customer_documents_query(query.current_user)
        base_query = base_query.filter(Document.id != query.document_id)

        source_tags = {
            t.strip().lower()
            for t in (source.tags or "").split(",")
            if t.strip()
        }

        # Score candidates by shared attributes
        candidates = base_query.all()
        scored: list[tuple[float, Document]] = []
        for doc in candidates:
            score = 0.0
            if source.category and doc.category == source.category:
                score += 3.0
            if source.topic and doc.topic == source.topic:
                score += 2.0
            if source.platform_name and doc.platform_name == source.platform_name:
                score += 1.5
            if source_tags:
                doc_tags = {
                    t.strip().lower()
                    for t in (doc.tags or "").split(",")
                    if t.strip()
                }
                overlap = len(source_tags & doc_tags)
                score += overlap * 1.0
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: (-x[0], x[1].updated_at or x[1].created_at), reverse=False)
        top = scored[: query.limit]

        return [
            {
                "id": doc.id,
                "title": doc.title,
                "description": doc.description,
                "category": doc.category,
                "thumbnail_url": doc.thumbnail_url,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
            for _score, doc in top
        ]
