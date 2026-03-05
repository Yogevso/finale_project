"""Wave U fuzz tests for audience-assignment API inputs."""

from __future__ import annotations

import pytest

try:
    from hypothesis import HealthCheck, given
    from hypothesis import settings as hypothesis_settings
    from hypothesis import strategies as st
except ModuleNotFoundError:  # pragma: no cover - optional local dev dependency
    pytest.skip("hypothesis is not installed", allow_module_level=True)

from app.models import Document, DocumentStatus, DocumentVisibility


@pytest.fixture
def company_scope_document(db, test_admin, test_tenant):
    document = Document(
        title="Wave U Fuzz Document",
        document_number="DOC-WAVE-U-FUZZ-0001",
        status=DocumentStatus.DRAFT,
        visibility=DocumentVisibility.COMPANY,
        created_by=test_admin.id,
    )
    document.assigned_companies = [test_tenant]
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


_company_id_fuzz_values = st.one_of(
    st.integers(min_value=-20, max_value=1000),
    st.text(min_size=0, max_size=8),
    st.none(),
    st.booleans(),
)


@hypothesis_settings(
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(company_ids=st.lists(_company_id_fuzz_values, max_size=8))
def test_companies_bulk_assignment_fuzz_inputs_never_return_500(
    client,
    db,
    admin_headers,
    company_scope_document,
    company_ids,
):
    db.refresh(company_scope_document)
    response = client.put(
        f"/api/v1/documents/{company_scope_document.id}/companies/batch",
        headers={**admin_headers, "If-Match": company_scope_document.etag},
        json={"company_ids": company_ids},
    )

    assert response.status_code in {200, 400, 403, 404, 409, 422, 428}

