# P7: Feedback, Analytics, and Audit (Endpoint-Level Phase Pack)

## Scope

Phase `P7` covers feedback loops, internal response workflows, notification consumption, analytics reporting, and export flows.

## Endpoint Inventory

| Domain | Method | Endpoint | Guard |
|---|---|---|---|
| Portal feedback | `POST` | `/portal/feedback` | customer role + doc access |
| Portal feedback | `GET` | `/portal/feedback`, `/portal/feedback/{id}` | own feedback only |
| Mgmt feedback | `GET` | `/feedback`, `/feedback/{id}` | internal role + contributor visibility |
| Mgmt feedback | `POST` | `/feedback/{id}/respond` | admin/manager + contributor visibility |
| Mgmt feedback | `PUT` | `/feedback/{id}/status` | internal role + contributor visibility |
| Mgmt feedback | `GET` | `/feedback/stats/summary` | admin/manager/system_admin |
| Notifications | `GET` | `/notifications`, `/notifications/count` | current user |
| Notifications | `POST` | `/notifications/read`, `/notifications/{id}/read` | current user |
| Notifications | `DELETE` | `/notifications/{id}`, `/notifications` | current user |
| Analytics | `GET` | `/analytics/overview`, `/engagement`, `/content`, `/feedback`, `/recent-activity` | manager+ |
| Analytics | `GET` | `/analytics/users` | admin+ |
| Analytics | `GET` | `/analytics/tenants` | system_admin |
| Analytics export | `GET` | `/analytics/export/csv`, `/analytics/export/pdf` | manager+ |

## Domain Class Diagram

