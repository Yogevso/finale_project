"""Tests for search/portal read-model query handlers."""

from datetime import datetime
from uuid import uuid4

from app.application.queries.portal_queries import (
    ListPortalDocumentsQuery,
    PortalDashboardStatsQuery,
    PortalDocumentsQueryHandler,
)
from app.application.queries.search_queries import (
    SearchDocumentsQuery,
    SearchQueryHandler,
)
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Feedback,
    FeedbackStatus,
    FeedbackType,
    Tenant,
    Version,
)


def test_search_query_handler_applies_tenant_scope(db, test_user):
    tenant_a = Tenant(
        name="Search Scope A",
        slug=f"search-scope-a-{uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    tenant_b = Tenant(
        name="Search Scope B",
        slug=f"search-scope-b-{uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    db.add_all([tenant_a, tenant_b])
    db.commit()
    db.refresh(tenant_a)
    db.refresh(tenant_b)

    test_user.tenant_id = tenant_a.id
    db.commit()

    visible_doc = Document(
        title="Scoped Search Visible",
        document_number=f"DOC-SSV-{uuid4().hex[:6].upper()}",
        description="handler-scope-keyword",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=tenant_a.id,
    )
    hidden_doc = Document(
        title="Scoped Search Hidden",
        document_number=f"DOC-SSH-{uuid4().hex[:6].upper()}",
        description="handler-scope-keyword",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=tenant_b.id,
    )
    db.add_all([visible_doc, hidden_doc])
    db.commit()

    handler = SearchQueryHandler(db)
    result = handler.execute_search_documents(
        SearchDocumentsQuery(
            q="handler-scope-keyword",
            category=None,
            date_from=None,
            date_to=None,
            page=1,
            page_size=20,
            current_user=test_user,
        )
    )

    titles = [item.title for item in result.items]
    assert "Scoped Search Visible" in titles
    assert "Scoped Search Hidden" not in titles


def test_portal_query_handler_prefers_published_version_in_list(db, test_admin, test_customer):
    document = Document(
        title="Portal Handler Version Pick",
        document_number=f"DOC-PH-{uuid4().hex[:8].upper()}",
        description="portal query handler version check",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    db.add_all(
        [
            Version(
                document_id=document.id,
                version_number=1,
                content="published",
                changes_summary="published",
                is_published=True,
                created_by=test_admin.id,
            ),
            Version(
                document_id=document.id,
                version_number=2,
                content="draft",
                changes_summary="draft",
                is_published=False,
                created_by=test_admin.id,
            ),
        ]
    )
    db.commit()

    handler = PortalDocumentsQueryHandler(db)
    payload = handler.execute_list_documents(
        ListPortalDocumentsQuery(
            page=1,
            per_page=50,
            category=None,
            search=None,
            current_user=test_customer,
        )
    )

    item = next(row for row in payload.items if row.id == document.id)
    assert item.version == 1


def test_portal_query_handler_dashboard_counts_visible_docs(db, test_admin, test_customer, test_tenant_2):
    public_doc = Document(
        title="Portal Handler Public",
        document_number=f"DOC-PHP-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    company_doc = Document(
        title="Portal Handler Company",
        document_number=f"DOC-PHC-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    hidden_company_doc = Document(
        title="Portal Handler Hidden",
        document_number=f"DOC-PHH-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add_all([public_doc, company_doc, hidden_company_doc])
    db.flush()

    company_doc.assigned_companies.append(test_customer.tenant)
    hidden_company_doc.assigned_companies.append(test_tenant_2)

    for doc in [public_doc, company_doc, hidden_company_doc]:
        db.add(Version(
            document_id=doc.id,
            version_number=1,
            content="Published",
            is_published=True,
            published_at=datetime.utcnow(),
            created_by=test_admin.id,
        ))
    db.commit()

    db.add_all(
        [
            Feedback(
                user_id=test_customer.id,
                document_id=public_doc.id,
                feedback_type=FeedbackType.QUESTION,
                status=FeedbackStatus.PENDING,
                content="pending feedback",
                created_at=datetime.utcnow(),
            ),
            Feedback(
                user_id=test_customer.id,
                document_id=public_doc.id,
                feedback_type=FeedbackType.QUESTION,
                status=FeedbackStatus.RESPONDED,
                content="responded feedback",
                created_at=datetime.utcnow(),
            ),
        ]
    )
    db.commit()

    handler = PortalDocumentsQueryHandler(db)
    stats = handler.execute_dashboard_stats(PortalDashboardStatsQuery(current_user=test_customer))

    assert stats.total_documents == 2
    assert stats.public_documents == 1
    assert stats.company_documents == 1
    assert stats.pending_feedback == 1
    assert stats.responded_feedback == 1
