# Public Portal + Customer Access + Role-Based Permissions

## Detailed Implementation Plan

**Feature**: Multi-tenant customer portal with public space and granular permissions  
**Status**: 📋 PLANNED  
**Estimated Time**: 42-52 hours  
**Priority**: High  

> A comprehensive step-by-step plan expanding each phase into actionable sub-tasks with exact file paths, code patterns, and dependencies.

---

## Overview

Implement a public-facing document portal, customer-specific access, and enhanced role-based permissions with peer review workflow.

---

## Roles (6 Total)

| Role | Type | Description |
|------|------|-------------|
| **system_admin** | Internal | Full platform control, manages admins |
| **admin** | Internal | Manages users, companies, full access |
| **manager** | Internal | Approves content, creates editors, publishes |
| **editor** | Internal | Creates/edits content, peer reviews |
| **customer** | External | Views company docs, downloads, submits feedback |
| *(anonymous)* | Public | Views public published docs only |

---

## Permission Matrix

| Action                    | system_admin | admin | manager | editor | customer |
|---------------------------|:------------:|:-----:|:-------:|:------:|:--------:|
| View public docs          | ✅           | ✅    | ✅      | ✅     | ✅       |
| View internal docs        | ✅           | ✅    | ✅      | ✅     | ❌       |
| View company docs         | ✅           | ✅    | ✅      | ✅     | Own only |
| Create documents          | ✅           | ✅    | ✅      | ✅     | ❌       |
| Edit documents            | ✅           | ✅    | ✅      | ✅     | ❌       |
| Delete documents          | ✅           | ✅    | ✅      | ❌     | ❌       |
| Submit for review         | ✅           | ✅    | ✅      | ✅     | ❌       |
| Approve/Reject reviews    | ✅           | ✅    | ✅      | Peers  | ❌       |
| Publish documents         | ✅           | ✅    | ✅      | ❌     | ❌       |
| Assign to companies       | ✅           | ✅    | ✅      | ❌     | ❌       |
| Download attachments      | ✅           | ✅    | ✅      | ✅     | ✅       |
| Add comments              | ✅           | ✅    | ✅      | ✅     | ❌       |
| Submit feedback           | ✅           | ✅    | ✅      | ✅     | ✅       |
| Manage users              | ✅           | ✅    | Editors | ❌     | ❌       |
| Manage companies          | ✅           | ✅    | ❌      | ❌     | ❌       |
| System settings           | ✅           | ✅    | ❌      | ❌     | ❌       |
| Manage admins             | ✅           | ❌    | ❌      | ❌     | ❌       |

---

## Document Visibility Levels

| Level | Who Can See |
|-------|-------------|
| **PUBLIC** | Everyone (no login needed) |
| **INTERNAL** | All internal staff (editor+) |
| **COMPANY** | Assigned companies + internal staff |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOCUMENT PORTAL                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      🌐 PUBLIC PORTAL (/)                           │   │
│  │  • Browse PUBLIC + PUBLISHED documents                              │   │
│  │  • Full-text search                                                 │   │
│  │  • View full document details                                       │   │
│  │  • [Login] button                                                   │   │
│  │  • NO company-specific docs visible                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                           ┌───────┴───────┐                                │
│                           │    /login     │                                │
│                           └───────┬───────┘                                │
│                                   │                                        │
│        ┌──────────────────────────┼──────────────────────────┐            │
│        ▼                          ▼                          ▼            │
│  ┌──────────┐           ┌─────────────────┐          ┌──────────────┐     │
│  │ CUSTOMER │           │ EDITOR/MANAGER  │          │    ADMIN     │     │
│  │  PORTAL  │           │     PORTAL      │          │    PORTAL    │     │
│  │  /portal │           │   /dashboard    │          │    /admin    │     │
│  └──────────┘           └─────────────────┘          └──────────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        COMPANY ISOLATION                            │   │
│  │  🏢 Dell Corp      🏢 Acme Inc       🏢 TechStart                   │   │
│  │  └─ Dell docs      └─ Acme docs      └─ TechStart docs              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Approval Workflow

```
Editor creates doc
        │
        ▼
Submits for review ──────────────────────────────────┐
        │                                            │
        ▼                                            ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│ Peer Editor │  OR │   Manager   │  OR │       Admin         │
│ (not self)  │     │             │     │                     │
└──────┬──────┘     └──────┬──────┘     └──────────┬──────────┘
       │                   │                       │
       └───────────────────┴───────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
          ✅ APPROVED            ❌ REJECTED
                │                     │
                ▼                     ▼
          Can Publish         Returns to Editor
                              with comments
```

---

# Implementation Steps

---

## Step 1: Update Database Models & Roles (3-4 hrs)

### 1.1 Update UserRole Enum
**File**: `v2/backend/app/models/__init__.py`  
**Current**: `SUPER_ADMIN`, `ADMIN`, `EDITOR`, `VIEWER`

- [ ] **1.1.1** Rename `SUPER_ADMIN` → `SYSTEM_ADMIN`
- [ ] **1.1.2** Add `MANAGER = "manager"` between ADMIN and EDITOR
- [ ] **1.1.3** Add `CUSTOMER = "customer"` after VIEWER
- [ ] **1.1.4** Update `__all__` exports if needed

