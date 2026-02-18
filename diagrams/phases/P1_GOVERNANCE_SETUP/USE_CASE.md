# P1: Governance and Setup - Use Case Diagram

## Actors

- `System Admin`
- `Admin`
- `Manager`
- `Authenticated User (Self-Service Profile)`

## Regular Use Cases

1. System admin reads and updates RBAC policies.
2. System admin publishes dynamic RBAC policy set.
3. System admin updates global system settings.
4. System admin manages tenants and tenant user listings.
5. Admin/system admin manages companies (create, update, deactivate, search).
6. Admin/system admin manages company membership assignments.
7. Manager/admin/system admin manages users with role hierarchy and tenant rules.

## Extreme and Edge Use Cases

1. Tenant or company slug collision on create/update.
2. Tenant deletion requested while users still exist.
3. Manager/admin attempts to assign a role outside hierarchy limits.
4. User attempts self-deactivation or self-deletion.
5. Non-system actor attempts cross-tenant user access.
6. Admin attempts to deactivate own company.
7. Concurrent governance edits produce stale write risk (no optimistic locking).

```mermaid
flowchart LR
    SA[System Admin]
    AD[Admin]
    MG[Manager]
    SELF[Authenticated User]

    UC1((Manage RBAC Policies))
    UC2((Publish RBAC Policies))
    UC3((Manage System Settings))
    UC4((Manage Tenants))
    UC5((Manage Companies))
    UC6((Manage Company Membership))
    UC7((Manage Users))

    EX1((Reject Duplicate Slug))
    EX2((Block Tenant Delete With Users))
    EX3((Block Role Hierarchy Violation))
    EX4((Block Self Deactivation Or Delete))
    EX5((Block Cross Tenant User Access))
    EX6((Block Own Company Deactivation))
    EX7((Handle Governance Write Races))

    SA --> UC1
    SA --> UC2
    SA --> UC3
    SA --> UC4
    SA --> UC5
    AD --> UC5
    SA --> UC6
    AD --> UC6
    SA --> UC7
    AD --> UC7
    MG --> UC7
    SELF --> UC7

    UC2 -. include .-> UC1
    UC6 -. include .-> UC5

    EX1 -. extend .-> UC4
    EX1 -. extend .-> UC5
    EX2 -. extend .-> UC4
    EX3 -. extend .-> UC7
    EX4 -. extend .-> UC7
    EX5 -. extend .-> UC7
    EX6 -. extend .-> UC5
    EX7 -. extend .-> UC1
    EX7 -. extend .-> UC3
```
