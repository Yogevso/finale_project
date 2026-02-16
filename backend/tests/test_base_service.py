"""Tests for TenantAwareService base class - multi-tenant isolation logic"""

import pytest
from sqlalchemy.orm import Session

from app.dependencies.tenant import TenantContext
from app.models import (
    Document,
    DocumentStatus,
    DocumentVisibility,
    Tenant,
    User,
    UserRole,
)
from app.security import get_password_hash
from app.services.base_service import TenantAwareService

# ============================================================================
# Test Service Classes
# ============================================================================


class UserService(TenantAwareService[User]):
    """Test service for User model"""

    model = User


class DocumentService(TenantAwareService[Document]):
    """Test service for Document model"""

    model = Document


class TenantService(TenantAwareService[Tenant]):
    """Test service for Tenant model (no tenant_id column)"""

    model = Tenant


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tenant1(db: Session) -> Tenant:
    """Create first test tenant"""
    tenant = Tenant(
        name="Tenant One",
        slug="tenant-one",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def tenant2(db: Session) -> Tenant:
    """Create second test tenant"""
    tenant = Tenant(
        name="Tenant Two",
        slug="tenant-two",
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def user_tenant1(db: Session, tenant1: Tenant) -> User:
    """Create user belonging to tenant1"""
    user = User(
        email="user1@tenant1.com",
        username="user_t1",
        full_name="User Tenant One",
        hashed_password=get_password_hash("password123"),
        role=UserRole.EDITOR,
        is_active=True,
        tenant_id=tenant1.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_tenant2(db: Session, tenant2: Tenant) -> User:
    """Create user belonging to tenant2"""
    user = User(
        email="user2@tenant2.com",
        username="user_t2",
        full_name="User Tenant Two",
        hashed_password=get_password_hash("password123"),
        role=UserRole.EDITOR,
        is_active=True,
        tenant_id=tenant2.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_no_tenant(db: Session) -> User:
    """Create user with no tenant (legacy/unassigned)"""
    user = User(
        email="legacy@example.com",
        username="legacy_user",
        full_name="Legacy User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.VIEWER,
        is_active=True,
        tenant_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def system_admin(db: Session) -> User:
    """Create system admin user"""
    user = User(
        email="sysadmin@example.com",
        username="sysadmin",
        full_name="System Admin",
        hashed_password=get_password_hash("password123"),
        role=UserRole.SYSTEM_ADMIN,
        is_active=True,
        tenant_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def doc_tenant1(db: Session, tenant1: Tenant, user_tenant1: User) -> Document:
    """Create document belonging to tenant1"""
    doc = Document(
        title="Tenant 1 Document",
        document_number="DOC-T1-001",
        description="Document for tenant 1",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        tenant_id=tenant1.id,
        created_by=user_tenant1.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def doc_tenant2(db: Session, tenant2: Tenant, user_tenant2: User) -> Document:
    """Create document belonging to tenant2"""
    doc = Document(
        title="Tenant 2 Document",
        document_number="DOC-T2-001",
        description="Document for tenant 2",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.INTERNAL,
        tenant_id=tenant2.id,
        created_by=user_tenant2.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def doc_no_tenant(db: Session, user_no_tenant: User) -> Document:
    """Create document with no tenant (legacy)"""
    doc = Document(
        title="Legacy Document",
        document_number="DOC-LEGACY-001",
        description="Legacy document without tenant",
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.PUBLIC,
        tenant_id=None,
        created_by=user_no_tenant.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def tenant1_context(tenant1: Tenant, user_tenant1: User) -> TenantContext:
    """Create tenant context for tenant1 user"""
    return TenantContext(
        tenant_id=tenant1.id,
        user_id=user_tenant1.id,
        user_role=UserRole.EDITOR,
        is_system_admin=False,
    )


@pytest.fixture
def tenant2_context(tenant2: Tenant, user_tenant2: User) -> TenantContext:
    """Create tenant context for tenant2 user"""
    return TenantContext(
        tenant_id=tenant2.id,
        user_id=user_tenant2.id,
        user_role=UserRole.EDITOR,
        is_system_admin=False,
    )


@pytest.fixture
def system_admin_context(system_admin: User) -> TenantContext:
    """Create tenant context for system admin"""
    return TenantContext(
        tenant_id=None,
        user_id=system_admin.id,
        user_role=UserRole.SYSTEM_ADMIN,
        is_system_admin=True,
    )


# ============================================================================
# Test: Service Initialization
# ============================================================================


class TestServiceInitialization:
    """Tests for TenantAwareService initialization"""

    def test_init_with_db_only(self, db: Session):
        """Service can be initialized with just db session"""
        service = UserService(db)
        assert service.db is db
        assert service.tenant_ctx is None

    def test_init_with_tenant_context(self, db: Session, tenant1_context: TenantContext):
        """Service can be initialized with tenant context"""
        service = UserService(db, tenant1_context)
        assert service.db is db
        assert service.tenant_ctx is tenant1_context

    def test_model_attribute_set(self, db: Session):
        """Service class has model attribute set"""
        service = UserService(db)
        assert service.model is User

        doc_service = DocumentService(db)
        assert doc_service.model is Document


# ============================================================================
# Test: _base_query - Tenant Filtering
# ============================================================================


class TestBaseQuery:
    """Tests for _base_query method - core tenant filtering logic"""

    def test_no_tenant_context_returns_all(
        self, db: Session, user_tenant1: User, user_tenant2: User, user_no_tenant: User
    ):
        """Without tenant context, query returns all records"""
        service = UserService(db)
        query = service._base_query()
        results = query.all()

        # Should see all users
        user_ids = [u.id for u in results]
        assert user_tenant1.id in user_ids
        assert user_tenant2.id in user_ids
        assert user_no_tenant.id in user_ids

    def test_tenant_context_filters_by_tenant(
        self,
        db: Session,
        tenant1_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
    ):
        """With tenant context, query filters by tenant_id"""
        service = UserService(db, tenant1_context)
        query = service._base_query()
        results = query.all()

        # Should only see tenant1 users
        user_ids = [u.id for u in results]
        assert user_tenant1.id in user_ids
        assert user_tenant2.id not in user_ids

    def test_system_admin_sees_all(
        self,
        db: Session,
        system_admin_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
        user_no_tenant: User,
    ):
        """System admin bypasses tenant filtering"""
        service = UserService(db, system_admin_context)
        query = service._base_query()
        results = query.all()

        # System admin should see all users
        user_ids = [u.id for u in results]
        assert user_tenant1.id in user_ids
        assert user_tenant2.id in user_ids
        assert user_no_tenant.id in user_ids

    def test_model_without_tenant_id_not_filtered(
        self, db: Session, tenant1_context: TenantContext, tenant1: Tenant, tenant2: Tenant
    ):
        """Models without tenant_id column are not filtered"""
        service = TenantService(db, tenant1_context)
        query = service._base_query()
        results = query.all()

        # Should see all tenants (Tenant model has no tenant_id)
        tenant_ids = [t.id for t in results]
        assert tenant1.id in tenant_ids
        assert tenant2.id in tenant_ids

    def test_custom_model_parameter(
        self,
        db: Session,
        tenant1_context: TenantContext,
        doc_tenant1: Document,
        doc_tenant2: Document,
    ):
        """Can pass custom model to _base_query"""
        # Using UserService but querying Documents
        service = UserService(db, tenant1_context)
        query = service._base_query(model=Document)
        results = query.all()

        # Should filter by tenant for Document model
        doc_ids = [d.id for d in results]
        assert doc_tenant1.id in doc_ids
        assert doc_tenant2.id not in doc_ids

    def test_null_tenant_id_not_returned_for_tenant_user(
        self,
        db: Session,
        tenant1_context: TenantContext,
        user_tenant1: User,
        user_no_tenant: User,
    ):
        """Users with null tenant_id are not returned for tenant-scoped queries"""
        service = UserService(db, tenant1_context)
        query = service._base_query()
        results = query.all()

        # Null tenant_id users should NOT be returned
        user_ids = [u.id for u in results]
        assert user_tenant1.id in user_ids
        assert user_no_tenant.id not in user_ids


# ============================================================================
# Test: get_by_id
# ============================================================================


class TestGetById:
    """Tests for get_by_id method"""

    def test_get_own_tenant_record(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User
    ):
        """Can get record from own tenant"""
        service = UserService(db, tenant1_context)
        result = service.get_by_id(user_tenant1.id)
        assert result is not None
        assert result.id == user_tenant1.id

    def test_cannot_get_other_tenant_record(
        self, db: Session, tenant1_context: TenantContext, user_tenant2: User
    ):
        """Cannot get record from other tenant"""
        service = UserService(db, tenant1_context)
        result = service.get_by_id(user_tenant2.id)
        assert result is None

    def test_system_admin_can_get_any_record(
        self,
        db: Session,
        system_admin_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
    ):
        """System admin can get record from any tenant"""
        service = UserService(db, system_admin_context)

        result1 = service.get_by_id(user_tenant1.id)
        assert result1 is not None
        assert result1.id == user_tenant1.id

        result2 = service.get_by_id(user_tenant2.id)
        assert result2 is not None
        assert result2.id == user_tenant2.id

    def test_get_nonexistent_record(self, db: Session, tenant1_context: TenantContext):
        """Getting nonexistent record returns None"""
        service = UserService(db, tenant1_context)
        result = service.get_by_id(99999)
        assert result is None

    def test_get_by_id_with_custom_model(
        self, db: Session, tenant1_context: TenantContext, doc_tenant1: Document
    ):
        """Can get by id with custom model parameter"""
        service = UserService(db, tenant1_context)
        result = service.get_by_id(doc_tenant1.id, model=Document)
        assert result is not None
        assert result.id == doc_tenant1.id

    def test_no_context_gets_any_record(self, db: Session, user_tenant1: User, user_tenant2: User):
        """Without context, can get any record"""
        service = UserService(db)

        result1 = service.get_by_id(user_tenant1.id)
        assert result1 is not None

        result2 = service.get_by_id(user_tenant2.id)
        assert result2 is not None


# ============================================================================
# Test: get_all
# ============================================================================


class TestGetAll:
    """Tests for get_all method"""

    def test_get_all_own_tenant(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User, user_tenant2: User
    ):
        """get_all returns only own tenant records"""
        service = UserService(db, tenant1_context)
        results = service.get_all()

        user_ids = [u.id for u in results]
        assert user_tenant1.id in user_ids
        assert user_tenant2.id not in user_ids

    def test_get_all_with_pagination(
        self, db: Session, tenant1: Tenant, tenant1_context: TenantContext
    ):
        """get_all respects skip and limit parameters"""
        # Create multiple users in tenant1
        for i in range(5):
            user = User(
                email=f"page_test_{i}@tenant1.com",
                username=f"page_user_{i}",
                full_name=f"Page User {i}",
                hashed_password=get_password_hash("password"),
                role=UserRole.VIEWER,
                is_active=True,
                tenant_id=tenant1.id,
            )
            db.add(user)
        db.commit()

        service = UserService(db, tenant1_context)

        # Test limit
        results = service.get_all(limit=2)
        assert len(results) == 2

        # Test skip
        results_skip = service.get_all(skip=2, limit=2)
        assert len(results_skip) == 2

        # Results should be different
        ids_first = {u.id for u in results}
        ids_second = {u.id for u in results_skip}
        assert ids_first.isdisjoint(ids_second)

    def test_get_all_system_admin(
        self,
        db: Session,
        system_admin_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
    ):
        """System admin get_all returns all records"""
        service = UserService(db, system_admin_context)
        results = service.get_all()

        user_ids = [u.id for u in results]
        assert user_tenant1.id in user_ids
        assert user_tenant2.id in user_ids

    def test_get_all_empty_result(self, db: Session, tenant1_context: TenantContext):
        """get_all returns empty list when no matching records"""
        # Delete all users in tenant1 first
        db.query(User).filter(User.tenant_id == tenant1_context.tenant_id).delete()
        db.commit()

        service = DocumentService(db, tenant1_context)
        results = service.get_all()
        assert results == []

    def test_get_all_with_custom_model(
        self,
        db: Session,
        tenant1_context: TenantContext,
        doc_tenant1: Document,
        doc_tenant2: Document,
    ):
        """get_all with custom model parameter"""
        service = UserService(db, tenant1_context)
        results = service.get_all(model=Document)

        doc_ids = [d.id for d in results]
        assert doc_tenant1.id in doc_ids
        assert doc_tenant2.id not in doc_ids


# ============================================================================
# Test: count
# ============================================================================


class TestCount:
    """Tests for count method"""

    def test_count_own_tenant(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User, user_tenant2: User
    ):
        """count returns only own tenant record count"""
        service = UserService(db, tenant1_context)
        count = service.count()

        # Should count only tenant1 users
        assert count >= 1  # At least user_tenant1

    def test_count_system_admin(
        self,
        db: Session,
        system_admin_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
        system_admin: User,
    ):
        """System admin count includes all tenants"""
        service = UserService(db, system_admin_context)
        count = service.count()

        # Should count all users
        assert count >= 3  # At least user_tenant1, user_tenant2, system_admin

    def test_count_empty(self, db: Session, tenant1_context: TenantContext):
        """count returns 0 when no matching records"""
        service = DocumentService(db, tenant1_context)
        count = service.count()
        assert count == 0

    def test_count_with_custom_model(
        self,
        db: Session,
        tenant1_context: TenantContext,
        doc_tenant1: Document,
        doc_tenant2: Document,
    ):
        """count with custom model parameter"""
        service = UserService(db, tenant1_context)
        count = service.count(model=Document)
        assert count == 1  # Only doc_tenant1


# ============================================================================
# Test: create
# ============================================================================


class TestCreate:
    """Tests for create method"""

    def test_create_auto_assigns_tenant_id(
        self, db: Session, tenant1_context: TenantContext, tenant1: Tenant
    ):
        """create auto-assigns tenant_id from context"""
        service = UserService(db, tenant1_context)

        new_user = User(
            email="new_user@example.com",
            username="new_user",
            full_name="New User",
            hashed_password=get_password_hash("password"),
            role=UserRole.VIEWER,
            is_active=True,
            tenant_id=None,  # Not set
        )

        created = service.create(new_user)

        assert created.id is not None
        assert created.tenant_id == tenant1.id

    def test_create_preserves_explicit_tenant_id(
        self, db: Session, tenant1_context: TenantContext, tenant2: Tenant
    ):
        """create preserves explicitly set tenant_id"""
        service = UserService(db, tenant1_context)

        new_user = User(
            email="explicit_tenant@example.com",
            username="explicit_tenant",
            full_name="Explicit Tenant User",
            hashed_password=get_password_hash("password"),
            role=UserRole.VIEWER,
            is_active=True,
            tenant_id=tenant2.id,  # Explicitly set to different tenant
        )

        created = service.create(new_user)

        assert created.id is not None
        assert created.tenant_id == tenant2.id  # Should preserve explicit value

    def test_create_without_context(self, db: Session, tenant1: Tenant):
        """create without context does not auto-assign tenant"""
        service = UserService(db)  # No tenant context

        new_user = User(
            email="no_context@example.com",
            username="no_context",
            full_name="No Context User",
            hashed_password=get_password_hash("password"),
            role=UserRole.VIEWER,
            is_active=True,
            tenant_id=None,
        )

        created = service.create(new_user)

        assert created.id is not None
        assert created.tenant_id is None  # Should remain null

    def test_create_model_without_tenant_id(self, db: Session, tenant1_context: TenantContext):
        """create works for models without tenant_id attribute"""
        service = TenantService(db, tenant1_context)

        new_tenant = Tenant(
            name="New Tenant",
            slug="new-tenant",
            is_active=True,
        )

        created = service.create(new_tenant)

        assert created.id is not None
        assert created.name == "New Tenant"

    def test_create_persists_to_db(self, db: Session, tenant1_context: TenantContext):
        """created record is persisted and can be retrieved"""
        service = UserService(db, tenant1_context)

        new_user = User(
            email="persist_test@example.com",
            username="persist_test",
            full_name="Persist Test",
            hashed_password=get_password_hash("password"),
            role=UserRole.VIEWER,
            is_active=True,
        )

        created = service.create(new_user)
        user_id = created.id

        # Verify can retrieve
        retrieved = service.get_by_id(user_id)
        assert retrieved is not None
        assert retrieved.email == "persist_test@example.com"


# ============================================================================
# Test: update
# ============================================================================


class TestUpdate:
    """Tests for update method"""

    def test_update_persists_changes(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User
    ):
        """update persists changes to database"""
        service = UserService(db, tenant1_context)

        user_tenant1.full_name = "Updated Name"
        updated = service.update(user_tenant1)

        assert updated.full_name == "Updated Name"

        # Verify persisted
        retrieved = service.get_by_id(user_tenant1.id)
        assert retrieved.full_name == "Updated Name"

    def test_update_refreshes_object(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User
    ):
        """update refreshes object from database"""
        service = UserService(db, tenant1_context)

        user_tenant1.full_name = "Refresh Test"

        updated = service.update(user_tenant1)

        # updated_at should be updated (assuming model has onupdate)
        assert updated.full_name == "Refresh Test"


# ============================================================================
# Test: delete
# ============================================================================


class TestDelete:
    """Tests for delete method"""

    def test_delete_removes_record(self, db: Session, tenant1: Tenant):
        """delete removes record from database"""
        # Create a user to delete
        user = User(
            email="to_delete@example.com",
            username="to_delete",
            full_name="To Delete",
            hashed_password=get_password_hash("password"),
            role=UserRole.VIEWER,
            is_active=True,
            tenant_id=tenant1.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        service = UserService(db)
        service.delete(user)

        # Verify deleted
        result = db.query(User).filter(User.id == user_id).first()
        assert result is None

    def test_delete_with_tenant_context(
        self, db: Session, tenant1_context: TenantContext, tenant1: Tenant
    ):
        """delete works with tenant context"""
        user = User(
            email="ctx_delete@example.com",
            username="ctx_delete",
            full_name="Context Delete",
            hashed_password=get_password_hash("password"),
            role=UserRole.VIEWER,
            is_active=True,
            tenant_id=tenant1.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        service = UserService(db, tenant1_context)
        service.delete(user)

        result = db.query(User).filter(User.id == user_id).first()
        assert result is None


# ============================================================================
# Test: verify_tenant_access
# ============================================================================


class TestVerifyTenantAccess:
    """Tests for verify_tenant_access method"""

    def test_no_context_returns_true(self, db: Session, user_tenant1: User):
        """Without tenant context, access is always granted"""
        service = UserService(db)  # No context
        assert service.verify_tenant_access(user_tenant1) is True

    def test_system_admin_returns_true(
        self, db: Session, system_admin_context: TenantContext, user_tenant1: User
    ):
        """System admin has access to all objects"""
        service = UserService(db, system_admin_context)
        assert service.verify_tenant_access(user_tenant1) is True

    def test_model_without_tenant_id_returns_true(
        self, db: Session, tenant1_context: TenantContext, tenant1: Tenant
    ):
        """Objects without tenant_id attribute are accessible"""
        service = TenantService(db, tenant1_context)
        assert service.verify_tenant_access(tenant1) is True

    def test_null_tenant_id_returns_true(
        self, db: Session, tenant1_context: TenantContext, user_no_tenant: User
    ):
        """Objects with null tenant_id are accessible (legacy data)"""
        service = UserService(db, tenant1_context)
        assert service.verify_tenant_access(user_no_tenant) is True

    def test_matching_tenant_returns_true(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User
    ):
        """Objects in user's tenant are accessible"""
        service = UserService(db, tenant1_context)
        assert service.verify_tenant_access(user_tenant1) is True

    def test_different_tenant_returns_false(
        self, db: Session, tenant1_context: TenantContext, user_tenant2: User
    ):
        """Objects in different tenant are NOT accessible"""
        service = UserService(db, tenant1_context)
        assert service.verify_tenant_access(user_tenant2) is False

    def test_document_access_matching_tenant(
        self, db: Session, tenant1_context: TenantContext, doc_tenant1: Document
    ):
        """Document in user's tenant is accessible"""
        service = DocumentService(db, tenant1_context)
        assert service.verify_tenant_access(doc_tenant1) is True

    def test_document_access_different_tenant(
        self, db: Session, tenant1_context: TenantContext, doc_tenant2: Document
    ):
        """Document in different tenant is NOT accessible"""
        service = DocumentService(db, tenant1_context)
        assert service.verify_tenant_access(doc_tenant2) is False


# ============================================================================
# Test: Cross-Tenant Isolation (Integration)
# ============================================================================


class TestCrossTenantIsolation:
    """Integration tests for complete tenant isolation"""

    def test_tenant_cannot_access_other_tenant_data(
        self,
        db: Session,
        tenant1_context: TenantContext,
        tenant2_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
        doc_tenant1: Document,
        doc_tenant2: Document,
    ):
        """Complete isolation test - tenant1 cannot see tenant2 data"""
        service1 = UserService(db, tenant1_context)
        service2 = UserService(db, tenant2_context)

        # Tenant1 queries
        t1_users = service1.get_all()
        t1_user_ids = [u.id for u in t1_users]

        # Tenant2 queries
        t2_users = service2.get_all()
        t2_user_ids = [u.id for u in t2_users]

        # Verify isolation
        assert user_tenant1.id in t1_user_ids
        assert user_tenant2.id not in t1_user_ids

        assert user_tenant2.id in t2_user_ids
        assert user_tenant1.id not in t2_user_ids

    def test_system_admin_can_access_all_tenants(
        self,
        db: Session,
        system_admin_context: TenantContext,
        user_tenant1: User,
        user_tenant2: User,
        doc_tenant1: Document,
        doc_tenant2: Document,
    ):
        """System admin has access to all tenant data"""
        user_service = UserService(db, system_admin_context)
        doc_service = DocumentService(db, system_admin_context)

        # Get all users
        all_users = user_service.get_all()
        user_ids = [u.id for u in all_users]

        # Get all documents
        all_docs = doc_service.get_all()
        doc_ids = [d.id for d in all_docs]

        # Verify access to all
        assert user_tenant1.id in user_ids
        assert user_tenant2.id in user_ids
        assert doc_tenant1.id in doc_ids
        assert doc_tenant2.id in doc_ids

    def test_create_in_tenant_visible_only_to_that_tenant(
        self,
        db: Session,
        tenant1_context: TenantContext,
        tenant2_context: TenantContext,
        tenant1: Tenant,
    ):
        """Records created in tenant1 are not visible to tenant2"""
        service1 = DocumentService(db, tenant1_context)
        service2 = DocumentService(db, tenant2_context)

        # Create document in tenant1
        new_doc = Document(
            title="Isolation Test Doc",
            document_number="DOC-ISO-001",
            description="Testing isolation",
            status=DocumentStatus.DRAFT,
            visibility=DocumentVisibility.INTERNAL,
            created_by=tenant1_context.user_id,
        )
        created = service1.create(new_doc)

        # Tenant1 can see it
        t1_result = service1.get_by_id(created.id)
        assert t1_result is not None

        # Tenant2 cannot see it
        t2_result = service2.get_by_id(created.id)
        assert t2_result is None


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_service_with_admin_context_not_system_admin(
        self, db: Session, tenant1: Tenant, user_tenant1: User
    ):
        """Admin role (not system_admin) still has tenant filtering"""
        admin_context = TenantContext(
            tenant_id=tenant1.id,
            user_id=user_tenant1.id,
            user_role=UserRole.ADMIN,
            is_system_admin=False,  # Admin but not system admin
        )

        service = UserService(db, admin_context)
        query = service._base_query()

        # Should still filter by tenant
        # Verify by checking SQL contains tenant filter
        results = query.all()
        for user in results:
            assert user.tenant_id == tenant1.id or user.tenant_id is None

    def test_multiple_services_same_context(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User, doc_tenant1: Document
    ):
        """Multiple services can share same tenant context"""
        user_service = UserService(db, tenant1_context)
        doc_service = DocumentService(db, tenant1_context)

        # Both should use same tenant context
        assert user_service.tenant_ctx is tenant1_context
        assert doc_service.tenant_ctx is tenant1_context

        # Both should filter correctly
        users = user_service.get_all()
        docs = doc_service.get_all()

        assert all(u.tenant_id == tenant1_context.tenant_id for u in users)
        assert all(d.tenant_id == tenant1_context.tenant_id for d in docs)

    def test_default_pagination_limit(
        self, db: Session, tenant1: Tenant, tenant1_context: TenantContext
    ):
        """Default limit is 100 records"""
        # Create 105 users
        for i in range(105):
            user = User(
                email=f"limit_test_{i}@tenant1.com",
                username=f"limit_user_{i}",
                full_name=f"Limit User {i}",
                hashed_password=get_password_hash("password"),
                role=UserRole.VIEWER,
                is_active=True,
                tenant_id=tenant1.id,
            )
            db.add(user)
        db.commit()

        service = UserService(db, tenant1_context)
        results = service.get_all()  # Default limit

        assert len(results) == 100

    def test_zero_skip_and_limit(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User
    ):
        """Skip=0 and limit=0 returns empty list"""
        service = UserService(db, tenant1_context)
        results = service.get_all(skip=0, limit=0)
        assert results == []

    def test_large_skip_returns_empty(
        self, db: Session, tenant1_context: TenantContext, user_tenant1: User
    ):
        """Skip larger than total count returns empty list"""
        service = UserService(db, tenant1_context)
        results = service.get_all(skip=10000)
        assert results == []