**Final enum:**
```python
class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    VIEWER = "viewer"
    CUSTOMER = "customer"
```

### 1.2 Create DocumentVisibility Enum
**File**: `v2/backend/app/models/__init__.py`

- [ ] **1.2.1** Add new enum after `DocumentStatus`:
```python
class DocumentVisibility(str, enum.Enum):
    PUBLIC = "public"      # Anyone can see
    INTERNAL = "internal"  # Staff only
    COMPANY = "company"    # Assigned companies + staff
```
- [ ] **1.2.2** Add to `__all__` exports

### 1.3 Update Document Model
**File**: `v2/backend/app/models/__init__.py` (Lines 92-114)

- [ ] **1.3.1** Add `visibility` column after `status`:
```python
visibility = Column(Enum(DocumentVisibility), default=DocumentVisibility.INTERNAL, index=True)
```
- [ ] **1.3.2** Add `assigned_companies` relationship (after junction table created)

### 1.4 Create Document-Company Junction Table
**File**: `v2/backend/app/models/__init__.py`

- [ ] **1.4.1** Add junction table after Tenant model:
```python
document_company_assignments = Table(
    'document_company_assignments',
    Base.metadata,
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True),
    Column('tenant_id', Integer, ForeignKey('tenants.id'), primary_key=True),
    Column('assigned_at', DateTime, default=datetime.utcnow),
    Column('assigned_by', Integer, ForeignKey('users.id'))
)
```
- [ ] **1.4.2** Add relationship to Document model:
```python
assigned_companies = relationship("Tenant", secondary=document_company_assignments, backref="assigned_documents")
```

### 1.5 Enhance Tenant Model
**File**: `v2/backend/app/models/__init__.py` (Lines 51-63)

- [ ] **1.5.1** Add `company_logo = Column(String(500), nullable=True)`
- [ ] **1.5.2** Add `contact_email = Column(String(255), nullable=True)`
- [ ] **1.5.3** Add `company_type = Column(String(50), default="customer")` (customer, partner, internal)

### 1.6 Create ReviewRequest Model
**File**: `v2/backend/app/models/__init__.py`

- [ ] **1.6.1** Create ReviewStatus enum:
```python
class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
```
- [ ] **1.6.2** Create ReviewRequest model:
```python
class ReviewRequest(Base):
    __tablename__ = "review_requests"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    document = relationship("Document", backref="review_requests")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
```
- [ ] **1.6.3** Add to `__all__` exports

### 1.7 Update Feedback Model (if needed)
**File**: `v2/backend/app/models/__init__.py`

- [ ] **1.7.1** Verify existing Feedback model has: `feedback_type`, `status`, `response`, `responded_by`
- [ ] **1.7.2** Add FeedbackType enum if missing:
```python
class FeedbackType(str, enum.Enum):
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    OTHER = "other"
```
- [ ] **1.7.3** Add FeedbackStatus enum if missing:
```python
class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"
    RESPONDED = "responded"
    CLOSED = "closed"
```

### 1.8 Create Database Migration
**File**: Create `v2/backend/migrations/add_customer_portal_fields.py`

- [ ] **1.8.1** Create Alembic migration or manual SQL script
- [ ] **1.8.2** Handle existing data (set default visibility = INTERNAL)
- [ ] **1.8.3** Update existing `super_admin` → `system_admin` in users table

### 1.9 Update Frontend Types
**File**: `v2/frontend/src/types/index.ts`

- [ ] **1.9.1** Update `UserRole` type:
```typescript
export type UserRole = 'system_admin' | 'admin' | 'manager' | 'editor' | 'viewer' | 'customer'
```
- [ ] **1.9.2** Add `DocumentVisibility` type:
```typescript
export type DocumentVisibility = 'public' | 'internal' | 'company'
```
- [ ] **1.9.3** Add `ReviewStatus` type
- [ ] **1.9.4** Update `Document` interface with `visibility` field

---

## Step 2: Implement Permission System (4-5 hrs)

### 2.1 Create Permissions Service
**File**: Create `v2/backend/app/services/permissions.py`

- [ ] **2.1.1** Create permission action enum:
```python
class Permission(str, Enum):
    VIEW_PUBLIC_DOCS = "view_public_docs"
    VIEW_INTERNAL_DOCS = "view_internal_docs"
    VIEW_COMPANY_DOCS = "view_company_docs"
    CREATE_DOCUMENT = "create_document"
    EDIT_DOCUMENT = "edit_document"
    DELETE_DOCUMENT = "delete_document"
    SUBMIT_REVIEW = "submit_review"
    APPROVE_REVIEW = "approve_review"
    PUBLISH_DOCUMENT = "publish_document"
    ASSIGN_COMPANIES = "assign_companies"
    ADD_COMMENTS = "add_comments"
    SUBMIT_FEEDBACK = "submit_feedback"
    MANAGE_USERS = "manage_users"
    MANAGE_COMPANIES = "manage_companies"
    SYSTEM_SETTINGS = "system_settings"
    MANAGE_ADMINS = "manage_admins"
```

