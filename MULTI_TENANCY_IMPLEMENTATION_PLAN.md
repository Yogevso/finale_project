# Multi-Tenancy Implementation Plan

## 📋 Overview

**Goal**: Add full tenant isolation to V2 Document Portal
**Estimated Effort**: 6-8 hours
**Risk Level**: Medium (touches core data layer)

### What Multi-Tenancy Means
- Each tenant is a separate organization/company
- Users belong to exactly one tenant
- Documents, comments, attachments are isolated per tenant
- Tenant A cannot see or access Tenant B's data
- Super Admin can manage all tenants

---

## 🏗️ Architecture Design

### Current State (Single-Tenant)
```
User → Documents → Versions → Attachments → Comments
```

### Target State (Multi-Tenant)
```
Tenant
  ├── User (belongs to tenant)
  │     └── Documents (owned by user, scoped to tenant)
  │           ├── Versions
  │           ├── Attachments
  │           └── Comments (scoped to tenant users)
  └── Settings (per-tenant configuration)
```

### Tenant Identification Strategy
- **Option A**: Subdomain-based (`tenant1.portal.com`) - Complex, requires DNS
- **Option B**: Path-based (`/api/v1/tenant1/...`) - Medium complexity
- **Option C**: Header/Token-based (tenant_id in JWT) - ✅ **CHOSEN** - Simplest

---

## 📅 Implementation Phases

### Phase 1: Database Schema Changes (1.5-2 hours)

#### 1.1 Create Tenant Model
- **1.1.1** Create `Tenant` SQLAlchemy model
  ```python
  # app/models/__init__.py
  class Tenant(Base):
      __tablename__ = "tenants"
      
      id = Column(Integer, primary_key=True, index=True)
      name = Column(String(255), nullable=False)
      slug = Column(String(100), unique=True, index=True, nullable=False)
      is_active = Column(Boolean, default=True, nullable=False)
      settings = Column(Text, nullable=True)  # JSON settings
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
      
      # Relationships
      users = relationship("User", back_populates="tenant")
      documents = relationship("Document", back_populates="tenant")
  ```

- **1.1.2** Create tenant schemas
  ```python
  # app/schemas/tenant.py
  class TenantBase(BaseModel):
      name: str
      slug: str
      is_active: bool = True
      
  class TenantCreate(TenantBase):
      pass
      
  class TenantResponse(TenantBase):
      id: int
      created_at: datetime
      
  class TenantInDB(TenantResponse):
      settings: Optional[str] = None
  ```

#### 1.2 Add tenant_id to User Model
- **1.2.1** Add `tenant_id` foreign key to User
  ```python
  class User(Base):
      # ... existing fields ...
      tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
      
      # Add relationship
      tenant = relationship("Tenant", back_populates="users")
  ```

- **1.2.2** Update UserRole enum
  ```python
  class UserRole(str, enum.Enum):
      SUPER_ADMIN = "super_admin"  # NEW - can manage all tenants
      ADMIN = "admin"              # Tenant admin
      EDITOR = "editor"
      VIEWER = "viewer"
  ```

#### 1.3 Add tenant_id to Document Model
- **1.3.1** Add `tenant_id` foreign key
  ```python
  class Document(Base):
      # ... existing fields ...
      tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
      
      # Add relationship
      tenant = relationship("Tenant", back_populates="documents")
  ```

#### 1.4 Create Database Migration
- **1.4.1** Create migration script for existing data
  ```python
  # scripts/migrate_to_multi_tenant.py
  """
  Migration steps:
  1. Create default tenant
  2. Add tenant_id columns (nullable first)
  3. Populate tenant_id with default tenant
  4. Make tenant_id NOT NULL
  5. Create indexes
  """
  ```

- **1.4.2** Test migration on copy of production data

#### 1.5 Verification Tests
- [ ] Tenant table created
- [ ] User has tenant_id column
- [ ] Document has tenant_id column
- [ ] Foreign keys working
- [ ] Indexes created

---

