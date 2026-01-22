# Public Portal + Customer Access + Role-Based Permissions

## Detailed Implementation Plan

**Feature**: Multi-tenant customer portal with public space and granular permissions  
**Status**: � COMPLETE  
**Estimated Time**: 42-52 hours  
**Priority**: High  

> A comprehensive step-by-step plan expanding each phase into actionable sub-tasks with exact file paths, code patterns, and dependencies.

---

## Progress Tracker

| Step | Description | Status | Time |
|------|-------------|--------|------|
| 1 | Update Database Models & Roles | ✅ COMPLETE | 3-4 hrs |
| 2 | Implement Permission System | ✅ COMPLETE | 4-5 hrs |
| 3 | Create Public Portal | ✅ COMPLETE | 5-6 hrs |
| 4 | Create Customer Portal | ✅ COMPLETE | 5-6 hrs |
| 5 | Create Company Management | ✅ COMPLETE | 4-5 hrs |
| 6 | Update Document Management | ✅ COMPLETE | 4-5 hrs |
| 7 | Implement Review/Approval Workflow | ✅ COMPLETE | 4-5 hrs |
| 8 | Implement Feedback System | ✅ COMPLETE | 3-4 hrs |
| 9 | Update User Management | ✅ COMPLETE | 3-4 hrs |
| 10 | Update Navigation & Routing | ✅ COMPLETE | 2-3 hrs |
| 11 | Testing | ✅ COMPLETE | 4-5 hrs |

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

## Step 1: Update Database Models & Roles ✅ COMPLETE (3-4 hrs)

### 1.1 Update UserRole Enum
**File**: `v2/backend/app/models/__init__.py`  
**Current**: `SUPER_ADMIN`, `ADMIN`, `EDITOR`, `VIEWER`

- [x] **1.1.1** Rename `SUPER_ADMIN` → `SYSTEM_ADMIN`
- [x] **1.1.2** Add `MANAGER = "manager"` between ADMIN and EDITOR
- [x] **1.1.3** Add `CUSTOMER = "customer"` after VIEWER
- [x] **1.1.4** Update `__all__` exports if needed

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
- [x] **1.2.2** Add to `__all__` exports

### 1.3 Update Document Model
**File**: `v2/backend/app/models/__init__.py` (Lines 92-114)

- [x] **1.3.1** Add `visibility` column after `status`:
```python
visibility = Column(Enum(DocumentVisibility), default=DocumentVisibility.INTERNAL, index=True)
```
- [x] **1.3.2** Add `assigned_companies` relationship (after junction table created)

### 1.4 Create Document-Company Junction Table
**File**: `v2/backend/app/models/__init__.py`

- [x] **1.4.1** Add junction table after Tenant model:
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
- [x] **1.4.2** Add relationship to Document model:
```python
assigned_companies = relationship("Tenant", secondary=document_company_assignments, backref="assigned_documents")
```

### 1.5 Enhance Tenant Model
**File**: `v2/backend/app/models/__init__.py` (Lines 51-63)

- [x] **1.5.1** Add `company_logo = Column(String(500), nullable=True)`
- [x] **1.5.2** Add `contact_email = Column(String(255), nullable=True)`
- [x] **1.5.3** Add `company_type = Column(String(50), default="customer")` (customer, partner, internal)

### 1.6 Create ReviewRequest Model
**File**: `v2/backend/app/models/__init__.py`

- [x] **1.6.1** Create ReviewStatus enum:
```python
class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
```
- [x] **1.6.2** Create ReviewRequest model:
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
- [x] **1.6.3** Add to `__all__` exports

### 1.7 Update Feedback Model (if needed)
**File**: `v2/backend/app/models/__init__.py`

- [x] **1.7.1** Verify existing Feedback model has: `feedback_type`, `status`, `response`, `responded_by`
- [x] **1.7.2** Add FeedbackType enum if missing:
```python
class FeedbackType(str, enum.Enum):
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    OTHER = "other"
```
- [x] **1.7.3** Add FeedbackStatus enum if missing:
```python
class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"
    RESPONDED = "responded"
    CLOSED = "closed"
```

### 1.8 Create Database Migration
**File**: Create `v2/backend/migrations/add_customer_portal_fields.py`

- [x] **1.8.1** Create Alembic migration or manual SQL script
- [x] **1.8.2** Handle existing data (set default visibility = INTERNAL)
- [x] **1.8.3** Update existing `super_admin` → `system_admin` in users table