- [ ] **2.1.2** Create permission matrix dictionary:
```python
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.SYSTEM_ADMIN: {Permission.VIEW_PUBLIC_DOCS, Permission.VIEW_INTERNAL_DOCS, ...all...},
    UserRole.ADMIN: {...},
    UserRole.MANAGER: {...},
    UserRole.EDITOR: {...},
    UserRole.VIEWER: {...},
    UserRole.CUSTOMER: {Permission.VIEW_PUBLIC_DOCS, Permission.VIEW_COMPANY_DOCS, Permission.SUBMIT_FEEDBACK},
}
```

- [ ] **2.1.3** Create `has_permission(user: User, permission: Permission) -> bool` function
- [ ] **2.1.4** Create `is_internal_user(user: User) -> bool` helper
- [ ] **2.1.5** Create `can_view_document(user: User, document: Document) -> bool` function

### 2.2 Create Permission Dependencies
**File**: Create `v2/backend/app/dependencies/permissions.py`

- [ ] **2.2.1** Create `require_permission` dependency factory:
```python
def require_permission(permission: Permission):
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if not has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return current_user
    return dependency
```

- [ ] **2.2.2** Create `require_any_role` dependency:
```python
def require_any_role(roles: List[UserRole]):
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current_user
    return dependency
```

- [ ] **2.2.3** Create `require_internal_user` dependency:
```python
async def require_internal_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Internal users only")
    return current_user
```

- [ ] **2.2.4** Create `require_document_access` dependency:
```python
async def require_document_access(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404)
    if not can_view_document(current_user, document):
        raise HTTPException(status_code=403)
    return document
```

### 2.3 Update Existing Security
**File**: `v2/backend/app/security.py`

- [ ] **2.3.1** Import new permission dependencies
- [ ] **2.3.2** Update `require_super_admin` → `require_system_admin`
- [ ] **2.3.3** Export all new dependencies

### 2.4 Update Existing API Endpoints
**Files**: Multiple files in `v2/backend/app/api/management/`

- [ ] **2.4.1** `documents.py`: Replace inline role checks with `require_permission`
- [ ] **2.4.2** `users.py`: Add `require_permission(MANAGE_USERS)`
- [ ] **2.4.3** `tenants.py`: Add `require_permission(MANAGE_COMPANIES)`
- [ ] **2.4.4** `versions.py`: Update publish permission

### 2.5 Update Frontend Auth Context
**File**: `v2/frontend/src/lib/auth.tsx`

- [ ] **2.5.1** Update role helper functions:
```typescript
const isSystemAdmin = user?.role === 'system_admin'
const isAdmin = user?.role === 'admin' || isSystemAdmin
const isManager = user?.role === 'manager' || isAdmin
const isEditor = user?.role === 'editor' || isManager
const isInternal = user?.role !== 'customer'
const isCustomer = user?.role === 'customer'
```
- [ ] **2.5.2** Add `hasPermission(permission: string)` helper
- [ ] **2.5.3** Export new helpers from context

---

## Step 3: Create Public Portal - No Auth (5-6 hrs)

### 3.1 Create Public API Router
**File**: Create `v2/backend/app/api/public/__init__.py`

- [ ] **3.1.1** Create empty `__init__.py`

### 3.2 Create Public Documents Endpoint
**File**: Create `v2/backend/app/api/public/documents.py`

- [ ] **3.2.1** Create router with prefix `/public`:
```python
router = APIRouter(prefix="/public", tags=["Public"])
```

- [ ] **3.2.2** `GET /public/documents` - List public published documents:
  - Filter: `visibility=PUBLIC`, `status=ACTIVE`
  - Pagination: `skip`, `limit`
  - Optional: `category`, `search` query params
  - NO auth dependency

- [ ] **3.2.3** `GET /public/documents/{id}` - Get single public document:
  - Validate: `visibility=PUBLIC`, `status=ACTIVE`
  - Return full content + latest version
  - NO auth dependency

- [ ] **3.2.4** `GET /public/categories` - List categories with public doc counts

- [ ] **3.2.5** `GET /public/search` - Full-text search public docs

### 3.3 Create Public Schemas
**File**: Create `v2/backend/app/schemas/public.py`

- [ ] **3.3.1** `PublicDocumentSummary` - Minimal fields for list
- [ ] **3.3.2** `PublicDocumentDetail` - Full content, no internal metadata
- [ ] **3.3.3** `PublicSearchResult` - Search response format

### 3.4 Register Public Router
**File**: `v2/backend/app/main.py`

- [ ] **3.4.1** Import public router
- [ ] **3.4.2** Add: `app.include_router(public.router, prefix=settings.API_PREFIX, tags=["Public"])`

### 3.5 Create Public Layout Component
**File**: Create `v2/frontend/src/layouts/PublicLayout.tsx`

- [ ] **3.5.1** Simple header with logo + Login button
- [ ] **3.5.2** No sidebar
- [ ] **3.5.3** Full-width content area
- [ ] **3.5.4** Footer with basic links

### 3.6 Create Public Landing Page
**File**: Create `v2/frontend/src/pages/public/PublicHomePage.tsx`

- [ ] **3.6.1** Hero section with search bar
- [ ] **3.6.2** Featured/recent public documents
- [ ] **3.6.3** Category browsing
- [ ] **3.6.4** Login CTA

### 3.7 Create Public Documents List Page
**File**: Create `v2/frontend/src/pages/public/PublicDocumentsPage.tsx`

- [ ] **3.7.1** Grid/list view of public documents
- [ ] **3.7.2** Category filter sidebar
- [ ] **3.7.3** Search integration
- [ ] **3.7.4** Pagination

