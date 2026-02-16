# P1: Governance and Setup - Use Case Diagram

## Actors

- `System Admin`
- `Admin`
- `Manager`
- `Platform Auditor`

## Regular Use Cases

1. System admin reads and updates RBAC policies.
2. System admin publishes active policy set.
3. System admin updates global system settings.
4. System admin manages tenants.
5. Admin manages companies within authorized scope.
6. Manager/admin manages users based on role hierarchy.
7. Auditor reviews governance and configuration audit logs.

## Extreme and Edge Use Cases

1. Policy publish introduces conflict or denies critical access.
2. Actor attempts cross-tenant management action without scope.
3. Manager attempts to create user above allowed role.
4. Tenant deletion requested while active dependencies exist.
5. Concurrent policy edits race and cause stale writes.
6. Admin attempts self-deactivation or privileged lockout scenario.
7. Invalid setting key/value type submitted.

```mermaid
flowchart LR
    SA[System Admin]
    AD[Admin]
    MG[Manager]
    AU[Platform Auditor]

    UC1((Manage RBAC Policies))
    UC2((Publish Policies))
    UC3((Manage System Settings))
    UC4((Manage Tenants))
    UC5((Manage Companies))
    UC6((Manage Users))
    UC7((Review Governance Audit))

    EX1((Detect Policy Conflict))
    EX2((Block Cross-Tenant Action))
    EX3((Block Role Hierarchy Violation))
    EX4((Reject Destructive Tenant Delete))
    EX5((Prevent Config Lockout))

    SA --> UC1
    SA --> UC2
    SA --> UC3
    SA --> UC4
    AD --> UC5
    SA --> UC5
    MG --> UC6
    AD --> UC6
    SA --> UC6
    AU --> UC7

    UC2 -. include .-> UC1
    UC6 -. include .-> UC5
    EX1 -. extend .-> UC2
    EX2 -. extend .-> UC4
    EX2 -. extend .-> UC5
    EX2 -. extend .-> UC6
    EX3 -. extend .-> UC6
    EX4 -. extend .-> UC4
    EX5 -. extend .-> UC3
```