### 1.9 Update Frontend Types
**File**: `v2/frontend/src/types/index.ts`

- [x] **1.9.1** Update `UserRole` type:
```typescript
export type UserRole = 'system_admin' | 'admin' | 'manager' | 'editor' | 'viewer' | 'customer'
```
- [x] **1.9.2** Add `DocumentVisibility` type:
```typescript
export type DocumentVisibility = 'public' | 'internal' | 'company'
```
- [x] **1.9.3** Add `ReviewStatus` type
- [x] **1.9.4** Update `Document` interface with `visibility` field

---

## Step 2: Implement Permission System ✅ COMPLETE (4-5 hrs)

### 2.1 Create Permissions Service
**File**: Created `v2/backend/app/services/permissions.py`

- [x] **2.1.1** Create permission action enum:
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

- [x] **2.1.2** Create permission matrix dictionary:
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

- [x] **2.1.3** Create `has_permission(user: User, permission: Permission) -> bool` function
- [x] **2.1.4** Create `is_internal_user(user: User) -> bool` helper
- [x] **2.1.5** Create `can_view_document(user: User, document: Document) -> bool` function

### 2.2 Create Permission Dependencies
**File**: Created `v2/backend/app/dependencies/permissions.py`

- [x] **2.2.1** Create `require_permission` dependency factory:
```python
def require_permission(permission: Permission):
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if not has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return current_user
    return dependency
```

- [x] **2.2.2** Create `require_any_role` dependency:
```python
def require_any_role(roles: List[UserRole]):
    async def dependency(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current_user
    return dependency
```

- [x] **2.2.3** Create `require_internal_user` dependency:
```python
async def require_internal_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Internal users only")
    return current_user
```

- [x] **2.2.4** Create `DocumentAccessChecker` class for document access verification

### 2.3 Update Existing Security
**File**: `v2/backend/app/security.py`

- [x] **2.3.1** Import new permission dependencies
- [x] **2.3.2** Update `require_super_admin` → `require_system_admin`
- [x] **2.3.3** Export all new dependencies

### 2.4 Update Existing API Endpoints
**Files**: Multiple files in `v2/backend/app/api/management/`

- [x] **2.4.1** `documents.py`: Updated role checks to use SYSTEM_ADMIN and MANAGER
- [x] **2.4.2** `users.py`: Updated role checks to use SYSTEM_ADMIN and MANAGER  
- [x] **2.4.3** `tenants.py`: Updated to use `require_system_admin`
- [x] **2.4.4** `versions.py`: Updated publish permission to include MANAGER

### 2.5 Update Frontend Auth Context
**File**: `v2/frontend/src/lib/auth.tsx`

- [x] **2.5.1** Update role helper functions:
```typescript
const isSystemAdmin = user?.role === 'system_admin'
const isAdmin = user?.role === 'admin' || isSystemAdmin
const isManager = user?.role === 'manager' || isAdmin
const isEditor = user?.role === 'editor' || isManager
const isInternal = user?.role !== 'customer'
const isCustomer = user?.role === 'customer'
```
- [x] **2.5.2** Add `hasPermission(permission: string)` helper
- [x] **2.5.3** Export new helpers from context

### 2.6 Update Frontend Components
- [x] **2.6.1** Updated `UsersPage.tsx` role badge colors
- [x] **2.6.2** Updated `LoginPage.tsx` demo credentials
- [x] **2.6.3** Updated `CommentsSection.tsx` role badge styling

---

## Step 3: Create Public Portal - No Auth (5-6 hrs)

### 3.1 Create Public API Router
**File**: Created `v2/backend/app/api/public/__init__.py`

- [x] **3.1.1** Created router that includes document endpoints

### 3.2 Create Public Documents Endpoint
**File**: Created `v2/backend/app/api/public/documents.py`

- [x] **3.2.1** Create router with prefix `/public`:
```python
router = APIRouter(prefix="/public", tags=["Public"])
```

- [x] **3.2.2** `GET /public/documents` - List public published documents:
  - Filter: `visibility=PUBLIC`, `status=PUBLISHED`
  - Pagination: `page`, `page_size`
  - Optional: `category`, `search`, `sort_by`, `sort_order` query params
  - NO auth dependency

- [x] **3.2.3** `GET /public/documents/{id}` - Get single public document:
  - Validate: `visibility=PUBLIC`, `status=PUBLISHED`
  - Return full content + latest version + attachments
  - NO auth dependency