### 3.8 Create Public Document Viewer
**File**: Create `v2/frontend/src/pages/public/PublicDocumentPage.tsx`

- [ ] **3.8.1** Read-only document display
- [ ] **3.8.2** Table of contents
- [ ] **3.8.3** Download button (if attachments allowed)
- [ ] **3.8.4** "Login for more" prompt

### 3.9 Create Public API Client Functions
**File**: `v2/frontend/src/lib/api.ts`

- [ ] **3.9.1** `fetchPublicDocuments(params)` - No auth header
- [ ] **3.9.2** `fetchPublicDocument(id)` - No auth header
- [ ] **3.9.3** `searchPublicDocuments(query)` - No auth header

### 3.10 Add Public Routes
**File**: `v2/frontend/src/App.tsx`

- [ ] **3.10.1** Add routes outside ProtectedRoute:
```tsx
<Route path="/" element={<PublicLayout />}>
  <Route index element={<PublicHomePage />} />
  <Route path="docs" element={<PublicDocumentsPage />} />
  <Route path="docs/:id" element={<PublicDocumentPage />} />
  <Route path="search" element={<PublicSearchPage />} />
</Route>
```

---

## Step 4: Create Customer Portal (5-6 hrs)

### 4.1 Create Portal API Router
**File**: Create `v2/backend/app/api/portal/__init__.py`

- [ ] **4.1.1** Create empty `__init__.py`

### 4.2 Create Portal Documents Endpoint
**File**: Create `v2/backend/app/api/portal/documents.py`

- [ ] **4.2.1** Create router with prefix `/portal`
- [ ] **4.2.2** `GET /portal/documents` - List docs visible to customer:
  - PUBLIC docs + COMPANY docs assigned to customer's tenant
  - Requires auth, validates `role=CUSTOMER`
- [ ] **4.2.3** `GET /portal/documents/{id}` - Get document if allowed
- [ ] **4.2.4** `GET /portal/documents/{id}/download/{attachment_id}` - Download attachment

### 4.3 Create Portal Feedback Endpoint
**File**: Create `v2/backend/app/api/portal/feedback.py`

- [ ] **4.3.1** `POST /portal/feedback` - Submit feedback on document
- [ ] **4.3.2** `GET /portal/feedback` - List own submitted feedback
- [ ] **4.3.3** `GET /portal/feedback/{id}` - Get feedback with response

### 4.4 Create Portal Schemas
**File**: Create `v2/backend/app/schemas/portal.py`

- [ ] **4.4.1** `PortalDocumentResponse` - Customer-safe document view
- [ ] **4.4.2** `FeedbackCreate` - Submit feedback
- [ ] **4.4.3** `FeedbackResponse` - Feedback with status/response

### 4.5 Register Portal Router
**File**: `v2/backend/app/main.py`

- [ ] **4.5.1** Import portal routers
- [ ] **4.5.2** Add both portal routers with prefix

### 4.6 Create Customer Layout Component
**File**: Create `v2/frontend/src/layouts/CustomerLayout.tsx`

- [ ] **4.6.1** Simplified header (company logo, user menu)
- [ ] **4.6.2** Minimal sidebar (Documents, My Feedback, Profile)
- [ ] **4.6.3** No admin navigation items

### 4.7 Create Customer Dashboard
**File**: Create `v2/frontend/src/pages/portal/CustomerDashboard.tsx`

- [ ] **4.7.1** Welcome message with company name
- [ ] **4.7.2** Recent documents grid
- [ ] **4.7.3** Quick access to feedback
- [ ] **4.7.4** Announcements section (optional)

### 4.8 Create Customer Documents Page
**File**: Create `v2/frontend/src/pages/portal/CustomerDocumentsPage.tsx`

- [ ] **4.8.1** List of accessible documents
- [ ] **4.8.2** Search within allowed docs
- [ ] **4.8.3** Category filter
- [ ] **4.8.4** Download buttons for attachments

### 4.9 Create Customer Document View
**File**: Create `v2/frontend/src/pages/portal/CustomerDocumentPage.tsx`

- [ ] **4.9.1** Read-only document viewer
- [ ] **4.9.2** Attachment download list
- [ ] **4.9.3** Feedback form at bottom
- [ ] **4.9.4** Related documents section

### 4.10 Create Feedback Form Component
**File**: Create `v2/frontend/src/components/FeedbackForm.tsx`

- [ ] **4.10.1** Feedback type selector (Question, Suggestion, Issue, Other)
- [ ] **4.10.2** Text area for content
- [ ] **4.10.3** Submit button with loading state
- [ ] **4.10.4** Success/error messages

### 4.11 Create My Feedback Page
**File**: Create `v2/frontend/src/pages/portal/MyFeedbackPage.tsx`

- [ ] **4.11.1** List of submitted feedback
- [ ] **4.11.2** Status badges (Pending, Responded, Closed)
- [ ] **4.11.3** View response in modal/expansion

### 4.12 Add Customer Routes
**File**: `v2/frontend/src/App.tsx`