### Phase 2: Authentication & Authorization Changes (1.5-2 hours)

#### 2.1 Update JWT Token Payload
- **2.1.1** Add tenant_id to token
  ```python
  # app/security.py
  def create_access_token(
      user_id: int,
      tenant_id: int,  # NEW
      role: str,
      expires_delta: timedelta = None
  ) -> str:
      payload = {
          "sub": str(user_id),
          "tenant_id": tenant_id,  # NEW
          "role": role,
          "exp": datetime.utcnow() + (expires_delta or timedelta(minutes=30))
      }
      return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
  ```

- **2.1.2** Update token response schema
  ```python
  # app/schemas/auth.py
  class TokenPayload(BaseModel):
      sub: int
      tenant_id: int  # NEW
      role: str
      exp: datetime
  ```

#### 2.2 Update Auth Dependencies
- **2.2.1** Create TenantContext dependency
  ```python
  # app/dependencies.py
  class TenantContext:
      def __init__(self, tenant_id: int, user_id: int, role: str):
          self.tenant_id = tenant_id
          self.user_id = user_id
          self.role = role
          self.is_super_admin = role == "super_admin"
  
  async def get_tenant_context(
      token: str = Depends(oauth2_scheme),
      db: Session = Depends(get_db)
  ) -> TenantContext:
      payload = decode_token(token)
      return TenantContext(
          tenant_id=payload.tenant_id,
          user_id=payload.sub,
          role=payload.role
      )
  ```

- **2.2.2** Update get_current_user to include tenant
  ```python
  async def get_current_user(
      token: str = Depends(oauth2_scheme),
      db: Session = Depends(get_db)
  ) -> User:
      payload = decode_token(token)
      user = db.query(User).filter(
          User.id == payload.sub,
          User.tenant_id == payload.tenant_id  # NEW - verify tenant
      ).first()
      if not user:
          raise HTTPException(status_code=401, detail="User not found")
      return user
  ```

#### 2.3 Update Login Flow
- **2.3.1** Login returns tenant info
  ```python
  # app/services/auth_service.py
  def login(self, username: str, password: str) -> TokenResponse:
      user = self._get_user_by_username(username)
      # ... password verification ...
      
      access_token = create_access_token(
          user_id=user.id,
          tenant_id=user.tenant_id,  # NEW
          role=user.role.value
      )
      # ...
  ```

- **2.3.2** Update TokenResponse schema
  ```python
  class TokenResponse(BaseModel):
      access_token: str
      refresh_token: Optional[str]
      token_type: str = "bearer"
      tenant_id: int  # NEW
      tenant_name: str  # NEW
  ```

#### 2.4 Verification Tests
- [ ] JWT contains tenant_id
- [ ] Login returns tenant info
- [ ] Token validation checks tenant
- [ ] Super admin bypass works

---

### Phase 3: Service Layer Changes (1.5-2 hours)

#### 3.1 Create Base Tenant-Aware Service
- **3.1.1** Create TenantAwareService base class
  ```python
  # app/services/base.py
  class TenantAwareService:
      def __init__(self, db: Session, tenant_context: TenantContext):
          self.db = db
          self.ctx = tenant_context
      
      def _tenant_filter(self, query, model):
          """Apply tenant filter unless super_admin"""
          if self.ctx.is_super_admin:
              return query
          return query.filter(model.tenant_id == self.ctx.tenant_id)
  ```

#### 3.2 Update DocumentService
- **3.2.1** Inherit from TenantAwareService
  ```python
  # app/services/document_service.py
  class DocumentService(TenantAwareService):
      def get_documents(self, params: DocumentQueryParams) -> DocumentListResponse:
          query = self.db.query(Document)
          query = self._tenant_filter(query, Document)  # NEW
          # ... rest of query ...
      
      def create_document(self, data: DocumentCreate) -> Document:
          doc = Document(
              **data.model_dump(),
              tenant_id=self.ctx.tenant_id,  # NEW
              created_by=self.ctx.user_id
          )
          # ...
      
      def get_document(self, doc_id: int) -> Document:
          query = self.db.query(Document).filter(Document.id == doc_id)
          query = self._tenant_filter(query, Document)  # NEW
          doc = query.first()
          if not doc:
              raise HTTPException(status_code=404, detail="Document not found")
          return doc
  ```

