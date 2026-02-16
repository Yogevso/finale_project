# P1: Governance and Setup (Endpoint-Level Phase Pack)

## Scope

Phase `P1` covers system-level governance: RBAC policies, system settings, tenant/company administration, and user management.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `GET` | `/rbac/policies` | System Admin | `require_system_admin` |
| `PUT` | `/rbac/policies` | System Admin | upsert + publish + audit |
| `POST` | `/rbac/policies/publish` | System Admin | publish dynamic permissions |
| `GET` | `/system/settings` | System Admin | `require_system_admin` |
| `PUT` | `/system/settings` | System Admin | upsert + audit |
| `POST/GET/PUT/DELETE` | `/tenants` and `/tenants/{id}` | System Admin | `require_system_admin` |
| `GET/POST/PUT/DELETE` | `/companies...` | Admin, System Admin | admin-only company operations |
| `GET/POST/GET/PUT/DELETE` | `/users...` | Manager+, Admin+, System Admin | role hierarchy + tenant scope |

## Domain Class Diagram

```mermaid
classDiagram
    class GovernanceController {
        +getPolicies()
        +updatePolicies(payload)
        +publishPolicies()
        +getSystemSettings()
        +updateSystemSettings(payload)
    }
    class TenantController {
        +createTenant(payload)
        +listTenants()
        +updateTenant(id, payload)
        +deleteTenant(id)
    }
    class CompanyController {
        +createCompany(payload)
        +listCompanies(filters)
        +updateCompany(id, payload)
        +deleteCompany(id)
    }
    class UserAdminController {
        +createUser(payload)
        +listUsers(filters)
        +getUser(id)
        +updateUser(id, payload)
        +deactivateUser(id)
    }
    class RBACPolicyService {
        +getPolicies()
        +upsertPolicies(rows)
        +publishPolicies()
        +computeEffectivePermissions()
    }
    class SystemSettingsService {
        +getSettings()
        +upsertSettings(payload)
        +deleteRemovedKeys(payload)
    }
    class TenantScopeGuard {
        +requireSystemAdmin(actor)
        +resolveTenantScope(actor)
        +assertRoleHierarchy(actorRole, targetRole)
    }
    class Tenant {
        +UUID id
        +String slug
        +String name
        +Boolean is_active
        +DateTime created_at
    }
    class Company {
        +UUID id
        +UUID tenant_id
        +String name
        +Boolean is_active
    }
    class PlatformUser {
        +UUID id
        +UUID tenant_id
        +UUID company_id
        +String role
        +Boolean is_active
    }
    class RBACPolicy {
        +UUID id
        +String role
        +String permission
        +Boolean allowed
        +Integer version
    }
    class SystemSetting {
        +UUID id
        +String setting_key
        +String setting_value
        +String value_type
    }
    class AuditEvent {
        +UUID id
        +UUID actor_id
        +String action
        +String resource_type
        +UUID resource_id
    }

    GovernanceController --> RBACPolicyService
    GovernanceController --> SystemSettingsService
    GovernanceController --> TenantScopeGuard
    TenantController --> TenantScopeGuard
    CompanyController --> TenantScopeGuard
    UserAdminController --> TenantScopeGuard
    RBACPolicyService --> RBACPolicy
    SystemSettingsService --> SystemSetting
    TenantController --> Tenant
    CompanyController --> Company
    UserAdminController --> PlatformUser
    Tenant "1" --> "0..*" Company
    Tenant "1" --> "0..*" PlatformUser
    Company "1" --> "0..*" PlatformUser
    GovernanceController --> AuditEvent
    TenantController --> AuditEvent
    CompanyController --> AuditEvent
    UserAdminController --> AuditEvent
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[System Admin opens governance console] --> B{System admin privileges present?}
    B -- No --> B1[Stop with 403]
    B -- Yes --> C[Load current RBAC policies]
    C --> D[Edit policy matrix]
    D --> E[Upsert policy rows]
    E --> F[Publish active policies]
    F --> G[Record governance audit event]

    G --> H[Open system settings]
    H --> I[Apply key/value updates]
    I --> J[Upsert changed keys and remove deleted keys]
    J --> K[Write settings audit event]

    K --> L[Manage platform tenants]
    L --> M{Tenant slug unique and constraints valid?}
    M -- No --> M1[Reject request 400]
    M -- Yes --> N[Persist tenant create/update/delete]

    N --> O[Admin manages companies in tenant]
    O --> P{Actor is admin or system admin?}
    P -- No --> P1[Reject request 403]
    P -- Yes --> Q[Persist company assignment and status]

    Q --> R[Manager/Admin manages users]
    R --> S{Target role allowed by hierarchy and scope?}
    S -- No --> S1[Reject request 403]
    S -- Yes --> T[Persist create/update/deactivate]
    T --> U[Publish updated operational state]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor SysAdmin as System Admin
    actor Admin as Admin
    actor Manager as Manager
    participant FE as Frontend
    participant API as Governance APIs
    participant TENANT as Tenant Context and Role Guards
    participant RBAC as RBAC Service
    participant DB as Database

    Note over SysAdmin,Manager: RBAC and system settings governance
    SysAdmin->>FE: Open RBAC policies
    FE->>API: GET /api/v1/rbac/policies
    API->>TENANT: require_system_admin
    API->>RBAC: get_policies or fallback defaults
    RBAC->>DB: Read rbac_policies
    API-->>SysAdmin: policy matrix

    SysAdmin->>FE: Update policies
    FE->>API: PUT /api/v1/rbac/policies
    API->>TENANT: require_system_admin
    API->>RBAC: upsert_policies
    RBAC->>DB: Persist policy rows
    API->>RBAC: publish_policies
    RBAC->>DB: Read active policies
    RBAC-->>API: dynamic effective permissions loaded
    API->>DB: Insert system audit event
    API-->>SysAdmin: updated published policies

    SysAdmin->>FE: Update system settings
    FE->>API: PUT /api/v1/system/settings
    API->>TENANT: require_system_admin
    API->>DB: Upsert settings and delete removed keys
    API->>DB: Insert system audit event
    API-->>SysAdmin: effective settings payload

    Note over SysAdmin,Manager: Tenant and company administration
    SysAdmin->>FE: Manage platform tenants
    FE->>API: POST/GET/PUT/DELETE /api/v1/tenants...
    API->>TENANT: require_system_admin
    API->>DB: Validate slug uniqueness and user count constraints
    API-->>SysAdmin: tenant operation result

    Admin->>FE: Manage companies
    FE->>API: GET/POST/PUT/DELETE /api/v1/companies...
    API->>TENANT: Require admin or system_admin role
    API->>DB: Query and persist company/user assignment changes
    API-->>Admin: company operation result

    Note over SysAdmin,Manager: User administration with role hierarchy
    Manager->>FE: Create or update user
    FE->>API: POST or PUT /api/v1/users...
    API->>TENANT: Resolve tenant scope and manager role bounds
    API->>DB: Validate target role, tenant assignment, uniqueness
    alt Allowed by hierarchy and scope
        API->>DB: Persist user create/update
        API-->>Manager: success
    else Violates role hierarchy or tenant scope
        API-->>Manager: 403 or 400
    end

    Admin->>FE: Deactivate user
    FE->>API: DELETE /api/v1/users/{user_id}
    API->>TENANT: Validate cannot delete self and role constraints
    API->>DB: Soft-delete via is_active=false
    API-->>Admin: 204
```
