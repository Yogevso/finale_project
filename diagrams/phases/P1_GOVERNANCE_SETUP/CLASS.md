# P1: Governance and Setup - Class Diagram

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