- **3.2.2** Update all document methods
  - [ ] get_documents - add tenant filter
  - [ ] get_document - add tenant filter
  - [ ] create_document - set tenant_id
  - [ ] update_document - verify tenant ownership
  - [ ] delete_document - verify tenant ownership

#### 3.3 Update VersionService
- **3.3.1** Add tenant awareness
  ```python
  class VersionService(TenantAwareService):
      def get_versions(self, document_id: int) -> List[Version]:
          # First verify document belongs to tenant
          doc = self._verify_document_access(document_id)
          return doc.versions
      
      def _verify_document_access(self, doc_id: int) -> Document:
          query = self.db.query(Document).filter(Document.id == doc_id)
          query = self._tenant_filter(query, Document)
          doc = query.first()
          if not doc:
              raise HTTPException(status_code=404)
          return doc
  ```

#### 3.4 Update AttachmentService
- **3.4.1** Add tenant awareness (same pattern as VersionService)

#### 3.5 Update CommentService
- **3.5.1** Add tenant awareness
- **3.5.2** Ensure comments only visible to tenant users

#### 3.6 Update UserService (if exists)
- **3.6.1** Users can only see users in same tenant
- **3.6.2** Admins can manage tenant users
- **3.6.3** Super admins can see all

#### 3.7 Verification Tests
- [ ] Documents filtered by tenant
- [ ] Versions filtered by parent document's tenant
- [ ] Attachments filtered by parent document's tenant
- [ ] Comments filtered by tenant
- [ ] Create operations set tenant_id
- [ ] Cross-tenant access blocked (404 not 403)

---

### Phase 4: API Endpoint Updates (1 hour)

#### 4.1 Update Document Endpoints
- **4.1.1** Inject TenantContext instead of just current_user
  ```python
  # app/api/management/documents.py
  @router.get("")
  async def list_documents(
      params: DocumentQueryParams = Depends(),
      ctx: TenantContext = Depends(get_tenant_context),  # NEW
      db: Session = Depends(get_db)
  ):
      service = DocumentService(db, ctx)  # NEW
      return service.get_documents(params)
  ```

- **4.1.2** Update all document endpoints
  - [ ] GET /documents
  - [ ] POST /documents
  - [ ] GET /documents/{id}
  - [ ] PATCH /documents/{id}
  - [ ] DELETE /documents/{id}

#### 4.2 Update Version Endpoints
- **4.2.1** Same pattern - inject TenantContext

#### 4.3 Update Attachment Endpoints
- **4.3.1** Same pattern

#### 4.4 Update Comment Endpoints
- **4.4.1** Same pattern

#### 4.5 Create Tenant Management Endpoints (Admin only)
- **4.5.1** Create tenant router
  ```python
  # app/api/management/tenants.py
  router = APIRouter(prefix="/tenants", tags=["Tenants"])
  
  @router.get("")
  async def list_tenants(
      ctx: TenantContext = Depends(require_super_admin),
      db: Session = Depends(get_db)
  ):
      """Super admin only: List all tenants"""
      return db.query(Tenant).all()
  
  @router.post("")
  async def create_tenant(
      data: TenantCreate,
      ctx: TenantContext = Depends(require_super_admin),
      db: Session = Depends(get_db)
  ):
      """Super admin only: Create new tenant"""
      tenant = Tenant(**data.model_dump())
      db.add(tenant)
      db.commit()
      return tenant
  
  @router.get("/{tenant_id}")
  async def get_tenant(tenant_id: int, ...):
      """Get tenant details"""
  
  @router.patch("/{tenant_id}")
  async def update_tenant(tenant_id: int, data: TenantUpdate, ...):
      """Update tenant"""
  
  @router.delete("/{tenant_id}")
  async def delete_tenant(tenant_id: int, ...):
      """Deactivate tenant (soft delete)"""
  ```