```mermaid
classDiagram
    class PortalFeedbackController {
        +createFeedback(payload)
        +listMyFeedback(filters)
        +getMyFeedback(feedbackId)
    }
    class ManagementFeedbackController {
        +listFeedback(filters)
        +getFeedback(feedbackId)
        +respondFeedback(feedbackId, payload)
        +updateFeedbackStatus(feedbackId, payload)
        +getFeedbackSummaryStats()
    }
    class NotificationController {
        +listNotifications(filters)
        +getUnreadCount()
        +markAllRead()
        +markRead(notificationId)
        +deleteNotification(notificationId)
        +clearNotifications()
    }
    class AnalyticsController {
        +getOverview(filters)
        +getEngagement(filters)
        +getContentMetrics(filters)
        +getFeedbackMetrics(filters)
        +getRecentActivity(filters)
        +getUserMetrics(filters)
        +getTenantMetrics(filters)
        +exportCsv(filters)
        +exportPdf(filters)
    }
    class FeedbackService {
        +createCustomerFeedback(actor, payload)
        +respondInternal(actor, feedbackId, payload)
        +updateStatus(actor, feedbackId, status)
        +assertContributorVisibility(actor, feedback)
    }
    class NotificationService {
        +emitFeedbackCreated(feedback)
        +emitFeedbackResponded(feedback)
        +listForUser(actor)
        +markRead(actor, notificationId)
    }
    class AnalyticsService {
        +aggregateTenantScopedMetrics(actor, filters)
        +aggregateGlobalMetrics(actor, filters)
        +buildExportDataset(actor, filters)
    }
    class AuditService {
        +logFeedbackAction(actor, action, feedbackId)
        +logAnalyticsExport(actor, format)
    }
    class Feedback {
        +UUID id
        +UUID document_id
        +UUID user_id
        +String status
        +String message
        +String response
        +DateTime created_at
        +DateTime responded_at
    }
    class Notification {
        +UUID id
        +UUID user_id
        +String type
        +Boolean is_read
        +DateTime created_at
        +DateTime read_at
    }
    class AnalyticsReport {
        +String report_type
        +String scope
        +String period
        +String format
    }
    class AuditEvent {
        +UUID id
        +UUID actor_id
        +String action
        +String target_type
        +UUID target_id
    }

    PortalFeedbackController --> FeedbackService
    ManagementFeedbackController --> FeedbackService
    ManagementFeedbackController --> NotificationService
    NotificationController --> NotificationService
    AnalyticsController --> AnalyticsService
    FeedbackService --> Feedback
    NotificationService --> Notification
    AnalyticsService --> AnalyticsReport
    FeedbackService --> AuditService
    AnalyticsService --> AuditService
    AuditService --> AuditEvent
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Customer submits feedback from portal] --> B{Customer role and document access valid?}
    B -- No --> B1[Reject feedback 403]
    B -- Yes --> C[Create feedback record status pending]
    C --> D[Emit internal notification for staff queue]

    D --> E[Manager/Admin opens feedback queue]
    E --> F{Contributor visibility and role valid?}
    F -- No --> F1[Hide item or reject 403]
    F -- Yes --> G[Respond to feedback and set responded status]
    G --> H[Notify customer with response event]
    H --> I[Optional status transitions: in_progress/resolved/closed]

    I --> J[Users consume notifications]
    J --> K[Mark individual or bulk notifications as read]
    K --> L[Optional notification cleanup]

    L --> M[Manager opens analytics dashboards]
    M --> N{Endpoint role gate passes?}
    N -- No --> N1[Reject analytics 403]
    N -- Yes --> O[Aggregate tenant-scoped metrics]
    O --> P[Export CSV/PDF reports]
    P --> Q[System admin views cross-tenant analytics]
    Q --> R[Feed insights into next authoring/governance cycle]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Customer
    actor Manager as Manager or Admin
    actor SysAdmin as System Admin
    actor AnyUser as Authenticated User
    participant FE as Frontend
    participant PORTAL as Portal Feedback API
    participant MGMTFB as Management Feedback API
    participant NOTIF as Notifications API
    participant ANALYTICS as Analytics API
    participant ACL as Permission and Contributor Checks
    participant DB as Database

    Note over Customer,SysAdmin: Customer feedback ingestion
    Customer->>FE: Submit feedback on document
    FE->>PORTAL: POST /api/v1/portal/feedback
    PORTAL->>ACL: require_customer plus document access checks
    PORTAL->>DB: Insert feedback with status=pending
    PORTAL-->>Customer: feedback created

    Customer->>FE: View own feedback
    FE->>PORTAL: GET /api/v1/portal/feedback and /portal/feedback/{id}
    PORTAL->>DB: Query by feedback.user_id=current_user.id
    PORTAL-->>Customer: own feedback timeline

    Note over Customer,SysAdmin: Internal response and contributor visibility
    Manager->>FE: Open feedback queue
    FE->>MGMTFB: GET /api/v1/feedback
    MGMTFB->>ACL: require_internal_staff plus contributor visibility
    MGMTFB->>DB: Query and filter visible feedback rows
    MGMTFB-->>Manager: visible queue

    Manager->>FE: Respond to feedback
    FE->>MGMTFB: POST /api/v1/feedback/{feedback_id}/respond
    MGMTFB->>ACL: require_admin_or_manager plus contributor visibility
    alt Allowed
        MGMTFB->>DB: Update response and set status=responded
        MGMTFB->>DB: Insert feedback_responded notification for customer
        MGMTFB-->>Manager: updated feedback payload
    else Not contributor or role mismatch
        MGMTFB-->>Manager: 403
    end

    Manager->>FE: Update feedback status
    FE->>MGMTFB: PUT /api/v1/feedback/{feedback_id}/status
    MGMTFB->>ACL: require_internal_staff plus contributor visibility
    MGMTFB->>DB: Persist status update
    MGMTFB-->>Manager: updated feedback payload

    Note over Customer,SysAdmin: Notification consumption loop
    AnyUser->>FE: Open notifications
    FE->>NOTIF: GET /api/v1/notifications and /notifications/count
    NOTIF->>DB: Query user-specific notifications and unread count
    NOTIF-->>AnyUser: notification list and counters

    AnyUser->>FE: Mark notifications read
    FE->>NOTIF: POST /api/v1/notifications/read or /notifications/{id}/read
    NOTIF->>DB: Update is_read/read_at
    NOTIF-->>AnyUser: read acknowledgment

    Note over Customer,SysAdmin: Analytics and reporting
    Manager->>FE: Open analytics dashboards
    FE->>ANALYTICS: GET /api/v1/analytics/overview and related endpoints
    ANALYTICS->>ACL: manager/admin/system_admin gates per endpoint
    ANALYTICS->>DB: Aggregate metrics with tenant context filters
    ANALYTICS-->>Manager: chart data and summaries

    Manager->>FE: Export report
    FE->>ANALYTICS: GET /api/v1/analytics/export/csv or /export/pdf
    ANALYTICS->>DB: Build report dataset
    ANALYTICS-->>Manager: streaming file response

    SysAdmin->>FE: View cross-tenant analytics
    FE->>ANALYTICS: GET /api/v1/analytics/tenants
    ANALYTICS->>ACL: require_system_admin
    ANALYTICS->>DB: Aggregate global tenant metrics
    ANALYTICS-->>SysAdmin: tenant health and comparisons
```
