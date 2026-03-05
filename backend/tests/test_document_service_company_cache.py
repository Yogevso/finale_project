"""Tests for document-service company lookup caching."""

from app.services.document_service import DocumentService, _CompanyLookupLRU
from tests.factories import create_tenant


def test_company_lookup_cache_hits_and_ttl_expiry(db, monkeypatch):
    tenant = create_tenant(
        db,
        name="Cache Target Tenant",
        slug="cache-target-tenant",
        company_type="customer",
    )

    ticks = {"value": 1000.0}

    def fake_monotonic() -> float:
        return ticks["value"]

    monkeypatch.setattr("app.services.document_service.monotonic", fake_monotonic)

    service = DocumentService(db)
    service._company_lookup_cache = _CompanyLookupLRU(max_entries=32, ttl_seconds=1)

    query_calls = {"count": 0}
    original_query = db.query

    def counting_query(*args, **kwargs):
        if len(args) == 4:
            query_calls["count"] += 1
        return original_query(*args, **kwargs)

    monkeypatch.setattr(db, "query", counting_query)

    first = service._lookup_company_snapshots([tenant.id])
    second = service._lookup_company_snapshots([tenant.id])
    ticks["value"] += 2.0
    third = service._lookup_company_snapshots([tenant.id])

    assert first[tenant.id].name == tenant.name
    assert second[tenant.id].slug == tenant.slug
    assert third[tenant.id].id == tenant.id
    assert query_calls["count"] == 2