- **4.5.2** Register router in main.py

#### 4.6 Update Viewer Portal Endpoints
- **4.6.1** Viewer portal shows documents from ALL active tenants (public view)
  ```python
  # app/api/viewer/documents.py
  @router.get("")
  async def list_public_documents(db: Session = Depends(get_db)):
      """Public viewer - shows all active documents from all tenants"""
      return db.query(Document).filter(
          Document.status == DocumentStatus.ACTIVE
      ).all()
  ```

  OR

- **4.6.2** Viewer portal is tenant-specific (via subdomain/path)
  ```python
  @router.get("/{tenant_slug}/documents")
  async def list_tenant_public_documents(
      tenant_slug: str,
      db: Session = Depends(get_db)
  ):
      """Public viewer - shows active documents for specific tenant"""
      tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
      if not tenant:
          raise HTTPException(status_code=404)
      return db.query(Document).filter(
          Document.tenant_id == tenant.id,
          Document.status == DocumentStatus.ACTIVE
      ).all()
  ```

#### 4.7 Verification Tests
- [ ] All endpoints use TenantContext
- [ ] Tenant management endpoints work
- [ ] Super admin can access all tenants
- [ ] Regular users restricted to their tenant

---

### Phase 5: Database Migration & Seed Data (0.5-1 hour)

#### 5.1 Create Migration Script
- **5.1.1** Write migration script
  ```python
  # scripts/migrate_to_multi_tenant.py
  from app.db import engine, SessionLocal
  from app.models import Tenant, User, Document
  
  def migrate():
      db = SessionLocal()
      
      # 1. Create tenants table
      Tenant.__table__.create(engine, checkfirst=True)
      
      # 2. Create default tenant
      default_tenant = Tenant(
          name="Default Organization",
          slug="default",
          is_active=True
      )
      db.add(default_tenant)
      db.commit()
      
      # 3. Update all existing users
      db.execute(
          "UPDATE users SET tenant_id = :tid WHERE tenant_id IS NULL",
          {"tid": default_tenant.id}
      )
      
      # 4. Update all existing documents
      db.execute(
          "UPDATE documents SET tenant_id = :tid WHERE tenant_id IS NULL",
          {"tid": default_tenant.id}
      )
      
      db.commit()
      print(f"Migration complete. Default tenant ID: {default_tenant.id}")
  
  if __name__ == "__main__":
      migrate()
  ```

#### 5.2 Create Test Tenants
- **5.2.1** Create seed script for testing
  ```python
  # scripts/seed_tenants.py
  def seed_tenants():
      db = SessionLocal()
      
      # Create Tenant 1: Acme Corp
      acme = Tenant(name="Acme Corporation", slug="acme", is_active=True)
      db.add(acme)
      
      # Create Tenant 2: Beta Inc
      beta = Tenant(name="Beta Industries", slug="beta", is_active=True)
      db.add(beta)
      
      db.commit()
      
      # Create users for each tenant
      acme_admin = User(
          username="acme_admin",
          email="admin@acme.com",
          full_name="Acme Admin",
          hashed_password=get_password_hash("acme123"),
          role=UserRole.ADMIN,
          tenant_id=acme.id
      )
      
      beta_admin = User(
          username="beta_admin",
          email="admin@beta.com",
          full_name="Beta Admin",
          hashed_password=get_password_hash("beta123"),
          role=UserRole.ADMIN,
          tenant_id=beta.id
      )
      
      # Create super admin (no tenant restriction)
      super_admin = User(
          username="super_admin",
          email="super@portal.com",
          full_name="Super Admin",
          hashed_password=get_password_hash("super123"),
          role=UserRole.SUPER_ADMIN,
          tenant_id=acme.id  # Has a home tenant but can access all
      )
      
      db.add_all([acme_admin, beta_admin, super_admin])
      db.commit()
      
      # Create sample documents for each tenant
      # ... (similar pattern)
  ```