- [ ] **4.12.1** Add customer portal routes:
```tsx
<Route path="/portal" element={<CustomerRoute><CustomerLayout /></CustomerRoute>}>
  <Route index element={<Navigate to="/portal/dashboard" />} />
  <Route path="dashboard" element={<CustomerDashboard />} />
  <Route path="documents" element={<CustomerDocumentsPage />} />
  <Route path="documents/:id" element={<CustomerDocumentPage />} />
  <Route path="feedback" element={<MyFeedbackPage />} />
</Route>
```

### 4.13 Create CustomerRoute Guard
**File**: Create `v2/frontend/src/components/guards/CustomerRoute.tsx`

- [ ] **4.13.1** Check if user is logged in
- [ ] **4.13.2** Check if user role is `customer`
- [ ] **4.13.3** Redirect to appropriate portal if wrong role

---

## Step 5: Create Company Management - Admin (4-5 hrs)

### 5.1 Create Companies API Endpoint
**File**: Create `v2/backend/app/api/management/companies.py`

- [ ] **5.1.1** `GET /companies` - List all companies (admin+)
- [ ] **5.1.2** `POST /companies` - Create company
- [ ] **5.1.3** `GET /companies/{id}` - Get company details
- [ ] **5.1.4** `PUT /companies/{id}` - Update company
- [ ] **5.1.5** `DELETE /companies/{id}` - Soft delete company
- [ ] **5.1.6** `GET /companies/{id}/users` - List company users
- [ ] **5.1.7** `POST /companies/{id}/users` - Add user to company
- [ ] **5.1.8** `DELETE /companies/{id}/users/{user_id}` - Remove user

### 5.2 Create Company Schemas
**File**: Create `v2/backend/app/schemas/company.py`

- [ ] **5.2.1** `CompanyCreate` - name, slug, contact_email, company_type
- [ ] **5.2.2** `CompanyUpdate` - All optional fields
- [ ] **5.2.3** `CompanyResponse` - Full details + user count
- [ ] **5.2.4** `CompanyUserAdd` - user_id or email + role

### 5.3 Register Companies Router
**File**: `v2/backend/app/main.py`

- [ ] **5.3.1** Import and register companies router

### 5.4 Create Companies Page
**File**: Create `v2/frontend/src/pages/admin/CompaniesPage.tsx`

- [ ] **5.4.1** Table with company list
- [ ] **5.4.2** Add Company button → modal
- [ ] **5.4.3** Edit/Delete actions
- [ ] **5.4.4** Click row → company detail
- [ ] **5.4.5** Search/filter by name, type, status

### 5.5 Create Company Form Component
**File**: Create `v2/frontend/src/components/CompanyForm.tsx`

- [ ] **5.5.1** Fields: name, slug (auto-generate), contact_email, type
- [ ] **5.5.2** Logo upload (optional)
- [ ] **5.5.3** Active toggle
- [ ] **5.5.4** Validation

### 5.6 Create Company Detail Page
**File**: Create `v2/frontend/src/pages/admin/CompanyDetailPage.tsx`

- [ ] **5.6.1** Company info header
- [ ] **5.6.2** Users tab - list + add/remove
- [ ] **5.6.3** Documents tab - assigned documents
- [ ] **5.6.4** Activity tab (optional)

### 5.7 Create Company API Functions
**File**: `v2/frontend/src/lib/api.ts`

- [ ] **5.7.1** `fetchCompanies()`, `createCompany()`, `updateCompany()`, `deleteCompany()`
- [ ] **5.7.2** `fetchCompanyUsers()`, `addCompanyUser()`, `removeCompanyUser()`

### 5.8 Add Admin Routes
**File**: `v2/frontend/src/App.tsx`

- [ ] **5.8.1** Add `/admin/companies` route
- [ ] **5.8.2** Add `/admin/companies/:id` route

---

## Step 6: Update Document Management (4-5 hrs)

### 6.1 Update Document Schemas
**File**: `v2/backend/app/schemas/__init__.py`

- [ ] **6.1.1** Add `visibility` to `DocumentCreate`
- [ ] **6.1.2** Add `visibility` to `DocumentUpdate`
- [ ] **6.1.3** Add `visibility` and `assigned_companies` to `DocumentResponse`

### 6.2 Create Company Assignment Endpoint
**File**: `v2/backend/app/api/management/documents.py`

- [ ] **6.2.1** `POST /documents/{id}/assign-companies` - Assign companies
- [ ] **6.2.2** `DELETE /documents/{id}/assign-companies/{company_id}` - Remove assignment
- [ ] **6.2.3** `GET /documents/{id}/assigned-companies` - List assignments

### 6.3 Update Document Service
**File**: Create/update `v2/backend/app/services/document_service.py`

- [ ] **6.3.1** Update `get_documents` to filter by visibility based on user role
- [ ] **6.3.2** Add `assign_company_to_document()` function
- [ ] **6.3.3** Add `get_documents_for_company()` function

### 6.4 Add Visibility Selector to Form
**File**: Update document form component in frontend

- [ ] **6.4.1** Add visibility dropdown: Public, Internal, Company
- [ ] **6.4.2** Show company selector when "Company" is selected
- [ ] **6.4.3** Multi-select for companies

### 6.5 Create VisibilityBadge Component
**File**: Create `v2/frontend/src/components/VisibilityBadge.tsx`

- [ ] **6.5.1** Color-coded badge: 🌐 Public (green), 🏢 Internal (blue), 🔒 Company (orange)
- [ ] **6.5.2** Tooltip with details

