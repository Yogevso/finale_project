# V2 Implementation Plan - Complete Rebuild Strategy

## Overview
This document outlines a comprehensive, step-by-step plan for rebuilding/implementing V2 of the project based on the existing codebase structure and the Intel Document Lifecycle system.

## Architecture Principles (V2)

### Core Changes from V1:
1. **Frontend Structure**: Only 2 portals
   - **Management Portal** (Internal - Intel users)
   - **Viewer Portal** (External - Customers/Partners)
   - **Entity Management** handled separately (user management outside portal scope)

2. **Backend Architecture**: Unified CMS
   - Single backend service combining CMS + optional AI functionality
   - No separate AI server (keep search generic, AI optional)
   - AI features (if implemented) managed as CMS modules

3. **User Roles & Permissions**:
   - System Admin (infrastructure & configuration)
   - Intel Content Creator (document creation)
   - Reviewer (approval workflows)
   - Intel Content Manager (publishing & permissions)
   - Customer/External Partner (read-only access)

---

## Phase 1: Project Setup & Foundation

### 1.1 Environment Configuration
- [ ] **1.1.1** Review and update `.env.example`
  - [ ] 1.1.1.1 Audit all required environment variables
  - [ ] 1.1.1.2 Add V2-specific configuration variables
  - [ ] 1.1.1.3 Document each variable's purpose
  - [ ] 1.1.1.4 Set up environment validation

- [ ] **1.1.2** Configure local `.env`
  - [ ] 1.1.2.1 Copy from .env.example
  - [ ] 1.1.2.2 Set development-specific values
  - [ ] 1.1.2.3 Verify database connection strings
  - [ ] 1.1.2.4 Set up API keys and secrets

### 1.2 Docker & Infrastructure
- [ ] **1.2.1** Review [docker-compose.yml](../docker-compose.yml)
  - [ ] 1.2.1.1 Audit existing services
  - [ ] 1.2.1.2 Update service versions
  - [ ] 1.2.1.3 Configure volume mappings
  - [ ] 1.2.1.4 Set up network configurations
  - [ ] 1.2.1.5 **Remove AI server service** (AI now part of CMS)

- [ ] **1.2.2** Follow [DOCKER_QUICKSTART.md](../DOCKER_QUICKSTART.md)
  - [ ] 1.2.2.1 Build all containers
  - [ ] 1.2.2.2 Verify service health checks
  - [ ] 1.2.2.3 Test inter-service communication
  - [ ] 1.2.2.4 Document any deviations

### 1.3 Database Setup
- [ ] **1.3.1** PostgreSQL Configuration
  - [ ] 1.3.1.1 Review [POSTGRES_GATE_REPORT.md](../POSTGRES_GATE_REPORT.md)
  - [ ] 1.3.1.2 Run schema comparison using [compare_schemas.py](../compare_schemas.py)
  - [ ] 1.3.1.3 Initialize base schema
  - [ ] 1.3.1.4 Set up migrations infrastructure

---

## Phase 2: Backend Architecture (Unified CMS)

### 2.1 API Design & Documentation
- [ ] **2.1.1** OpenAPI Specification
  - [ ] 2.1.1.1 Review [openapi_spec.json](../openapi_spec.json)
  - [ ] 2.1.1.2 Review [openapi_formatted.json](../openapi_formatted.json)
  - [ ] 2.1.1.3 Identify endpoints to keep/modify/remove
  - [ ] 2.1.1.4 Design new V2 endpoints for document lifecycle
  - [ ] 2.1.1.5 Update request/response schemas
  - [ ] 2.1.1.6 Add authentication specifications
  - [ ] 2.1.1.7 **Remove AI-specific endpoints** (merge into CMS)
  - [ ] 2.1.1.8 Add generic search endpoints

- [ ] **2.1.2** API Versioning Strategy
  - [ ] 2.1.2.1 Define URL versioning scheme (e.g., /api/v2/)
  - [ ] 2.1.2.2 Plan backward compatibility approach
  - [ ] 2.1.2.3 Set deprecation timelines for V1
  - [ ] 2.1.2.4 Document migration path

