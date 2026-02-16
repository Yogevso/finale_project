# P7: Feedback, Analytics, and Audit - Use Case Diagram

## Actors

- `Customer`
- `Manager`
- `Admin`
- `System Admin`
- `Any Authenticated User`
- `Analytics Pipeline`

## Regular Use Cases

1. Customer submits feedback for accessible document.
2. Customer tracks own feedback status.
3. Manager/admin views internal feedback queue.
4. Manager/admin responds and updates feedback status.
5. Users read and manage personal notifications.
6. Manager/admin/system admin opens analytics dashboards.
7. Manager/admin exports analytics reports.
8. System admin reviews cross-tenant analytics.

## Extreme and Edge Use Cases

1. Feedback spam or abuse from compromised accounts.
2. Unauthorized feedback response attempt by non-contributor.
3. Notification count drift or unread mismatch.
4. Analytics export requested outside allowed role/scope.
5. Data skew from late or malformed telemetry events.
6. Long-running export timeout or partial download failure.
7. Cross-tenant analytics data leak attempt.

```mermaid
flowchart LR
    CU[Customer]
    MG[Manager]
    AD[Admin]
    SA[System Admin]
    AU[Any Authenticated User]
    AP[Analytics Pipeline]

    UC1((Submit Feedback))
    UC2((View Own Feedback))
    UC3((Review Feedback Queue))
    UC4((Respond or Update Feedback Status))
    UC5((Read and Manage Notifications))
    UC6((View Analytics Dashboards))
    UC7((Export Analytics Reports))
    UC8((View Cross-Tenant Analytics))

    EX1((Throttle or Block Feedback Spam))
    EX2((Reject Unauthorized Feedback Action))
    EX3((Reconcile Notification Counters))
    EX4((Reject Unauthorized Export))
    EX5((Detect Analytics Data Quality Issues))
    EX6((Retry or Resume Failed Export))

    CU --> UC1
    CU --> UC2
    MG --> UC3
    AD --> UC3
    MG --> UC4
    AD --> UC4
    AU --> UC5
    MG --> UC6
    AD --> UC6
    SA --> UC6
    MG --> UC7
    AD --> UC7
    SA --> UC8
    AP --> EX5

    UC4 -. include .-> UC3
    UC7 -. include .-> UC6
    UC8 -. include .-> UC6
    EX1 -. extend .-> UC1
    EX2 -. extend .-> UC4
    EX3 -. extend .-> UC5
    EX4 -. extend .-> UC7
    EX5 -. extend .-> UC6
    EX6 -. extend .-> UC7
```
