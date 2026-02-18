# P1: Governance and Setup (Endpoint-Level Phase Pack)

## Scope

Phase `P1` covers RBAC policy administration, system setting management, tenant/company administration, and platform user management.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `GET` | `/rbac/policies` | System Admin | `require_system_admin` tenant dependency |
| `PUT` | `/rbac/policies` | System Admin | Upsert policies + publish dynamic map + audit write |
| `POST` | `/rbac/policies/publish` | System Admin | Publish persisted policies to in-memory ACL |
| `GET` | `/system/settings` | System Admin | `require_system_admin` |
| `PUT` | `/system/settings` | System Admin | Upsert keys, delete removed keys, audit write |
| `POST/GET` | `/tenants` | System Admin | `require_system_admin` |
| `GET/PUT/DELETE` | `/tenants/{tenant_id}` | System Admin | `require_system_admin` + slug/user-count constraints |
| `GET` | `/tenants/{tenant_id}/users` | System Admin | `require_system_admin` |
| `GET/POST` | `/companies` | Admin, System Admin | Local `require_admin` role check |
| `GET/PUT/DELETE` | `/companies/{company_id}` | Admin, System Admin | Local `require_admin`; delete is soft deactivate |
| `GET/POST` | `/companies/{company_id}/users` | Admin, System Admin | Local `require_admin` + entity existence checks |
| `DELETE` | `/companies/{company_id}/users/{user_id}` | Admin, System Admin | Cannot remove self |
| `GET` | `/companies/{company_id}/documents` | Admin, System Admin | Local `require_admin` |
| `GET/POST` | `/users` | Manager, Admin, System Admin | Role hierarchy + tenant context scoping |
| `GET/PUT` | `/users/{user_id}` | Self, Manager, Admin, System Admin | Self-service allowed; admin path includes hierarchy checks |
| `DELETE` | `/users/{user_id}` | Admin, System Admin | Soft delete via `is_active=false`; cannot delete self |

## Domain Class Diagram