#### 5.3 Run Migration
- **5.3.1** Backup existing database
- **5.3.2** Run migration script
- **5.3.3** Verify data integrity
- **5.3.4** Run seed script for test tenants

---

### Phase 6: Testing & Verification (1 hour)

#### 6.1 Unit Tests
- **6.1.1** Test TenantContext creation
- **6.1.2** Test tenant filter logic
- **6.1.3** Test super admin bypass

#### 6.2 Integration Tests
- **6.2.1** Test tenant isolation
  ```python
  # tests/test_multi_tenancy.py
  
  @pytest.fixture
  def tenant_a():
      return create_tenant("Tenant A", "tenant-a")
  
  @pytest.fixture
  def tenant_b():
      return create_tenant("Tenant B", "tenant-b")
  
  @pytest.fixture
  def user_a(tenant_a):
      return create_user("user_a", tenant_a.id)
  
  @pytest.fixture
  def user_b(tenant_b):
      return create_user("user_b", tenant_b.id)
  
  def test_user_a_cannot_see_tenant_b_documents(client, user_a, tenant_b):
      # Create document in tenant B
      doc = create_document(tenant_id=tenant_b.id)
      
      # Login as user A
      token = login_as(user_a)
      
      # Try to access tenant B's document
      response = client.get(
          f"/api/v1/documents/{doc.id}",
          headers={"Authorization": f"Bearer {token}"}
      )
      
      # Should get 404 (not 403 - don't reveal existence)
      assert response.status_code == 404
  
  def test_user_a_can_see_own_tenant_documents(client, user_a, tenant_a):
      doc = create_document(tenant_id=tenant_a.id)
      token = login_as(user_a)
      
      response = client.get(
          f"/api/v1/documents/{doc.id}",
          headers={"Authorization": f"Bearer {token}"}
      )
      
      assert response.status_code == 200
      assert response.json()["id"] == doc.id
  
  def test_super_admin_can_see_all_tenants(client, super_admin, tenant_a, tenant_b):
      doc_a = create_document(tenant_id=tenant_a.id)
      doc_b = create_document(tenant_id=tenant_b.id)
      token = login_as(super_admin)
      
      # Can see tenant A's document
      response = client.get(
          f"/api/v1/documents/{doc_a.id}",
          headers={"Authorization": f"Bearer {token}"}
      )
      assert response.status_code == 200
      
      # Can also see tenant B's document
      response = client.get(
          f"/api/v1/documents/{doc_b.id}",
          headers={"Authorization": f"Bearer {token}"}
      )
      assert response.status_code == 200
  
  def test_document_list_filtered_by_tenant(client, user_a, tenant_a, tenant_b):
      # Create docs in both tenants
      doc_a = create_document(tenant_id=tenant_a.id, title="Tenant A Doc")
      doc_b = create_document(tenant_id=tenant_b.id, title="Tenant B Doc")
      
      token = login_as(user_a)
      response = client.get(
          "/api/v1/documents",
          headers={"Authorization": f"Bearer {token}"}
      )
      
      docs = response.json()["items"]
      titles = [d["title"] for d in docs]
      
      assert "Tenant A Doc" in titles
      assert "Tenant B Doc" not in titles
  ```

#### 6.3 E2E Tests
- **6.3.1** Create E2E test for tenant isolation
  ```typescript
  // e2e/multi-tenancy.spec.ts
  test.describe('Multi-Tenancy Isolation', () => {
    test('tenant A user cannot access tenant B documents', async ({ page }) => {
      // Login as tenant A user
      await loginAs(page, 'acme_admin', 'acme123');
      
      // Go to documents
      await page.goto('/documents');
      
      // Should only see Acme documents
      await expect(page.locator('body')).toContainText('Acme');
      await expect(page.locator('body')).not.toContainText('Beta Doc');
    });
    
    test('super admin can switch tenants', async ({ page }) => {
      await loginAs(page, 'super_admin', 'super123');
      
      // Should see tenant switcher
      await expect(page.locator('[data-testid="tenant-switcher"]')).toBeVisible();
    });
  });
  ```