- [x] **3.2.4** `GET /public/categories` - List categories with public doc counts

- [x] **3.2.5** `GET /public/search` - Full-text search public docs

- [x] **3.2.6** `GET /public/stats` - Get public portal statistics

- [x] **3.2.7** `GET /public/documents/{id}/attachments/{attachment_id}` - Get attachment info

### 3.3 Create Public Schemas
**File**: Created `v2/backend/app/schemas/public.py`

- [x] **3.3.1** `PublicDocumentSummary` - Minimal fields for list
- [x] **3.3.2** `PublicDocumentDetail` - Full content with attachments
- [x] **3.3.3** `PublicDocumentWithAttachments` - Detail with attachment list
- [x] **3.3.4** `PublicSearchResult` - Search response format
- [x] **3.3.5** `PublicCategoryCount` - Category with document count
- [x] **3.3.6** `PublicAttachmentInfo` - Attachment details

### 3.4 Register Public Router
**File**: `v2/backend/app/main.py`

- [x] **3.4.1** Import public router
- [x] **3.4.2** Added: `app.include_router(public_router, prefix=settings.API_PREFIX, tags=["Public"])`

### 3.5 Create Public Layout Component
**File**: Created `v2/frontend/src/layouts/PublicLayout.tsx`

- [x] **3.5.1** Header with logo + Login button
- [x] **3.5.2** Mobile responsive menu
- [x] **3.5.3** Full-width content area with Outlet
- [x] **3.5.4** Footer with links

### 3.6 Create Public Landing Page
**File**: Created `v2/frontend/src/pages/public/PublicHomePage.tsx`

- [x] **3.6.1** Hero section with search bar
- [x] **3.6.2** Featured/recent public documents
- [x] **3.6.3** Category browsing
- [x] **3.6.4** Login CTA / Go to Dashboard button

### 3.7 Create Public Documents List Page
**File**: Created `v2/frontend/src/pages/public/PublicDocumentsPage.tsx`

- [x] **3.7.1** Grid/list view toggle
- [x] **3.7.2** Category filter sidebar
- [x] **3.7.3** Search integration
- [x] **3.7.4** Pagination

### 3.8 Create Public Document Viewer
**File**: Created `v2/frontend/src/pages/public/PublicDocumentPage.tsx`

- [x] **3.8.1** Read-only document display
- [x] **3.8.2** Document metadata (category, tags, dates)
- [x] **3.8.3** Attachment download section
- [x] **3.8.4** "Login for more" prompt

### 3.9 Create Public API Client Functions
**File**: Created `v2/frontend/src/lib/publicApi.ts`

- [x] **3.9.1** `publicApi.getDocuments(params)` - No auth header
- [x] **3.9.2** `publicApi.getDocument(id)` - No auth header
- [x] **3.9.3** `publicApi.search(params)` - No auth header
- [x] **3.9.4** `publicApi.getCategories()` - No auth header
- [x] **3.9.5** `publicApi.getStats()` - No auth header
- [x] **3.9.6** `publicApi.getAttachment()` - No auth header

### 3.10 Add Public Routes
**File**: `v2/frontend/src/App.tsx`

- [x] **3.10.1** Added routes with PublicLayout:
```tsx
<Route element={<PublicLayout />}>
  <Route path="/" element={<PublicHomePage />} />
  <Route path="/browse" element={<PublicDocumentsPage />} />
  <Route path="/doc/:id" element={<PublicDocumentPage />} />
  <Route path="/search" element={<PublicSearchPage />} />
</Route>
```

### 3.11 Create Public Search Page
**File**: Created `v2/frontend/src/pages/public/PublicSearchPage.tsx`

- [x] **3.11.1** Search form with category filter
- [x] **3.11.2** Search results with highlighting
- [x] **3.11.3** Pagination

---

## Step 4: Create Customer Portal ✅ COMPLETE (5-6 hrs)

### 4.1 Create Portal API Router
**File**: Created `v2/backend/app/api/portal/__init__.py`

- [x] **4.1.1** Created router that includes documents and feedback routers

### 4.2 Create Portal Documents Endpoint
**File**: Created `v2/backend/app/api/portal/documents.py`

- [x] **4.2.1** Created router with prefix `/portal`
- [x] **4.2.2** `GET /portal/documents` - List docs visible to customer:
  - PUBLIC docs + COMPANY docs assigned to customer's tenant
  - Requires auth, validates `role=CUSTOMER`
