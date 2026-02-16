# P1: Governance and Setup - Flow Diagram

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