### 2.2 Backend Core Implementation (Unified CMS)
- [ ] **2.2.1** Review backend_vision/ directory
  - [ ] 2.2.1.1 Audit existing code structure
  - [ ] 2.2.1.2 Identify reusable components
  - [ ] 2.2.1.3 Document technical debt
  - [ ] 2.2.1.4 Plan refactoring priorities
  - [ ] 2.2.1.5 **Remove/archive AI server components** (keep generic search)

- [ ] **2.2.2** Authentication & Authorization
  - [ ] 2.2.2.1 Design JWT/session strategy
  - [ ] 2.2.2.2 Implement user authentication
  - [ ] 2.2.2.3 Set up role-based access control (RBAC)
    - [ ] 2.2.2.3.1 System Admin role
    - [ ] 2.2.2.3.2 Intel Content Creator role
    - [ ] 2.2.2.3.3 Reviewer role
    - [ ] 2.2.2.3.4 Intel Content Manager role
    - [ ] 2.2.2.3.5 Customer/External Partner role
  - [ ] 2.2.2.4 Add OAuth integrations (if needed)
  - [ ] 2.2.2.5 Implement refresh token mechanism
  - [ ] 2.2.2.6 Create external user management (separate from portal)

- [ ] **2.2.3** Document Lifecycle Management
  - [ ] 2.2.3.1 Define document domain models
    - [ ] 2.2.3.1.1 Document entity (id, title, content, metadata)
    - [ ] 2.2.3.1.2 Version entity (track changes)
    - [ ] 2.2.3.1.3 Draft entity (work in progress)
    - [ ] 2.2.3.1.4 Tag/Category entity
  - [ ] 2.2.3.2 Implement document creation flow
    - [ ] 2.2.3.2.1 Create draft document
    - [ ] 2.2.3.2.2 Auto-save functionality
    - [ ] 2.2.3.2.3 Add metadata (tags, categories)
    - [ ] 2.2.3.2.4 Save document versions
  - [ ] 2.2.3.3 Implement document editing
    - [ ] 2.2.3.3.1 Update draft content
    - [ ] 2.2.3.3.2 Track changes
    - [ ] 2.2.3.3.3 Version comparison
  - [ ] 2.2.3.4 Create document repository layer
  - [ ] 2.2.3.5 Add document validation layer

- [ ] **2.2.4** Review & Approval Workflow
  - [ ] 2.2.4.1 Design workflow state machine
    - [ ] 2.2.4.1.1 Draft state
    - [ ] 2.2.4.1.2 Submitted for review
    - [ ] 2.2.4.1.3 Under review
    - [ ] 2.2.4.1.4 Approved
    - [ ] 2.2.4.1.5 Rejected (with feedback)
    - [ ] 2.2.4.1.6 Changes requested
  - [ ] 2.2.4.2 Implement review task assignment
  - [ ] 2.2.4.3 Create review context API
    - [ ] 2.2.4.3.1 Fetch review tasks
    - [ ] 2.2.4.3.2 Get document metadata
    - [ ] 2.2.4.3.3 Retrieve draft versions
  - [ ] 2.2.4.4 Implement review decision logic
    - [ ] 2.2.4.4.1 Approve document
    - [ ] 2.2.4.4.2 Reject with comments
    - [ ] 2.2.4.4.3 Request changes
  - [ ] 2.2.4.5 Add notification system
    - [ ] 2.2.4.5.1 Notify reviewers (task assignment)
    - [ ] 2.2.4.5.2 Notify creators (decision made)
    - [ ] 2.2.4.5.3 Log review actions