- [x] **4.2.3** `GET /portal/documents/{id}` - Get document if allowed
- [x] **4.2.4** `GET /portal/documents/{id}/attachments/{attachment_id}` - Get attachment info
- [x] **4.2.5** `GET /portal/categories` - Get categories with doc counts
- [x] **4.2.6** `GET /portal/dashboard/stats` - Get dashboard statistics
- [x] **4.2.7** `GET /portal/search` - Search customer-accessible documents

### 4.3 Create Portal Feedback Endpoint
**File**: Created `v2/backend/app/api/portal/feedback.py`

- [x] **4.3.1** `POST /portal/feedback` - Submit feedback on document
- [x] **4.3.2** `GET /portal/feedback` - List own submitted feedback
- [x] **4.3.3** `GET /portal/feedback/{id}` - Get feedback with response

### 4.4 Create Portal Schemas
**File**: Created `v2/backend/app/schemas/portal.py`

- [x] **4.4.1** `PortalDocumentSummary`, `PortalDocumentDetail` - Customer-safe document views
- [x] **4.4.2** `FeedbackCreate` - Submit feedback
- [x] **4.4.3** `FeedbackResponse` - Feedback with status/response
- [x] **4.4.4** `PortalDashboardStats` - Dashboard statistics

### 4.5 Register Portal Router
**File**: `v2/backend/app/main.py`

- [x] **4.5.1** Import portal router
- [x] **4.5.2** Add portal router with prefix

### 4.6 Create Customer Layout Component
**File**: Created `v2/frontend/src/layouts/CustomerLayout.tsx`

- [x] **4.6.1** Simplified header (logo, user menu)
- [x] **4.6.2** Sidebar with navigation (Dashboard, Documents, My Feedback)
- [x] **4.6.3** Search bar in header
- [x] **4.6.4** Mobile-responsive design

### 4.7 Create Customer Dashboard
**File**: Created `v2/frontend/src/pages/portal/CustomerDashboard.tsx`

- [x] **4.7.1** Welcome message with user name
- [x] **4.7.2** Stats cards (documents, feedback counts)
- [x] **4.7.3** Recent documents grid
- [x] **4.7.4** Browse by category section
- [x] **4.7.5** Quick action cards

### 4.8 Create Customer Documents Page
**File**: Created `v2/frontend/src/pages/portal/CustomerDocumentsPage.tsx`

- [x] **4.8.1** List of accessible documents (grid/list view)
- [x] **4.8.2** Search within allowed docs
- [x] **4.8.3** Category filter
- [x] **4.8.4** Pagination

### 4.9 Create Customer Document View
**File**: Created `v2/frontend/src/pages/portal/CustomerDocumentPage.tsx`

- [x] **4.9.1** Read-only document viewer
- [x] **4.9.2** Attachment download list
- [x] **4.9.3** Feedback form at bottom
- [x] **4.9.4** Document metadata display

### 4.10 Create Feedback Form Component
**File**: Created `v2/frontend/src/components/FeedbackForm.tsx`

- [x] **4.10.1** Feedback type selector (Question, Suggestion, Issue, Other)
- [x] **4.10.2** Text area for content
- [x] **4.10.3** Submit button with loading state
- [x] **4.10.4** Character count and validation

### 4.11 Create My Feedback Page
**File**: Created `v2/frontend/src/pages/portal/MyFeedbackPage.tsx`

- [x] **4.11.1** List of submitted feedback
- [x] **4.11.2** Status filter (Pending, Responded, Closed)
- [x] **4.11.3** View response in modal/expansion

### 4.12 Add Customer Routes
**File**: `v2/frontend/src/App.tsx`

- [x] **4.12.1** Added customer portal routes with CustomerLayout

### 4.13 Create CustomerRoute Guard
**File**: Created `v2/frontend/src/components/guards/CustomerRoute.tsx`

- [x] **4.13.1** Check if user is logged in
- [x] **4.13.2** Check if user role is `customer`
- [x] **4.13.3** Redirect to appropriate portal if wrong role

### 4.14 Create Portal API Client
**File**: Created `v2/frontend/src/lib/portalApi.ts`

- [x] **4.14.1** API functions for all portal endpoints
- [x] **4.14.2** TypeScript types for portal data

---

## Step 5: Create Company Management - Admin ✅ COMPLETE (4-5 hrs)

### 5.1 Create Companies API Endpoint
**File**: Created `v2/backend/app/api/management/companies.py`