### 6.6 Create CompanySelector Component
**File**: Create `v2/frontend/src/components/CompanySelector.tsx`

- [ ] **6.6.1** Multi-select dropdown with company search
- [ ] **6.6.2** Show selected companies as chips
- [ ] **6.6.3** Remove chip to unassign

### 6.7 Update Documents Page
**File**: `v2/frontend/src/pages/DocumentsPage.tsx`

- [ ] **6.7.1** Add visibility column to table
- [ ] **6.7.2** Add visibility filter dropdown
- [ ] **6.7.3** Show assigned companies count

### 6.8 Update Document Detail Page
**File**: `v2/frontend/src/pages/DocumentDetailPage.tsx`

- [ ] **6.8.1** Show visibility badge
- [ ] **6.8.2** Add "Assign Companies" button (if visibility=COMPANY)
- [ ] **6.8.3** List assigned companies with remove option

---

## Step 7: Implement Review/Approval Workflow (4-5 hrs)

### 7.1 Create Reviews API Router
**File**: Create `v2/backend/app/api/management/reviews.py`

- [ ] **7.1.1** `POST /documents/{id}/submit-review` - Submit doc for review
- [ ] **7.1.2** `GET /reviews/pending` - List pending reviews (for reviewer)
- [ ] **7.1.3** `GET /reviews/my-submissions` - List own submissions
- [ ] **7.1.4** `POST /reviews/{id}/approve` - Approve with optional comment
- [ ] **7.1.5** `POST /reviews/{id}/reject` - Reject with required comment
- [ ] **7.1.6** `POST /reviews/{id}/cancel` - Cancel own submission

### 7.2 Create Review Service
**File**: Create `v2/backend/app/services/review_service.py`

- [ ] **7.2.1** `submit_for_review(document_id, user)` - Create ReviewRequest
- [ ] **7.2.2** `get_pending_reviews(user)` - Filter by reviewer permissions
- [ ] **7.2.3** `can_review(user, review)` - Check: not self, has permission
- [ ] **7.2.4** `approve_review(review_id, reviewer, comments)`
- [ ] **7.2.5** `reject_review(review_id, reviewer, comments)`
- [ ] **7.2.6** Implement peer review logic (editors can review other editors)

### 7.3 Create Review Schemas
**File**: Create `v2/backend/app/schemas/review.py`

- [ ] **7.3.1** `ReviewSubmit` - version_id (optional), message
- [ ] **7.3.2** `ReviewAction` - comments (required for reject)
- [ ] **7.3.3** `ReviewResponse` - Full review with document info

### 7.4 Add Document Status: PENDING_REVIEW
**File**: `v2/backend/app/models/__init__.py`

- [ ] **7.4.1** Add `PENDING_REVIEW = "pending_review"` to DocumentStatus enum

### 7.5 Create Pending Reviews Page
**File**: Create `v2/frontend/src/pages/ReviewsPage.tsx`

- [ ] **7.5.1** Tabs: "Pending My Review" | "My Submissions"
- [ ] **7.5.2** Table with document title, submitter, submitted date
- [ ] **7.5.3** Quick actions: View, Approve, Reject

### 7.6 Create ReviewDialog Component
**File**: Create `v2/frontend/src/components/ReviewDialog.tsx`

- [ ] **7.6.1** Show document preview
- [ ] **7.6.2** Comments text area
- [ ] **7.6.3** Approve / Reject buttons
- [ ] **7.6.4** Confirmation before action

### 7.7 Add Submit for Review Button
**File**: Update document detail page

- [ ] **7.7.1** Show "Submit for Review" button when status=DRAFT
- [ ] **7.7.2** Hide when already pending or user can't submit
- [ ] **7.7.3** Confirmation dialog

### 7.8 Add Review Status UI
**File**: Update document list/detail

- [ ] **7.8.1** Show "Pending Review" badge
- [ ] **7.8.2** Show reviewer info when assigned
- [ ] **7.8.3** Show approval/rejection history

### 7.9 Create Review Notifications
**File**: Update notification service

- [ ] **7.9.1** Notify reviewers when doc submitted
- [ ] **7.9.2** Notify submitter when approved/rejected
- [ ] **7.9.3** Add REVIEW_SUBMITTED, REVIEW_APPROVED, REVIEW_REJECTED to NotificationType

### 7.10 Add Reviews Route
**File**: `v2/frontend/src/App.tsx`

- [ ] **7.10.1** Add `/reviews` route for internal users

---

## Step 8: Implement Feedback System (3-4 hrs)

### 8.1 Create Feedback Management API
**File**: Create `v2/backend/app/api/management/feedback.py`

- [ ] **8.1.1** `GET /feedback` - List all feedback (admin+)
- [ ] **8.1.2** `GET /feedback/{id}` - Get feedback details
- [ ] **8.1.3** `POST /feedback/{id}/respond` - Add response
- [ ] **8.1.4** `PUT /feedback/{id}/status` - Update status

### 8.2 Create Feedback Service
**File**: Create `v2/backend/app/services/feedback_service.py`

- [ ] **8.2.1** `get_feedback_list(filters)` - Filter by status, type, company
- [ ] **8.2.2** `respond_to_feedback(feedback_id, response, responder)`
- [ ] **8.2.3** `close_feedback(feedback_id)`