- [ ] **2.2.5** Permissions & Access Control
  - [ ] 2.2.5.1 Design permission model
    - [ ] 2.2.5.1.1 Document-level permissions
    - [ ] 2.2.5.1.2 Customer-specific access
    - [ ] 2.2.5.1.3 Role-based permissions
  - [ ] 2.2.5.2 Implement permission management
    - [ ] 2.2.5.2.1 Set permissions for customers
    - [ ] 2.2.5.2.2 Select allowed scopes
    - [ ] 2.2.5.2.3 Create permission lists
  - [ ] 2.2.5.3 Add permission verification
    - [ ] 2.2.5.3.1 Verify customer access
    - [ ] 2.2.5.3.2 Check authorized scopes
    - [ ] 2.2.5.3.3 Validate document access
  - [ ] 2.2.5.4 Implement permission audit log
  - [ ] 2.2.5.5 Create ACL (Access Control List) system

- [ ] **2.2.6** Publishing & Distribution
  - [ ] 2.2.6.1 Implement publish workflow
    - [ ] 2.2.6.1.1 Trigger publish action
    - [ ] 2.2.6.1.2 Request permissions setup
    - [ ] 2.2.6.1.3 Get available permissions/scopes
    - [ ] 2.2.6.1.4 Create permission list
  - [ ] 2.2.6.2 Create publish request logic
    - [ ] 2.2.6.2.1 Validate document ready
    - [ ] 2.2.6.2.2 Set version id
    - [ ] 2.2.6.2.3 Update status to published
  - [ ] 2.2.6.3 Implement sync/update mechanisms
    - [ ] 2.2.6.3.1 Sync published content
    - [ ] 2.2.6.3.2 Update status metadata
  - [ ] 2.2.6.4 Add publish notification system
  - [ ] 2.2.6.5 Log usage data (manager, doc id, permissions, timestamp)

### 2.3 Search & Discovery (Generic Implementation)
- [ ] **2.3.1** Basic Search Infrastructure
  - [ ] 2.3.1.1 Implement text-based search
  - [ ] 2.3.1.2 Add metadata filtering
  - [ ] 2.3.1.3 Create category/tag search
  - [ ] 2.3.1.4 Add search ranking algorithm
  - [ ] 2.3.1.5 Implement search result pagination

- [ ] **2.3.2** Semantic Search (Optional - Modular)
  - [ ] 2.3.2.1 Design as pluggable module within CMS
  - [ ] 2.3.2.2 Create search service abstraction
  - [ ] 2.3.2.3 Implement semantic query processing (if AI enabled)
  - [ ] 2.3.2.4 Add fallback to basic search
  - [ ] 2.3.2.5 Log search usage data
  - [ ] 2.3.2.6 **Keep implementation generic** (no dedicated AI service)

- [ ] **2.3.3** Document Discovery Features
  - [ ] 2.3.3.1 Build ranked search results
  - [ ] 2.3.3.2 Implement authorized scope filtering
  - [ ] 2.3.3.3 Add document embeddings/metadata (optional)
  - [ ] 2.3.3.4 Create search analytics
  - [ ] 2.3.3.5 Log customer search actions

### 2.4 Customer Interaction Features
- [ ] **2.4.1** Document Viewing & Access
  - [ ] 2.4.1.1 Implement document retrieval
  - [ ] 2.4.1.2 Verify access permissions
  - [ ] 2.4.1.3 Log document views
  - [ ] 2.4.1.4 Track usage analytics

- [ ] **2.4.2** Comment & Feedback System
  - [ ] 2.4.2.1 Design comment data model
  - [ ] 2.4.2.2 Implement add comment functionality
  - [ ] 2.4.2.3 Create comment verification/moderation
  - [ ] 2.4.2.4 Add comment notifications
  - [ ] 2.4.2.5 Store comments with timestamps
  - [ ] 2.4.2.6 Notify stakeholders of new comments
  - [ ] 2.4.2.7 Log comment actions

- [ ] **2.4.3** Draft Revision System
  - [ ] 2.4.3.1 Implement draft update after feedback
  - [ ] 2.4.3.2 Create change request workflow
  - [ ] 2.4.3.3 Save revised drafts with new versions
  - [ ] 2.4.3.4 Update status metadata
  - [ ] 2.4.3.5 Log revision actions