```mermaid
classDiagram
    class RbacPolicyRouter {
        +GET /rbac/policies
        +PUT /rbac/policies
        +POST /rbac/policies/publish
    }

    class SystemSettingsRouter {
        +GET /system/settings
        +PUT /system/settings
    }

    class TenantRouter {
        +POST /tenants
        +GET /tenants
        +GET /tenants/{tenant_id}
        +PUT /tenants/{tenant_id}
        +DELETE /tenants/{tenant_id}
        +GET /tenants/{tenant_id}/users
    }

    class CompanyRouter {
        +GET /companies
        +POST /companies
        +GET /companies/{company_id}
        +PUT /companies/{company_id}
        +DELETE /companies/{company_id}
        +GET /companies/{company_id}/users
        +POST /companies/{company_id}/users
        +DELETE /companies/{company_id}/users/{user_id}
    }

    class UserRouter {
        +GET /users
        +POST /users
        +GET /users/{user_id}
        +PUT /users/{user_id}
        +DELETE /users/{user_id}
    }

    class RbacService {
        +get_policies()
        +upsert_policies(policies, updated_by)
        +publish_policies()
    }

    class SystemSettingsService {
        +get_settings()
        +upsert_settings(settings, updated_by)
    }

    class TenantContext {
        +tenant_id: int?
        +user_id: int
        +user_role: UserRole
        +is_system_admin: bool
    }

    class RbacPolicy {
        +role: UserRole
        +permissions: json
        +is_active: bool
        +updated_by: int?
        +published_at: datetime?
    }

    class SystemSetting {
        +key: str
        +value: json
        +updated_by: int?
    }

    class Tenant {
        +id: int
        +name: str
        +slug: str
        +is_active: bool
        +company_type: str
    }

    class User {
        +id: int
        +email: str
        +username: str
        +role: UserRole
        +tenant_id: int?
        +is_active: bool
    }

    class AuditLog {
        +id: int
        +action: ActionType
        +details: str?
    }

    RbacPolicyRouter --> TenantContext
    RbacPolicyRouter --> RbacService
    RbacPolicyRouter --> AuditLog
    SystemSettingsRouter --> TenantContext
    SystemSettingsRouter --> SystemSettingsService
    SystemSettingsRouter --> AuditLog
    TenantRouter --> TenantContext
    TenantRouter --> Tenant
    CompanyRouter --> Tenant
    CompanyRouter --> User
    UserRouter --> TenantContext
    UserRouter --> User
    RbacService --> RbacPolicy
    SystemSettingsService --> SystemSetting
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[System admin opens governance controls] --> B{System admin authenticated?}
    B -- No --> B1[403 forbidden]
    B -- Yes --> C[Load and update RBAC policies]
    C --> D[Persist and publish policies]
    D --> E[Write audit event for RBAC update]

    E --> F[Load and update system settings]
    F --> G[Upsert incoming keys and delete removed keys]
    G --> H[Write audit event for settings update]

    H --> I[Manage tenants]
    I --> J{Slug unique and tenant exists?}
    J -- No --> J1[400 or 404]
    J -- Yes --> K[Create or update tenant]
    K --> L{Delete requested while users exist?}
    L -- Yes --> L1[400 blocked]
    L -- No --> M[Delete tenant]

    M --> N[Admin company administration]
    N --> O{Actor is admin or system admin?}
    O -- No --> O1[403 forbidden]
    O -- Yes --> P[Create, update, list, or deactivate company]
    P --> Q{Attempt to delete own company?}
    Q -- Yes --> Q1[400 rejected]
    Q -- No --> R[Persist company change]

    R --> S[User administration]
    S --> T{Role hierarchy and tenant scope pass?}
    T -- No --> T1[403 or 404]
    T -- Yes --> U[Create, update, list, or soft-delete user]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor SysAdmin as System Admin
    actor Admin as Admin
    actor Manager as Manager
    participant FE as Frontend
    participant GOV as RBAC and Settings APIs
    participant TEN as Tenant API
    participant COM as Company API
    participant USR as User API
    participant SVC as RBAC and Settings Services
    participant DB as Database

    Note over SysAdmin,Manager: RBAC and settings governance
    SysAdmin->>FE: Open RBAC policy screen
    FE->>GOV: GET /api/v1/rbac/policies
    GOV->>SVC: get_policies (fallback to static map when empty)
    SVC->>DB: Read rbac_policies
    GOV-->>SysAdmin: policy matrix

    SysAdmin->>FE: Save RBAC policies
    FE->>GOV: PUT /api/v1/rbac/policies
    GOV->>SVC: upsert_policies and publish_policies
    SVC->>DB: Upsert per-role permissions and publish
    GOV->>DB: Insert SYSTEM audit log
    GOV-->>SysAdmin: published policy response

    SysAdmin->>FE: Save system settings
    FE->>GOV: PUT /api/v1/system/settings
    GOV->>SVC: upsert_settings (delete removed keys)
    SVC->>DB: Upsert settings rows
    GOV->>DB: Insert SYSTEM audit log
    GOV-->>SysAdmin: current settings map

    Note over SysAdmin,Manager: Tenant and company administration
    SysAdmin->>FE: Manage tenants
    FE->>TEN: POST/GET/PUT/DELETE /api/v1/tenants...
    TEN->>DB: Validate slug uniqueness and delete constraints
    TEN-->>SysAdmin: tenant operation result

    Admin->>FE: Manage companies
    FE->>COM: GET/POST/PUT/DELETE /api/v1/companies...
    COM->>DB: Query and mutate tenant rows used as companies
    alt Delete own company
        COM-->>Admin: 400 cannot delete your own company
    else Valid mutation
        COM-->>Admin: company response
    end

    Admin->>FE: Manage company membership
    FE->>COM: POST/DELETE /api/v1/companies/{company_id}/users...
    COM->>DB: Resolve user and set user.tenant_id
    COM-->>Admin: membership update result

    Note over SysAdmin,Manager: User management with hierarchy and scope
    Manager->>FE: Create or update user
    FE->>USR: POST/PUT /api/v1/users...
    USR->>DB: Validate role hierarchy, uniqueness, tenant constraints
    alt Allowed
        USR->>DB: Persist user create or update
        USR-->>Manager: user payload
    else Denied
        USR-->>Manager: 400, 403, or 404
    end

    Admin->>FE: Deactivate user
    FE->>USR: DELETE /api/v1/users/{user_id}
    USR->>DB: Validate self-delete and role constraints
    USR->>DB: Set is_active=false
    USR-->>Admin: 204
```
