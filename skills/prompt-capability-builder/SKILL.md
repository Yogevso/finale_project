---
name: prompt-capability-builder
description: Convert a user prompt into a production-ready, integration-safe capability specification tailored specifically for the Documentation Platform architecture (FastAPI + React + RBAC + Multi-tenant + Real-time Collaboration).
---

# Prompt Capability Builder (Project-Aware v2)

## 🎯 Purpose

Transform any prompt into a concrete, integration-safe capability that can be implemented in the Documentation Platform without breaking:

- Multi-tenant isolation
- RBAC policies
- API versioning (/api/v1)
- Real-time collaboration
- Existing test coverage
- Docker environments

This skill enforces engineering discipline equivalent to a senior backend/full-stack tech lead.

---

## 🏗 System Context (Mandatory Awareness)

All capabilities MUST respect:

- Backend: FastAPI + SQLAlchemy + Pydantic
- Auth: JWT-based authentication
- RBAC: Role-based access control
- Multi-tenancy: Tenant isolation enforced in dependencies
- API versioning: `/api/v1`
- Frontend: React + Vite + TypeScript
- Collaboration: Yjs + Hocuspocus WebSocket server
- DevOps: Docker Compose (dev + prod)
- Test stack: Pytest + Playwright + Jest

Any generated capability that ignores these constraints is invalid.

---

## 🔍 Workflow

### 1️⃣ Parse the Prompt

Extract:

- Business goal
- Affected layer (backend / frontend / collab / devops)
- Domain objects
- Roles impacted (must be explicit: System Admin / Admin / Manager / Editor / Viewer / Customer)
- Tenant scope
- Whether real-time behavior is affected

If critical inputs are missing — ask up to 3 targeted questions.

---

### 2️⃣ Classify the Capability

Primary type:

- transformation
- retrieval
- generation
- orchestration
- validation
- integration

Domain:

- backend
- frontend
- devops
- full-stack

---

### 3️⃣ Produce a Production-Ready Capability Spec

Use the structure below.

---

# 📄 Output Template (Strict)

```markdown
Capability Name: <hyphen-case>
Domain: <backend|frontend|devops|full-stack>
Purpose: <single precise sentence>

Trigger Conditions:

- ...

Required Inputs:

- ...

Optional Inputs:

- ...

Repo Context:

- Relevant paths:
- Existing constraints:
- Existing related tests:

Change Impact Analysis:

- Affected API routes:
- Affected models:
- Affected services:
- Affected dependencies/guards:
- Affected frontend pages:
- Affected collaboration logic:
- Required test updates:

Output Contract:

- API changes (if any):
- Request schema:
- Response schema:
- Error cases:
- Permission behavior:
- Tenant behavior:

Execution Steps:

1. ...
2. ...
3. ...

Integration Validation:

- Backward compatibility impact:
- Tenant isolation verified:
- RBAC matrix verified:
- API versioning preserved (/api/v1):
- Collaboration impact evaluated:
- Docker/dev/prod environment impact:

Deliverables:

- Files to create/update:
- Tests to add/update:
- Commands to run:
- Migration required (yes/no):

Tools/Dependencies:

- ...

Constraints/Safety:

- Must not break tenant isolation
- Must not bypass RBAC dependencies
- Must not remove existing API contracts
- Must preserve /api/v1 prefix

Failure Modes:

- ...
- ...
- ...

Acceptance Tests:

Happy Path:

1. Given ... When ... Then ...

Failure Paths: 2. Given invalid role ... Then 403 3. Given cross-tenant access ... Then 404

Permission Test: 4. Given role X ... Then allowed 5. Given role Y ... Then denied

Tenant Isolation Test: 6. Given tenant A accessing tenant B resource ... Then forbidden
```

---

## ✅ Quality Gate (Enforced Checklist)

Before returning the capability, the agent MUST verify:

### Contract & Traceability

- Every execution step maps to at least one Required Input and one Output Contract field.
- API contracts explicitly define success and error responses.
- Roles are explicitly listed (no generic “user/admin”).

### Testing Requirements (Minimum)

- 1 happy-path test.
- 2 failure-path tests.
- 1 permission test.
- 1 tenant isolation test.

### Repository Precision

- Concrete file paths are listed.
- `/api/v1` is preserved (if backend).
- Collaboration impact evaluated (if document-related).
- Docker/dev/prod impact considered.

If any checklist item is missing → the capability is invalid.

---

## 🧠 Domain Rules (Enforced)

### Backend

Must include:

- Dependency injection updates
- RBAC guard validation
- Tenant filtering in queries
- Proper HTTP status codes (401/403/404/409/422 as appropriate)
- Schema validation (Pydantic)

### Frontend

Must include:

- Loading / empty / error / success states
- Role-based UI behavior
- API client updates
- Type updates aligned with backend schema

### Collaboration (if document-related)

Must include:

- Yjs document impact
- Persistence impact
- WebSocket auth impact (JWT validation + tenant context)

### DevOps

Must include:

- Compose impact (dev + prod)
- Required environment variables
- Health checks impact
- Rollback / safe recovery strategy

---

## 🚫 Forbidden Patterns (Hard Fail)

The capability is invalid if it contains:

- “Handle properly”
- “Update as needed”
- Vague acceptance criteria
- Ignoring roles
- Ignoring tenants
- Ignoring tests
- Ignoring Docker
- Ignoring collaboration when relevant

---

## 🏁 Objective

Every capability generated must be:

✔ Integration-safe  
✔ Tenant-safe  
✔ RBAC-safe  
✔ Test-covered  
✔ Docker-compatible  
✔ Collaboration-aware  
✔ Production-grade