### 2.5 Data Layer
- [ ] **2.5.1** ORM/Query Builder Setup
  - [ ] 2.5.1.1 Choose ORM framework (SQLAlchemy)
  - [ ] 2.5.1.2 Configure connection pooling
  - [ ] 2.5.1.3 Set up query logging
  - [ ] 2.5.1.4 Implement transaction management

- [ ] **2.5.2** Database Schema Design
  - [ ] 2.5.2.1 Users table (external entity management)
  - [ ] 2.5.2.2 Documents table
  - [ ] 2.5.2.3 Versions table
  - [ ] 2.5.2.4 Drafts table
  - [ ] 2.5.2.5 Reviews table
  - [ ] 2.5.2.6 Permissions table
  - [ ] 2.5.2.7 Comments table
  - [ ] 2.5.2.8 Usage logs table
  - [ ] 2.5.2.9 Tags/Categories tables

- [ ] **2.5.3** Database Migrations
  - [ ] 2.5.3.1 Create initial migration files
  - [ ] 2.5.3.2 Set up migration runner
  - [ ] 2.5.3.3 Add rollback procedures
  - [ ] 2.5.3.4 Document migration workflow

---

## Phase 3: Frontend Development (2 Portal Architecture)

### 3.1 Shared Frontend Foundation
- [ ] **3.1.1** Review frontend/ directory
  - [ ] 3.1.1.1 Audit current component structure
  - [ ] 3.1.1.2 Review [TODOFRONT.md](../TODOFRONT.md) for pending items
  - [ ] 3.1.1.3 Identify reusable components
  - [ ] 3.1.1.4 Plan component library structure
  - [ ] 3.1.1.5 **Remove entity management from portal** (external)

- [ ] **3.1.2** Design System (Shared)
  - [ ] 3.1.2.1 Define color palette (Intel branding)
  - [ ] 3.1.2.2 Set typography scales
  - [ ] 3.1.2.3 Create spacing system
  - [ ] 3.1.2.4 Build shared component library
  - [ ] 3.1.2.5 Create responsive layouts

- [ ] **3.1.3** State Management (Shared)
  - [ ] 3.1.3.1 Choose state management solution
  - [ ] 3.1.3.2 Design global state structure
  - [ ] 3.1.3.3 Implement context providers
  - [ ] 3.1.3.4 Add state persistence layer