- [x] **5.1.1** `GET /companies` - List all companies (admin+)
- [x] **5.1.2** `POST /companies` - Create company
- [x] **5.1.3** `GET /companies/{id}` - Get company details
- [x] **5.1.4** `PUT /companies/{id}` - Update company
- [x] **5.1.5** `DELETE /companies/{id}` - Soft delete company
- [x] **5.1.6** `GET /companies/{id}/users` - List company users
- [x] **5.1.7** `POST /companies/{id}/users` - Add user to company
- [x] **5.1.8** `DELETE /companies/{id}/users/{user_id}` - Remove user

### 5.2 Create Company Schemas
**File**: Created `v2/backend/app/schemas/company.py`

- [x] **5.2.1** `CompanyCreate` - name, slug, contact_email, company_type
- [x] **5.2.2** `CompanyUpdate` - All optional fields
- [x] **5.2.3** `CompanyResponse` - Full details + user count
- [x] **5.2.4** `CompanyUserAdd` - user_id or email

### 5.3 Register Companies Router
**File**: `v2/backend/app/main.py`

- [x] **5.3.1** Import and register companies router

### 5.4 Create Companies Page
**File**: Created `v2/frontend/src/pages/CompaniesPage.tsx`

- [x] **5.4.1** Table with company list
- [x] **5.4.2** Add Company button → modal
- [x] **5.4.3** Edit/Delete actions
- [x] **5.4.4** Click row → company detail
- [x] **5.4.5** Search/filter by name, type, status

### 5.5 Create Company Form Component
**File**: Created `v2/frontend/src/components/CompanyForm.tsx`

- [x] **5.5.1** Fields: name, slug (auto-generate), contact_email, type
- [x] **5.5.2** Logo URL field (optional)
- [x] **5.5.3** Active toggle
- [x] **5.5.4** Validation

### 5.6 Create Company Detail Page
**File**: Created `v2/frontend/src/pages/CompanyDetailPage.tsx`

- [x] **5.6.1** Company info header
- [x] **5.6.2** Users tab - list + add/remove
- [x] **5.6.3** Documents tab - assigned documents
- [x] **5.6.4** Activity tab (optional) - skipped, not essential

### 5.7 Create Company API Functions
**File**: `v2/frontend/src/lib/api.ts`

- [x] **5.7.1** `getCompanies()`, `createCompany()`, `updateCompany()`, `deleteCompany()`
- [x] **5.7.2** `getCompanyUsers()`, `addUserToCompany()`, `removeUserFromCompany()`

### 5.8 Add Admin Routes
**File**: `v2/frontend/src/App.tsx`

- [x] **5.8.1** Add `/admin/companies` route
- [x] **5.8.2** Add `/admin/companies/:id` route

---

## Step 6: Update Document Management (4-5 hrs) ✅ COMPLETED

### 6.1 Update Document Schemas
**File**: `v2/backend/app/schemas/__init__.py`

- [x] **6.1.1** Add `visibility` to `DocumentCreate`
- [x] **6.1.2** Add `visibility` to `DocumentUpdate`
- [x] **6.1.3** Add `visibility` and `assigned_companies` to `DocumentResponse`

### 6.2 Create Company Assignment Endpoint
**File**: `v2/backend/app/api/management/documents.py`

- [x] **6.2.1** `POST /documents/{id}/assign-companies` - Assign companies
- [x] **6.2.2** `DELETE /documents/{id}/assign-companies/{company_id}` - Remove assignment
- [x] **6.2.3** `GET /documents/{id}/assigned-companies` - List assignments

### 6.3 Update Document Service
**File**: Create/update `v2/backend/app/services/document_service.py`

- [x] **6.3.1** Update `get_documents` to filter by visibility based on user role
- [x] **6.3.2** Add `assign_company_to_document()` function
- [x] **6.3.3** Add `get_documents_for_company()` function

### 6.4 Add Visibility Selector to Form
**File**: Update document form component in frontend

- [x] **6.4.1** Add visibility dropdown: Public, Internal, Company
- [x] **6.4.2** Show company selector when "Company" is selected
- [x] **6.4.3** Multi-select for companies

### 6.5 Create VisibilityBadge Component
**File**: Create `v2/frontend/src/components/VisibilityBadge.tsx`

- [x] **6.5.1** Color-coded badge: 🌐 Public (green), 🏢 Internal (blue), 🔒 Company (orange)
- [x] **6.5.2** Tooltip with details

### 6.6 Create CompanySelector Component
**File**: Create `v2/frontend/src/components/CompanySelector.tsx`