### 8.3 Create Feedback Management Page
**File**: Create `v2/frontend/src/pages/admin/FeedbackPage.tsx`

- [ ] **8.3.1** Table with feedback list
- [ ] **8.3.2** Filters: status, type, company, date range
- [ ] **8.3.3** Click to open response dialog

### 8.4 Create FeedbackResponseDialog
**File**: Create `v2/frontend/src/components/FeedbackResponseDialog.tsx`

- [ ] **8.4.1** Show original feedback + document link
- [ ] **8.4.2** Response text area
- [ ] **8.4.3** Status selector
- [ ] **8.4.4** Send response + notify customer

### 8.5 Create Feedback Notifications
**File**: Update notification service

- [ ] **8.5.1** Notify admins when new feedback received
- [ ] **8.5.2** Notify customer when feedback responded
- [ ] **8.5.3** Add FEEDBACK_RECEIVED, FEEDBACK_RESPONDED to NotificationType

### 8.6 Add Feedback Route
**File**: `v2/frontend/src/App.tsx`

- [ ] **8.6.1** Add `/admin/feedback` route

---

## Step 9: Update User Management (3-4 hrs)

### 9.1 Update User Creation
**File**: `v2/backend/app/api/management/users.py`

- [ ] **9.1.1** Add company assignment on create
- [ ] **9.1.2** Validate: customers MUST have company
- [ ] **9.1.3** Validate: managers can only create editors/viewers

### 9.2 Update User Schemas
**File**: `v2/backend/app/schemas/__init__.py`

- [ ] **9.2.1** Add `company_id` to UserCreate
- [ ] **9.2.2** Add `company` to UserResponse

### 9.3 Update User Form
**File**: Update user form component in frontend

- [ ] **9.3.1** Add role dropdown with all 6 roles
- [ ] **9.3.2** Show company selector when role=customer
- [ ] **9.3.3** Disable roles above current user's level

### 9.4 Update Users Page
**File**: `v2/frontend/src/pages/UsersPage.tsx`

- [ ] **9.4.1** Add role filter dropdown
- [ ] **9.4.2** Add company filter dropdown
- [ ] **9.4.3** Show company column
- [ ] **9.4.4** Color-code roles

### 9.5 Create Customer Invitation Flow
**File**: Create `v2/backend/app/api/management/invitations.py`

- [ ] **9.5.1** `POST /companies/{id}/invite` - Send email invitation
- [ ] **9.5.2** Create invitation token model
- [ ] **9.5.3** `POST /auth/accept-invitation` - Accept and set password

### 9.6 Create Invitation UI
**File**: Create `v2/frontend/src/components/InviteUserDialog.tsx`

- [ ] **9.6.1** Email input
- [ ] **9.6.2** Role selector (customer only for company invite)
- [ ] **9.6.3** Send invitation button

---

## Step 10: Update Navigation & Routing (2-3 hrs)

### 10.1 Create Role-Based Route Config
**File**: Create `v2/frontend/src/config/routes.ts`

- [ ] **10.1.1** Define route config with role requirements
- [ ] **10.1.2** Export route generator functions

### 10.2 Create RoleGuard Component
**File**: Create `v2/frontend/src/components/guards/RoleGuard.tsx`

- [ ] **10.2.1** Accept `allowedRoles` prop
- [ ] **10.2.2** Check current user role
- [ ] **10.2.3** Redirect to appropriate home if denied

### 10.3 Update Sidebar Navigation
**File**: `v2/frontend/src/components/Sidebar.tsx`

- [ ] **10.3.1** Group nav items by section
- [ ] **10.3.2** Filter items by user role
- [ ] **10.3.3** Add Reviews nav item for internal users
- [ ] **10.3.4** Add Companies, Feedback nav items for admins

### 10.4 Update App.tsx with Complete Routes
**File**: `v2/frontend/src/App.tsx`

- [ ] **10.4.1** Organize routes by portal type (public, customer, internal, admin)
- [ ] **10.4.2** Add all new routes with proper guards
- [ ] **10.4.3** Add 404 handler per portal

### 10.5 Create Role-Based Home Redirect
**File**: Update login flow

- [ ] **10.5.1** After login, redirect based on role:
  - customer → `/portal/dashboard`
  - editor/manager → `/dashboard`
  - admin → `/admin` or `/dashboard`

---

## Step 11: Testing (4-5 hrs)

### 11.1 Backend Unit Tests
**File**: Create tests in `v2/backend/tests/`

- [ ] **11.1.1** `test_permissions.py` - Test permission matrix
- [ ] **11.1.2** `test_review_service.py` - Test review workflow
- [ ] **11.1.3** `test_feedback_service.py` - Test feedback flow

### 11.2 API Integration Tests
**File**: Create/update `v2/backend/tests/test_api/`

- [ ] **11.2.1** `test_public_api.py` - Test public endpoints without auth
- [ ] **11.2.2** `test_portal_api.py` - Test customer portal endpoints
- [ ] **11.2.3** `test_companies_api.py` - Test company management
- [ ] **11.2.4** `test_reviews_api.py` - Test review workflow

### 11.3 Role-Based Access Tests
**File**: Create `v2/backend/tests/test_roles.py`

