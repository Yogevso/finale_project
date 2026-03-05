"""Tests for audience-specific test data factories."""

from app.models import DocumentVisibility
from tests.factories import create_audience_edge_case_set


def test_audience_edge_case_factory_creates_expected_visibility_matrix(
    db, test_admin, test_tenant, test_tenant_2
):
    edge_cases = create_audience_edge_case_set(
        db,
        created_by=test_admin.id,
        primary_company=test_tenant,
        secondary_company=test_tenant_2,
    )

    assert edge_cases.internal_document.visibility == DocumentVisibility.INTERNAL
    assert edge_cases.public_document.visibility == DocumentVisibility.PUBLIC
    assert edge_cases.company_single_assignment.visibility == DocumentVisibility.COMPANY
    assert edge_cases.company_multi_assignment.visibility == DocumentVisibility.COMPANY

    single_ids = sorted(company.id for company in edge_cases.company_single_assignment.assigned_companies)
    multi_ids = sorted(company.id for company in edge_cases.company_multi_assignment.assigned_companies)
    assert single_ids == [test_tenant.id]
    assert multi_ids == sorted([test_tenant.id, test_tenant_2.id])