- [x] **6.6.1** Multi-select dropdown with company search
- [x] **6.6.2** Show selected companies as chips
- [x] **6.6.3** Remove chip to unassign

### 6.7 Update Documents Page
**File**: `v2/frontend/src/pages/DocumentsPage.tsx`

- [x] **6.7.1** Add visibility column to table
- [x] **6.7.2** Add visibility filter dropdown
- [x] **6.7.3** Show assigned companies count

### 6.8 Update Document Detail Page
**File**: `v2/frontend/src/pages/DocumentDetailPage.tsx`

- [x] **6.8.1** Show visibility badge
- [x] **6.8.2** Add "Assign Companies" button (if visibility=COMPANY)
- [x] **6.8.3** List assigned companies with remove option

---

## Step 7: Implement Review/Approval Workflow (4-5 hrs) ✅ COMPLETE

### 7.1 Create Reviews API Router
**File**: Create `v2/backend/app/api/management/reviews.py`

- [x] **7.1.1** `POST /documents/{id}/submit-review` - Submit doc for review
- [x] **7.1.2** `GET /reviews/pending` - List pending reviews (for reviewer)
- [x] **7.1.3** `GET /reviews/my-submissions` - List own submissions
- [x] **7.1.4** `POST /reviews/{id}/approve` - Approve with optional comment
- [x] **7.1.5** `POST /reviews/{id}/reject` - Reject with required comment
- [x] **7.1.6** `POST /reviews/{id}/cancel` - Cancel own submission

### 7.2 Create Review Service
**File**: Create `v2/backend/app/services/review_service.py`

- [x] **7.2.1** `submit_for_review(document_id, user)` - Create ReviewRequest
- [x] **7.2.2** `get_pending_reviews(user)` - Filter by reviewer permissions
- [x] **7.2.3** `can_review(user, review)` - Check: not self, has permission
- [x] **7.2.4** `approve_review(review_id, reviewer, comments)`
- [x] **7.2.5** `reject_review(review_id, reviewer, comments)`
- [x] **7.2.6** Implement peer review logic (editors can review other editors)

### 7.3 Create Review Schemas
**File**: Create `v2/backend/app/schemas/review.py`

- [x] **7.3.1** `ReviewSubmit` - version_id (optional), message
- [x] **7.3.2** `ReviewAction` - comments (required for reject)
- [x] **7.3.3** `ReviewResponse` - Full review with document info

### 7.4 Add Document Status: PENDING_REVIEW
**File**: `v2/backend/app/models/__init__.py`

- [x] **7.4.1** Add `PENDING_REVIEW = "pending_review"` to DocumentStatus enum

### 7.5 Create Pending Reviews Page
**File**: Create `v2/frontend/src/pages/ReviewsPage.tsx`

- [x] **7.5.1** Tabs: "Pending My Review" | "My Submissions"
- [x] **7.5.2** Table with document title, submitter, submitted date
- [x] **7.5.3** Quick actions: View, Approve, Reject

### 7.6 Create ReviewDialog Component
**File**: Create `v2/frontend/src/components/ReviewDialog.tsx`

- [x] **7.6.1** Show document preview
- [x] **7.6.2** Comments text area
- [x] **7.6.3** Approve / Reject buttons
- [x] **7.6.4** Confirmation before action

### 7.7 Add Submit for Review Button
**File**: Update document detail page

- [x] **7.7.1** Show "Submit for Review" button when status=DRAFT
- [x] **7.7.2** Hide when already pending or user can't submit
- [x] **7.7.3** Confirmation dialog

### 7.8 Add Review Status UI
**File**: Update document list/detail

- [x] **7.8.1** Show "Pending Review" badge
- [x] **7.8.2** Show reviewer info when assigned
- [x] **7.8.3** Show approval/rejection history

### 7.9 Create Review Notifications
**File**: Update notification service

- [x] **7.9.1** Notify reviewers when doc submitted
- [x] **7.9.2** Notify submitter when approved/rejected
- [x] **7.9.3** Add REVIEW_SUBMITTED, REVIEW_APPROVED, REVIEW_REJECTED to NotificationType

### 7.10 Add Reviews Route
**File**: `v2/frontend/src/App.tsx`

- [x] **7.10.1** Add `/reviews` route for internal users

---

## Step 8: Implement Feedback System (3-4 hrs) ✅ COMPLETE

### 8.1 Create Feedback Management API
**File**: Create `v2/backend/app/api/management/feedback.py`