- [ ] **11.3.1** Test each role can only access allowed endpoints
- [ ] **11.3.2** Test role escalation prevention
- [ ] **11.3.3** Test company isolation (customer A can't see customer B docs)

### 11.4 Frontend E2E Tests
**File**: Create tests in `v2/frontend/tests/`

- [ ] **11.4.1** `public-portal.spec.ts` - Test anonymous browsing
- [ ] **11.4.2** `customer-portal.spec.ts` - Test customer flow
- [ ] **11.4.3** `review-workflow.spec.ts` - Test submit/approve/reject
- [ ] **11.4.4** `company-management.spec.ts` - Test company CRUD

### 11.5 Security Tests
**File**: Create `v2/backend/tests/test_security.py`

- [ ] **11.5.1** Test JWT token with wrong role is rejected
- [ ] **11.5.2** Test customer can't access internal docs
- [ ] **11.5.3** Test cross-company document access denied

---

## File Structure After Implementation

```
v2/
├── backend/app/
│   ├── api/
│   │   ├── public/                    # NEW
│   │   │   ├── __init__.py
│   │   │   └── documents.py
│   │   ├── portal/                    # NEW
│   │   │   ├── __init__.py
│   │   │   ├── documents.py
│   │   │   └── feedback.py
│   │   ├── management/
│   │   │   ├── companies.py           # NEW
│   │   │   ├── reviews.py             # NEW
│   │   │   ├── feedback.py            # NEW
│   │   │   └── invitations.py         # NEW
│   │   └── admin/                     # NEW
│   │       └── settings.py
│   ├── services/
│   │   ├── permissions.py             # NEW
│   │   ├── review_service.py          # NEW
│   │   └── feedback_service.py        # NEW
│   ├── dependencies/
│   │   └── permissions.py             # NEW
│   ├── schemas/
│   │   ├── public.py                  # NEW
│   │   ├── portal.py                  # NEW
│   │   ├── company.py                 # NEW
│   │   └── review.py                  # NEW
│   └── models/
│       └── __init__.py                # UPDATED
│
└── frontend/src/
    ├── layouts/                       # NEW
    │   ├── PublicLayout.tsx
    │   ├── CustomerLayout.tsx
    │   └── AdminLayout.tsx
    ├── pages/
    │   ├── public/                    # NEW
    │   │   ├── PublicHomePage.tsx
    │   │   ├── PublicDocumentsPage.tsx
    │   │   └── PublicDocumentPage.tsx
    │   ├── portal/                    # NEW
    │   │   ├── CustomerDashboard.tsx
    │   │   ├── CustomerDocumentsPage.tsx
    │   │   ├── CustomerDocumentPage.tsx
    │   │   └── MyFeedbackPage.tsx
    │   ├── admin/                     # NEW
    │   │   ├── CompaniesPage.tsx
    │   │   ├── CompanyDetailPage.tsx
    │   │   └── FeedbackPage.tsx
    │   └── ReviewsPage.tsx            # NEW
    ├── components/
    │   ├── guards/                    # NEW
    │   │   ├── RoleGuard.tsx
    │   │   └── CustomerRoute.tsx
    │   ├── FeedbackForm.tsx           # NEW
    │   ├── FeedbackResponseDialog.tsx # NEW
    │   ├── ReviewDialog.tsx           # NEW
    │   ├── CompanyForm.tsx            # NEW
    │   ├── CompanySelector.tsx        # NEW
    │   ├── VisibilityBadge.tsx        # NEW
    │   └── InviteUserDialog.tsx       # NEW
    ├── config/
    │   └── routes.ts                  # NEW
    └── lib/
        ├── api.ts                     # UPDATED
        └── auth.tsx                   # UPDATED
```

---

## Timeline Summary

| Step | Description | Time | Dependencies | Status |
|------|-------------|------|--------------|--------|
| 1 | Database Models & Roles | 3-4 hrs | None | ⬜ |
| 2 | Permission System | 4-5 hrs | Step 1 | ⬜ |
| 3 | Public Portal | 5-6 hrs | Step 2 | ⬜ |
| 4 | Customer Portal | 5-6 hrs | Step 2, 3 | ⬜ |
| 5 | Company Management | 4-5 hrs | Step 1, 2 | ⬜ |
| 6 | Document Visibility | 4-5 hrs | Step 1, 2, 5 | ⬜ |
| 7 | Review Workflow | 4-5 hrs | Step 2 | ⬜ |
| 8 | Feedback System | 3-4 hrs | Step 4 | ⬜ |
| 9 | User Management | 3-4 hrs | Step 1, 2, 5 | ⬜ |
| 10 | Navigation & Routing | 2-3 hrs | All above | ⬜ |
| 11 | Testing | 4-5 hrs | All above | ⬜ |
| **Total** | | **42-52 hrs** | | |

---

## Considerations

1. **Email Service**: Do you want email notifications for invitations/feedback responses? If yes, we need to add an email service (SendGrid, AWS SES, etc.)

2. **Document Versioning on Approval**: Should approval be tied to a specific version, or just the document? Currently planned for version-optional.

3. **Customer Self-Registration**: Should customers be able to request access, or invitation-only? Currently planned as invitation-only.

---

## Progress Log

| Date | Step | Sub-steps | Notes |
|------|------|-----------|-------|
| | | | |

---