#### 6.4 Manual Testing Checklist
- [ ] Login as acme_admin → only see Acme documents
- [ ] Login as beta_admin → only see Beta documents
- [ ] Login as super_admin → see all documents
- [ ] Create document as acme_admin → appears in Acme only
- [ ] Try direct URL to Beta doc as Acme user → 404
- [ ] Comments only from same tenant users
- [ ] Attachments isolated per tenant

---

### Phase 7: Frontend Updates (Optional - 1 hour)

#### 7.1 Display Tenant Info
- **7.1.1** Show tenant name in header/sidebar
- **7.1.2** Store tenant info in auth context

#### 7.2 Super Admin Tenant Switcher
- **7.2.1** Create TenantSwitcher component
  ```tsx
  // src/components/TenantSwitcher.tsx
  export function TenantSwitcher() {
    const { user, setActiveTenant } = useAuth();
    const { data: tenants } = useQuery(['tenants'], api.getTenants);
    
    if (user.role !== 'super_admin') return null;
    
    return (
      <select onChange={(e) => setActiveTenant(e.target.value)}>
        {tenants?.map(t => (
          <option key={t.id} value={t.id}>{t.name}</option>
        ))}
      </select>
    );
  }
  ```

#### 7.3 Tenant Management Page (Super Admin)
- **7.3.1** Create /admin/tenants page
- **7.3.2** List all tenants
- **7.3.3** Create new tenant
- **7.3.4** Edit tenant settings
- **7.3.5** Deactivate tenant

---

## 📊 Implementation Checklist

### Database Layer
- [ ] Create Tenant model
- [ ] Add tenant_id to User model
- [ ] Add tenant_id to Document model
- [ ] Create migration script
- [ ] Run migration
- [ ] Verify existing data migrated

### Authentication
- [ ] Add tenant_id to JWT payload
- [ ] Update token creation
- [ ] Update token validation
- [ ] Create TenantContext dependency
- [ ] Add SUPER_ADMIN role

### Services
- [ ] Create TenantAwareService base
- [ ] Update DocumentService
- [ ] Update VersionService
- [ ] Update AttachmentService
- [ ] Update CommentService
- [ ] Update SearchService

### API Endpoints
- [ ] Update document endpoints
- [ ] Update version endpoints
- [ ] Update attachment endpoints
- [ ] Update comment endpoints
- [ ] Create tenant management endpoints
- [ ] Update viewer portal (if needed)

### Testing
- [ ] Create multi-tenancy test fixtures
- [ ] Write isolation tests
- [ ] Write super admin tests
- [ ] Run full test suite
- [ ] Manual verification

### Documentation
- [ ] Update API docs
- [ ] Update ARCHITECTURE.md
- [ ] Document tenant setup process

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data leak between tenants | Critical | Extensive testing, code review |
| Existing data broken | High | Backup before migration |
| Performance degradation | Medium | Add indexes on tenant_id |
| Auth token issues | High | Backward compatibility in token validation |

---

## 🚀 Execution Order

1. **Backup database**
2. **Phase 1**: Database schema changes
3. **Phase 2**: Auth updates
4. **Phase 3**: Service layer
5. **Phase 4**: API endpoints
6. **Phase 5**: Migration & seed
7. **Phase 6**: Testing
8. **Phase 7**: Frontend (optional)

---

## 📝 Test Users After Implementation

| Username | Password | Tenant | Role |
|----------|----------|--------|------|
| super_admin | super123 | (all) | SUPER_ADMIN |
| acme_admin | acme123 | Acme Corp | ADMIN |
| acme_editor | acme123 | Acme Corp | EDITOR |
| beta_admin | beta123 | Beta Inc | ADMIN |
| beta_editor | beta123 | Beta Inc | EDITOR |

---

Ready to implement? Start with Phase 1!