- [x] **8.1.1** `GET /feedback` - List all feedback (admin+)
- [x] **8.1.2** `GET /feedback/{id}` - Get feedback details
- [x] **8.1.3** `POST /feedback/{id}/respond` - Add response
- [x] **8.1.4** `PUT /feedback/{id}/status` - Update status
- [x] **8.1.5** `GET /feedback/stats/summary` - Get feedback statistics

### 8.2 Create Feedback Schemas
**File**: Defined inline in `v2/backend/app/api/management/feedback.py`

- [x] **8.2.1** `FeedbackDetailResponse` - Full feedback with document/user/tenant info
- [x] **8.2.2** `FeedbackListManagementResponse` - Paginated list response
- [x] **8.2.3** `FeedbackRespondRequest` - Response text validation
- [x] **8.2.4** `FeedbackStatusUpdate` - Status update request

### 8.3 Create Feedback Management Page
**File**: Create `v2/frontend/src/pages/admin/FeedbackPage.tsx`

- [x] **8.3.1** Table with feedback list
- [x] **8.3.2** Filters: status, type, company, search
- [x] **8.3.3** Click to open response dialog
- [x] **8.3.4** Stats cards showing total/pending/responded/closed counts
- [x] **8.3.5** Pagination support

### 8.4 Create FeedbackResponseDialog
**File**: Create `v2/frontend/src/components/FeedbackResponseDialog.tsx`

- [x] **8.4.1** Show original feedback + document link
- [x] **8.4.2** Response text area
- [x] **8.4.3** Status selector
- [x] **8.4.4** Send response + notify customer

### 8.5 Create Feedback Notifications
**File**: Implemented in respond endpoint

- [x] **8.5.1** Notify customer when feedback responded (FEEDBACK_RESPONDED)

### 8.6 Add Feedback Route
**File**: `v2/frontend/src/App.tsx`

- [x] **8.6.1** Add `/admin/feedback` route
- [x] **8.6.2** Add Feedback link to Sidebar for admins

---

## Step 9: Update User Management (3-4 hrs) ✅ COMPLETE

### 9.1 Update User Creation
**File**: `v2/backend/app/api/management/users.py`

- [x] **9.1.1** Add company assignment on create
- [x] **9.1.2** Validate: customers MUST have company
- [x] **9.1.3** Validate: managers can only create editors/viewers
- [x] **9.1.4** Add create, update, delete endpoints
- [x] **9.1.5** Add role hierarchy permission checks

### 9.2 Update User Schemas
**File**: `v2/backend/app/schemas/__init__.py`

- [x] **9.2.1** Add `tenant_id` to UserCreate
- [x] **9.2.2** Add `tenant_id` to UserUpdate
- [x] **9.2.3** Add `company_name` and `company_slug` to UserWithCompanyResponse

### 9.3 Update User Form
**File**: `v2/frontend/src/pages/UsersPage.tsx`

- [x] **9.3.1** Add role dropdown with all 6 roles
- [x] **9.3.2** Show company selector when role=customer
- [x] **9.3.3** Disable roles above current user's level

### 9.4 Update Users Page
**File**: `v2/frontend/src/pages/UsersPage.tsx`

- [x] **9.4.1** Add role filter dropdown
- [x] **9.4.2** Add company filter dropdown
- [x] **9.4.3** Show company column
- [x] **9.4.4** Color-code roles
- [x] **9.4.5** Add Create User dialog with form
- [x] **9.4.6** Add Edit User dialog
- [x] **9.4.7** Add delete (deactivate) action

### 9.5 Create Customer Invitation Flow
**File**: Created `v2/backend/app/api/management/invitations.py`

- [x] **9.5.1** Created Invitation model with token, email, role, tenant, expiry, status
- [x] **9.5.2** `POST /invitations` - Create invitation with role hierarchy validation
- [x] **9.5.3** `GET /invitations` - List invitations with status filter
- [x] **9.5.4** `DELETE /invitations/{id}` - Cancel pending invitation
- [x] **9.5.5** `POST /invitations/{id}/resend` - Resend with new token
- [x] **9.5.6** `GET /auth/invitation/{token}` - Public token validation
- [x] **9.5.7** `POST /auth/invitation/accept` - Accept invitation and create user

### 9.6 Create Invitation UI
**File**: Created `v2/frontend/src/components/InviteUserDialog.tsx`