### 3.2 Management Portal (Internal - Intel Users)
- [ ] **3.2.1** Portal Architecture
  - [ ] 3.2.1.1 Set up routing structure (/management/*)
  - [ ] 3.2.1.2 Create layout components
  - [ ] 3.2.1.3 Implement navigation sidebar
  - [ ] 3.2.1.4 Add role-based menu visibility

- [ ] **3.2.2** Document Creation & Editing
  - [ ] 3.2.2.1 Build rich text editor integration
  - [ ] 3.2.2.2 Create document metadata form
  - [ ] 3.2.2.3 Implement auto-save functionality
  - [ ] 3.2.2.4 Add version history viewer
  - [ ] 3.2.2.5 Create tag/category selector
  - [ ] 3.2.2.6 Implement draft management

- [ ] **3.2.3** Review & Approval Workflow UI
  - [ ] 3.2.3.1 Create review task dashboard
  - [ ] 3.2.3.2 Build document comparison view
  - [ ] 3.2.3.3 Implement approval/rejection forms
  - [ ] 3.2.3.4 Add review comments/annotations
  - [ ] 3.2.3.5 Create review history timeline
  - [ ] 3.2.3.6 Add notification center

- [ ] **3.2.4** Permissions & Publishing
  - [ ] 3.2.4.1 Build permissions management UI
  - [ ] 3.2.4.2 Create customer access selector
  - [ ] 3.2.4.3 Implement publishing workflow
  - [ ] 3.2.4.4 Add publish/unpublish actions
  - [ ] 3.2.4.5 Create permission audit log viewer

- [ ] **3.2.5** Content Management Dashboard
  - [ ] 3.2.5.1 Create overview statistics
  - [ ] 3.2.5.2 Build document status widgets
  - [ ] 3.2.5.3 Add recent activity feed
  - [ ] 3.2.5.4 Implement search & filters
  - [ ] 3.2.5.5 Create bulk operations UI

### 3.3 Viewer Portal (External - Customers)
- [ ] **3.3.1** Portal Architecture
  - [ ] 3.3.1.1 Set up routing structure (/viewer/*)
  - [ ] 3.3.1.2 Create clean, simple layout
  - [ ] 3.3.1.3 Implement navigation menu
  - [ ] 3.3.1.4 Add breadcrumb navigation

- [ ] **3.3.2** Document Discovery
  - [ ] 3.3.2.1 Build search interface (generic, no AI dependency)
  - [ ] 3.3.2.2 Create category browser
  - [ ] 3.3.2.3 Add filter sidebar
  - [ ] 3.3.2.4 Implement search results view
  - [ ] 3.3.2.5 Add search suggestions/autocomplete
  - [ ] 3.3.2.6 Create saved searches feature

- [ ] **3.3.3** Document Viewing
  - [ ] 3.3.3.1 Build document reader component
  - [ ] 3.3.3.2 Implement table of contents
  - [ ] 3.3.3.3 Add document download options
  - [ ] 3.3.3.4 Create print-friendly view
  - [ ] 3.3.3.5 Add document sharing features
  - [ ] 3.3.3.6 Implement embedded media viewer

- [ ] **3.3.4** User Interaction
  - [ ] 3.3.4.1 Add comment/feedback system
  - [ ] 3.3.4.2 Create document bookmarking
  - [ ] 3.3.4.3 Implement usage tracking (analytics)
  - [ ] 3.3.4.4 Add user preferences panel

### 3.4 API Integration (Both Portals)
- [ ] **3.4.1** HTTP Client Setup
  - [ ] 3.4.1.1 Configure API client (Axios/Fetch)
  - [ ] 3.4.1.2 Add request interceptors (auth tokens)
  - [ ] 3.4.1.3 Add response interceptors (error handling)
  - [ ] 3.4.1.4 Implement retry logic
  - [ ] 3.4.1.5 Add request caching strategy

- [ ] **3.4.2** API Services Layer
  - [ ] 3.4.2.1 Create auth service
  - [ ] 3.4.2.2 Create document service
  - [ ] 3.4.2.3 Create permissions service
  - [ ] 3.4.2.4 Create search service (generic)
  - [ ] 3.4.2.5 Create comments service
  - [ ] 3.4.2.6 Implement error handling
  - [ ] 3.4.2.7 Add loading states
  - [ ] 3.4.2.8 Implement optimistic updates

---

## Phase 4: Testing & Quality Assurance

### 4.1 Backend Testing
- [ ] **4.1.1** Unit Tests
  - [ ] 4.1.1.1 Set up testing framework
  - [ ] 4.1.1.2 Write model tests
  - [ ] 4.1.1.3 Write service layer tests
  - [ ] 4.1.1.4 Test workflow state machine
  - [ ] 4.1.1.5 Test permission logic
  - [ ] 4.1.1.6 Achieve 80%+ code coverage

- [ ] **4.1.2** Integration Tests
  - [ ] 4.1.2.1 Set up test database
  - [ ] 4.1.2.2 Test API endpoints
  - [ ] 4.1.2.3 Review [test_sprint2_endpoints.ps1](../test_sprint2_endpoints.ps1)
  - [ ] 4.1.2.4 Implement endpoint test suite
  - [ ] 4.1.2.5 Test authentication flows
  - [ ] 4.1.2.6 Test document lifecycle
  - [ ] 4.1.2.7 Test review workflow
  - [ ] 4.1.2.8 Test permissions system

### 4.2 Frontend Testing
- [ ] **4.2.1** Component Tests (Both Portals)
  - [ ] 4.2.1.1 Set up testing library
  - [ ] 4.2.1.2 Test UI components
  - [ ] 4.2.1.3 Test hooks and utilities
  - [ ] 4.2.1.4 Add snapshot tests

- [ ] **4.2.2** E2E Tests
  - [ ] 4.2.2.1 Set up Playwright (already configured)
  - [ ] 4.2.2.2 Write critical path tests
    - [ ] 4.2.2.2.1 Document creation workflow
    - [ ] 4.2.2.2.2 Review & approval workflow
    - [ ] 4.2.2.2.3 Publishing workflow
    - [ ] 4.2.2.2.4 Customer document access
  - [ ] 4.2.2.3 Add visual regression tests
  - [ ] 4.2.2.4 Set up CI/CD integration

### 4.3 Quality Gates
- [ ] **4.3.1** Review Quality Reports
  - [ ] 4.3.1.1 Review [WARNINGS_CLEANUP_REPORT.md](../WARNINGS_CLEANUP_REPORT.md)
  - [ ] 4.3.1.2 Review [WARNINGS_SANITY_GATE_REPORT.md](../WARNINGS_SANITY_GATE_REPORT.md)
  - [ ] 4.3.1.3 Address all critical warnings
  - [ ] 4.3.1.4 Set up linting rules

- [ ] **4.3.2** Testing Documentation
  - [ ] 4.3.2.1 Review [TESTING_GUIDE.md](../TESTING_GUIDE.md)
  - [ ] 4.3.2.2 Update testing procedures
  - [ ] 4.3.2.3 Document test data setup
  - [ ] 4.3.2.4 Create testing checklists

---

## Phase 5: Documentation & System Configuration

### 5.1 System Configuration & Admin
- [ ] **5.1.1** System Setup (Phase 1 - from diagram)
  - [ ] 5.1.1.1 Open admin console
  - [ ] 5.1.1.2 Configure tenants & system settings
  - [ ] 5.1.1.3 Persist tenant/system settings
  - [ ] 5.1.1.4 Define role-based policies
  - [ ] 5.1.1.5 Submit RBAC policies
  - [ ] 5.1.1.6 Publish RBAC policies
  - [ ] 5.1.1.7 Set up system log event handling

- [ ] **5.1.2** CMS Core Features
  - [ ] 5.1.2.1 Review [CMS_DOCUMENTS_FIX.md](../CMS_DOCUMENTS_FIX.md)
  - [ ] 5.1.2.2 Implement unified CMS architecture
  - [ ] 5.1.2.3 Create content schema
  - [ ] 5.1.2.4 Build CRUD operations
  - [ ] 5.1.2.5 Add rich text editor integration
  - [ ] 5.1.2.6 Implement media/file management
  - [ ] 5.1.2.7 Create metadata management

- [ ] **5.1.3** Document Management (Phase 2 - from diagram)
  - [ ] 5.1.3.1 Set up file upload system
  - [ ] 5.1.3.2 Implement version control
  - [ ] 5.1.3.3 Add metadata tagging
  - [ ] 5.1.3.4 Create search functionality
  - [ ] 5.1.3.5 Build document lifecycle tracking

### 5.2 Project Documentation
- [ ] **5.2.1** Technical Documentation
  - [ ] 5.2.1.1 Update [README.md](../README.md)
  - [ ] 5.2.1.2 Review docs/ directory
  - [ ] 5.2.1.3 Document API endpoints
  - [ ] 5.2.1.4 Create architecture diagrams
  - [ ] 5.2.1.5 Write deployment guide
  - [ ] 5.2.1.6 Document V2 architecture changes

- [ ] **5.2.2** Development Guides
  - [ ] 5.2.2.1 Create contribution guidelines
  - [ ] 5.2.2.2 Document coding standards
  - [ ] 5.2.2.3 Write setup instructions
  - [ ] 5.2.2.4 Add troubleshooting guide
  - [ ] 5.2.2.5 Document 2-portal architecture

---

## Phase 6: Infrastructure & DevOps

### 6.1 CI/CD Pipeline
- [ ] **6.1.1** GitHub Actions
  - [ ] 6.1.1.1 Review .github/ directory
  - [ ] 6.1.1.2 Set up build pipeline
  - [ ] 6.1.1.3 Add automated testing
  - [ ] 6.1.1.4 Configure deployment workflows

- [ ] **6.1.2** Pre-commit Hooks
  - [ ] 6.1.2.1 Review `.pre-commit-config.yaml`
  - [ ] 6.1.2.2 Set up linting checks
  - [ ] 6.1.2.3 Add format validation
  - [ ] 6.1.2.4 Configure commit message rules

### 6.2 Deployment Strategy
- [ ] **6.2.1** Infrastructure as Code
  - [ ] 6.2.1.1 Review infra/ directory
  - [ ] 6.2.1.2 Define cloud resources
  - [ ] 6.2.1.3 Set up staging environment
  - [ ] 6.2.1.4 Configure production environment
  - [ ] 6.2.1.5 **Remove AI server infrastructure**

- [ ] **6.2.2** Monitoring & Logging
  - [ ] 6.2.2.1 Set up application monitoring
  - [ ] 6.2.2.2 Configure error tracking
  - [ ] 6.2.2.3 Add performance monitoring
  - [ ] 6.2.2.4 Set up alerting rules
  - [ ] 6.2.2.5 Implement usage analytics
  - [ ] 6.2.2.6 Track document lifecycle events

---

## Phase 7: Migration & Rollout

### 7.1 Data Migration
- [ ] **7.1.1** Migration Planning
  - [ ] 7.1.1.1 Audit existing data
  - [ ] 7.1.1.2 Design migration scripts
  - [ ] 7.1.1.3 Create data validation rules
  - [ ] 7.1.1.4 Plan rollback procedures

- [ ] **7.1.2** Migration Execution
  - [ ] 7.1.2.1 Test on staging data
  - [ ] 7.1.2.2 Perform dry runs
  - [ ] 7.1.2.3 Execute production migration
  - [ ] 7.1.2.4 Validate migrated data

### 7.2 Rollout Strategy
- [ ] **7.2.1** Phased Deployment
  - [ ] 7.2.1.1 Deploy to staging
  - [ ] 7.2.1.2 Perform UAT testing
  - [ ] 7.2.1.3 Canary deployment (10%)
  - [ ] 7.2.1.4 Gradual rollout (50%, 100%)

- [ ] **7.2.2** Post-Launch
  - [ ] 7.2.2.1 Monitor error rates
  - [ ] 7.2.2.2 Track performance metrics
  - [ ] 7.2.2.3 Gather user feedback
  - [ ] 7.2.2.4 Address critical issues

---

## Phase 8: Completion & Handoff

### 8.1 Final Reviews
- [ ] **8.1.1** Code Review
  - [ ] 8.1.1.1 Review all PR notes from [PR_NOTES.md](../PR_NOTES.md)
  - [ ] 8.1.1.2 Conduct security audit
  - [ ] 8.1.1.3 Performance optimization review
  - [ ] 8.1.1.4 Accessibility compliance check

- [ ] **8.1.2** Documentation Review
  - [ ] 8.1.2.1 Review [VISION_REBUILD_PLAN.md](../VISION_REBUILD_PLAN.md)
  - [ ] 8.1.2.2 Review [PHASE_2_COMPLETE.md](../PHASE_2_COMPLETE.md)
  - [ ] 8.1.2.3 Update all documentation
  - [ ] 8.1.2.4 Create release notes

### 8.2 Knowledge Transfer
- [ ] **8.2.1** Team Training
  - [ ] 8.2.1.1 Conduct architecture walkthrough
  - [ ] 8.2.1.2 Demo key features
  - [ ] 8.2.1.3 Review operational procedures
  - [ ] 8.2.1.4 Document support procedures

- [ ] **8.2.2** Final Deliverables
  - [ ] 8.2.2.1 Review [TODO.md](../TODO.md) completion
  - [ ] 8.2.2.2 Archive completed tasks
  - [ ] 8.2.2.3 Create V2 release tag
  - [ ] 8.2.2.4 Celebrate! 🎉

---

## Appendix

### A. Architecture Diagram Reference (Intel Document Lifecycle)

**Actor Roles:**
- System Admin: Infrastructure & configuration
- Intel Content Creator: Document authoring
- Reviewer: Approval workflows
- Intel Content Manager: Publishing & permissions
- Customer (External Partner): Document consumption

**System Components:**
1. **Docs Management Portal (Intel)** - Internal content management
2. **Viewer Portal (External)** - Customer document access
3. **Content Management Services (CMS)** - Unified backend
4. **Access Control System** - Permissions & RBAC
5. **AI Services** - ❌ REMOVED (integrated into CMS as optional module)
6. **Storage/Database** - Document & metadata persistence

**Workflow Phases:**
1. **Phase 1**: System Setup & Configuration
2. **Phase 2**: Content Creation & Processing
3. **Phase 3**: Review, Permissions & Publication
4. **Phase 4**: Customer Access & Interaction

### B. Key Features to Implement

**Document Lifecycle:**
- Draft creation → Auto-save → Tagging/Summary
- Submit for review → Review context → Approval/Rejection
- Permission setup → Publishing → Customer access
- Comment system → Feedback loop → Revisions
- Search (generic, AI optional) → Document retrieval → Usage tracking

**Logging & Monitoring:**
- User actions (creator, reviewer, manager, customer)
- Document operations (create, update, publish, view)
- Permission changes (docId, permissions, timestamps)
- Search queries (query, authorized scopes, timestamps)
- Comments & feedback (userId, docId, timestamps)

### C. File References
- Configuration: `.env.example`, [docker-compose.yml](../docker-compose.yml)
- Documentation: [README.md](../README.md), [TESTING_GUIDE.md](../TESTING_GUIDE.md)
- Reports: [WARNINGS_CLEANUP_REPORT.md](../WARNINGS_CLEANUP_REPORT.md), [POSTGRES_GATE_REPORT.md](../POSTGRES_GATE_REPORT.md)
- Planning: [TODO.md](../TODO.md), [TODOFRONT.md](../TODOFRONT.md), [VISION_REBUILD_PLAN.md](../VISION_REBUILD_PLAN.md)
- CMS: [CMS_DOCUMENTS_FIX.md](../CMS_DOCUMENTS_FIX.md)
- Flow: [WEBSITE_FLOW_ANALYSIS.md](../WEBSITE_FLOW_ANALYSIS.md), [FLOW_FIXES_APPLIED.md](../FLOW_FIXES_APPLIED.md)

### D. V2 Architectural Decisions

**What's Changed:**
1. ❌ **Removed**: Separate AI server (now optional CMS module)
2. ❌ **Removed**: Entity management from portal (separate user management)
3. ✅ **Added**: 2-portal architecture (Management + Viewer only)
4. ✅ **Added**: Unified CMS backend
5. ✅ **Added**: Complete document lifecycle workflows
6. ✅ **Added**: Review & approval system
7. ✅ **Added**: Generic search (AI optional)

**Why:**
- Simpler architecture
- Keep search functionality generic
- AI features optional/modular (not core requirement)
- Better separation of concerns
- External user management (not in portal scope)
- Focused portal responsibilities

**Frontend Portals:**
- **Management Portal**: Document creation, review, permissions, publishing
- **Viewer Portal**: Document search, viewing, commenting
- **Entity Management**: Handled separately (user admin, system config)

**Backend Structure:**
- Single unified CMS service
- Optional AI module for semantic search
- Generic search as default
- All document lifecycle in one service

### E. Implementation Notes
- This plan is a living document - update as needed
- Track progress by checking off completed items
- Start from Phase 1 and work sequentially
- Reference existing project files to leverage existing work
- Each phase builds on previous phases
- Test thoroughly at each phase before proceeding
- Keep AI functionality optional and modular
- Maintain separation between portals and entity management
