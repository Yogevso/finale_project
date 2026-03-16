"""Tests for reusable query/access specification objects."""

from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.specifications import DateRangeSpec, RoleAccessSpec, TenantScopeSpec, VisibilitySpec
from app.models import Document, DocumentStatus, DocumentVisibility, Tenant, UserRole
from app.repositories import DocumentRepository


def test_tenant_scope_spec_applies_non_system_admin_filter(db, test_user):
    tenant_one = Tenant(
        name=f"Scope Tenant One {uuid4().hex[:6]}",
        slug=f"scope-tenant-one-{uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    tenant_two = Tenant(
        name=f"Scope Tenant Two {uuid4().hex[:6]}",
        slug=f"scope-tenant-two-{uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    db.add_all([tenant_one, tenant_two])
    db.commit()
    db.refresh(tenant_one)
    db.refresh(tenant_two)

    test_user.tenant_id = tenant_one.id
    db.commit()

    visible_doc = Document(
        title="Tenant Scope Visible",
        document_number=f"DOC-TSV-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=tenant_one.id,
    )
    hidden_doc = Document(
        title="Tenant Scope Hidden",
        document_number=f"DOC-TSH-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        tenant_id=tenant_two.id,
    )
    db.add_all([visible_doc, hidden_doc])
    db.commit()

    scoped_docs = TenantScopeSpec.for_user(test_user).apply(db.query(Document), Document).all()
    titles = {doc.title for doc in scoped_docs}
    assert "Tenant Scope Visible" in titles
    assert "Tenant Scope Hidden" not in titles


def test_tenant_scope_spec_sql_clause_variants(test_user, test_system_admin):
    tenant_clause, tenant_params = TenantScopeSpec.for_user(test_user).sql_clause(column_expr="d.tenant_id")
    assert tenant_clause == "d.tenant_id IS NULL"
    assert tenant_params == {}

    test_user.tenant_id = 42
    tenant_clause, tenant_params = TenantScopeSpec.for_user(test_user).sql_clause(column_expr="d.tenant_id")
    assert tenant_clause == "d.tenant_id = :tenant_id"
    assert tenant_params == {"tenant_id": 42}

    admin_clause, admin_params = TenantScopeSpec.for_user(test_system_admin).sql_clause(
        column_expr="d.tenant_id"
    )
    assert admin_clause is None
    assert admin_params == {}


def test_date_range_spec_filters_orm_and_sql_clauses(db, test_user):
    old_doc = Document(
        title="Date Spec Old",
        document_number=f"DOC-DAT-OLD-{uuid4().hex[:6].upper()}",
        description="date range test",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        created_at=datetime.utcnow() - timedelta(days=5),
    )
    fresh_doc = Document(
        title="Date Spec Fresh",
        document_number=f"DOC-DAT-NEW-{uuid4().hex[:6].upper()}",
        description="date range test",
        status=DocumentStatus.ACTIVE,
        created_by=test_user.id,
        created_at=datetime.utcnow(),
    )
    db.add_all([old_doc, fresh_doc])
    db.commit()

    date_spec = DateRangeSpec(date_from=datetime.utcnow() - timedelta(days=1))
    filtered_docs = date_spec.apply(db.query(Document), Document.created_at).all()
    titles = {doc.title for doc in filtered_docs}
    assert "Date Spec Fresh" in titles
    assert "Date Spec Old" not in titles

    clauses, params = date_spec.sql_clauses(column_expr="d.created_at")
    assert clauses == ["d.created_at >= :date_from"]
    assert "date_from" in params


def test_role_access_spec_customer_only(test_customer, test_user):
    spec = RoleAccessSpec.customer_only()
    assert spec.is_satisfied_by(test_customer)
    assert not spec.is_satisfied_by(test_user)

    inactive_customer = test_customer
    inactive_customer.is_active = False
    assert not spec.is_satisfied_by(inactive_customer)


def test_visibility_spec_customer_portal_query_and_runtime(
    db,
    test_customer,
    test_customer_2,
    public_document,
    company_document,
    internal_document,
):
    spec = VisibilitySpec.customer_portal(test_customer.tenant_id)
    assert spec.is_satisfied_by(public_document)
    assert spec.is_satisfied_by(company_document)
    assert not spec.is_satisfied_by(internal_document)

    other_customer_spec = VisibilitySpec.customer_portal(test_customer_2.tenant_id)
    assert other_customer_spec.is_satisfied_by(public_document)
    assert not other_customer_spec.is_satisfied_by(company_document)

    visible_docs = spec.apply(db.query(Document), Document).all()
    titles = {doc.title for doc in visible_docs}
    assert "Public Document" in titles
    assert "Company Document" in titles
    assert "Internal Document" not in titles


def test_document_repository_spec_composition(
    db, test_customer, test_user, public_document, company_document, internal_document
):
    tenant_a = Tenant(
        name=f"Repo Tenant A {uuid4().hex[:6]}",
        slug=f"repo-tenant-a-{uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    tenant_b = Tenant(
        name=f"Repo Tenant B {uuid4().hex[:6]}",
        slug=f"repo-tenant-b-{uuid4().hex[:6]}",
        is_active=True,
        company_type="customer",
    )
    db.add_all([tenant_a, tenant_b])
    db.commit()
    db.refresh(tenant_a)
    db.refresh(tenant_b)

    scoped_doc = Document(
        title="Repository Scoped Doc",
        document_number=f"DOC-RSD-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_user.id,
        tenant_id=tenant_a.id,
    )
    other_doc = Document(
        title="Repository Other Tenant Doc",
        document_number=f"DOC-ROD-{uuid4().hex[:6].upper()}",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        created_by=test_user.id,
        tenant_id=tenant_b.id,
    )
    db.add_all([scoped_doc, other_doc])
    db.commit()

    test_user.role = UserRole.EDITOR
    test_user.tenant_id = tenant_a.id
    db.commit()

    repository = DocumentRepository(db)

    scoped_titles = {doc.title for doc in repository.scoped_query_for_user(test_user).all()}
    assert "Repository Scoped Doc" in scoped_titles
    assert "Repository Other Tenant Doc" not in scoped_titles

    portal_titles = {
        doc.title for doc in repository.portal_visible_query_for_customer(test_customer).all()
    }
    assert "Public Document" in portal_titles
    assert "Company Document" in portal_titles
    assert "Internal Document" not in portal_titles