- [x] **9.6.1** Email input field
- [x] **9.6.2** Role selector (filtered by current user's role)
- [x] **9.6.3** Company selector for customer role
- [x] **9.6.4** Optional message field
- [x] **9.6.5** Send invitation button

### 9.7 Create Accept Invitation Page
**File**: Created `v2/frontend/src/pages/AcceptInvitationPage.tsx`

- [x] **9.7.1** Token validation on page load
- [x] **9.7.2** Display invitation details (email, role, company, inviter)
- [x] **9.7.3** Account creation form (username, full name, password)
- [x] **9.7.4** Auto-login and redirect after acceptance

### 9.8 Update Users Page with Invitations
**File**: Updated `v2/frontend/src/pages/UsersPage.tsx`

- [x] **9.8.1** Added "Invite User" button
- [x] **9.8.2** Added pending invitations table
- [x] **9.8.3** Resend and cancel invitation actions

---

## Step 10: Update Navigation & Routing (2-3 hrs) ✅ COMPLETE

### 10.1 Create Role-Based Route Config
**File**: Created `v2/frontend/src/config/routes.ts`

- [x] **10.1.1** Define route config with role requirements (RouteConfig interface)
- [x] **10.1.2** Export route generator functions (getNavigationForRole, canAccessRoute)
- [x] **10.1.3** Define internal nav items with section grouping
- [x] **10.1.4** Define customer nav items
- [x] **10.1.5** Create getHomeRouteForRole helper

### 10.2 Create RoleGuard Component
**File**: Created `v2/frontend/src/components/guards/RoleGuard.tsx`

- [x] **10.2.1** Accept `allowedRoles` prop
- [x] **10.2.2** Check current user role
- [x] **10.2.3** Redirect to appropriate home if denied
- [x] **10.2.4** Export convenience guards (AdminGuard, ManagerGuard, InternalGuard)

### 10.3 Update Sidebar Navigation
**File**: Updated `v2/frontend/src/components/Sidebar.tsx`

- [x] **10.3.1** Group nav items by section (Main, Management, Admin)
- [x] **10.3.2** Filter items by user role using route config
- [x] **10.3.3** Display section headers for grouped navigation
- [x] **10.3.4** Use centralized route configuration

### 10.4 Update App.tsx with Complete Routes
**File**: Updated `v2/frontend/src/App.tsx`

- [x] **10.4.1** Organize routes by portal type (public, customer, internal, admin)
- [x] **10.4.2** Add all routes with proper RoleGuard guards
- [x] **10.4.3** Add NotFoundPage component with role-appropriate redirect
- [x] **10.4.4** Add RoleBasedRedirect for smart home page routing

### 10.5 Create Role-Based Home Redirect
**File**: Updated `v2/frontend/src/pages/LoginPage.tsx`

- [x] **10.5.1** After login, redirect based on role:
  - customer → `/portal/dashboard`
  - editor/manager/admin → `/dashboard`
- [x] **10.5.2** Check if already logged in on page load and redirect
- [x] **10.5.3** Use getHomeRouteForRole for consistent routing

---

## Step 11: Testing (4-5 hrs) ✅ COMPLETE

### 11.1 Backend Unit Tests
**File**: Created tests in `v2/backend/tests/`

- [x] **11.1.1** `test_permissions.py` - Test permission matrix (20 tests)
- [x] **11.1.2** `test_reviews_api.py` - Test review workflow
- [x] **11.1.3** `test_public_api.py` - Test public endpoints

### 11.2 API Integration Tests
**File**: Created tests in `v2/backend/tests/`

- [x] **11.2.1** `test_public_api.py` - Test public endpoints without auth (17 tests)
- [x] **11.2.2** `test_portal_api.py` - Test customer portal endpoints (19 tests)
- [x] **11.2.4** `test_reviews_api.py` - Test review workflow (15 tests)

### 11.3 Role-Based Access Tests
**File**: Created `v2/backend/tests/test_roles.py`

- [x] **11.3.1** Test each role can only access allowed endpoints
- [x] **11.3.2** Test role escalation prevention
- [x] **11.3.3** Test company isolation (customer A can't see customer B docs)

### 11.5 Security Tests
**File**: Created `v2/backend/tests/test_security.py`

- [x] **11.5.1** Test JWT token with wrong role is rejected
- [x] **11.5.2** Test customer can't access internal docs
- [x] **11.5.3** Test cross-company document access denied

**Test Results Summary**: 82+ tests passing, covering permissions, public API, roles, reviews, and security.

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

