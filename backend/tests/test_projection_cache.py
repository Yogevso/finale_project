"""Projection/cache behavior tests for heavy read paths."""

from datetime import datetime
from uuid import uuid4

from app.application.queries.portal_queries import (
    ListPortalDocumentsQuery,
    PortalDocumentsQueryHandler,
)
from app.application.queries.search_queries import (
    SearchDocumentsQuery,
    SearchFacetsQuery,
    SearchQueryHandler,
)
from app.models import Document, DocumentStatus, DocumentVisibility, Tenant, Version
from app.projections import ProjectionCacheError, get_projection_cache


def test_search_projection_cache_hit_skips_recompute(db, test_user, monkeypatch):
    tenant = Tenant(
        name="Projection Search Tenant",
        slug=f"projection-search-{uuid4().hex[:8]}",
        is_active=True,
        company_type="customer",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    test_user.tenant_id = tenant.id
    db.commit()

    doc = Document(
        title="Projection Cache Search Document",
        document_number=f"DOC-PCS-{uuid4().hex[:6].upper()}",
        description="projection-cache-keyword",
        category="Guides",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=tenant.id,
    )
    db.add(doc)
    db.commit()

    handler = SearchQueryHandler(db)
    request = SearchDocumentsQuery(
        q="projection-cache-keyword",
        category=None,
        date_from=None,
        date_to=None,
        page=1,
        page_size=20,
        current_user=test_user,
    )
    first = handler.execute_search_documents(request)
    assert first.total >= 1

    def _unexpected_recompute(_row):
        raise AssertionError("search projection should come from cache on repeated request")

    monkeypatch.setattr(
        SearchQueryHandler,
        "_build_read_model",
        staticmethod(_unexpected_recompute),
    )

    second = handler.execute_search_documents(request)
    assert second.total == first.total
    assert [item.title for item in second.items] == [item.title for item in first.items]


def test_portal_projection_invalidates_after_document_write(db, test_admin, test_customer):
    document = Document(
        title="Projection Old Title",
        document_number=f"DOC-PCI-{uuid4().hex[:6].upper()}",
        description="projection invalidation",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        created_by=test_admin.id,
        tenant_id=test_admin.tenant_id,
    )
    db.add(document)
    db.flush()

    version = Version(
        document_id=document.id,
        version_number=1,
        content="Published content",
        is_published=True,
        published_at=datetime.utcnow(),
        created_by=test_admin.id,
    )
    db.add(version)
    db.commit()
    db.refresh(document)

    handler = PortalDocumentsQueryHandler(db)
    request = ListPortalDocumentsQuery(
        page=1,
        per_page=100,
        category=None,
        search="projection invalidation",
        current_user=test_customer,
    )

    before = handler.execute_list_documents(request)
    old_item = next(item for item in before.items if item.id == document.id)
    assert old_item.title == "Projection Old Title"

    document.title = "Projection Updated Title"
    document.updated_at = datetime.utcnow()
    db.commit()

    after = handler.execute_list_documents(request)
    updated_item = next(item for item in after.items if item.id == document.id)
    assert updated_item.title == "Projection Updated Title"


def test_search_projection_cache_falls_back_when_cache_path_fails(db, test_user, monkeypatch):
    tenant = Tenant(
        name="Projection Facets Tenant",
        slug=f"projection-facets-{uuid4().hex[:8]}",
        is_active=True,
        company_type="customer",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    test_user.tenant_id = tenant.id
    db.commit()

    db.add(
        Document(
            title="Projection Facet Doc",
            document_number=f"DOC-PCF-{uuid4().hex[:6].upper()}",
            description="facet projection",
            category="How-To",
            status=DocumentStatus.ACTIVE,
            created_by=test_user.id,
            tenant_id=tenant.id,
        )
    )
    db.commit()

    handler = SearchQueryHandler(db)
    cache = get_projection_cache()

    def _raise_projection_cache_error(**_kwargs):
        raise ProjectionCacheError("simulated cache path failure")

    monkeypatch.setattr(cache, "get_or_load", _raise_projection_cache_error)
    payload = handler.execute_facets(SearchFacetsQuery(current_user=test_user))

    assert "categories" in payload
    assert "statuses" in payload
