# P5: Publish and Release (Endpoint-Level Phase Pack)

## Scope

Phase `P5` covers release publication of an approved version, immutability transition, active status exposure, and downstream notifications.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/documents/{document_id}/versions/{version_id}/publish` | Manager, Admin, System Admin | version exists, not published, approved review exists |
| `GET` | `/documents/{document_id}/versions` | Internal users | used to inspect release candidates |
| `GET` | `/documents/{document_id}/versions/{version_id}` | Internal users | verify target version metadata |
| `PATCH` | `/documents/{document_id}/versions/{version_id}` | Editor+ | blocked after publish |
| `DELETE` | `/documents/{document_id}/versions/{version_id}` | Manager+ | blocked after publish |

## Domain Class Diagram

```mermaid
classDiagram
    class PublishController {
        +listVersions(documentId)
        +getVersion(documentId, versionId)
        +publishVersion(documentId, versionId)
        +updateVersion(documentId, versionId, payload)
        +deleteVersion(documentId, versionId)
    }
    class PublishService {
        +publish(actor, documentId, versionId)
        +validatePublisherRole(actor)
        +validatePublishPreconditions(documentId, versionId)
        +markPublished(documentId, versionId, actor)
    }
    class VersionLifecyclePolicy {
        +requiresApprovedReview(versionId)
        +isAlreadyPublished(version)
        +isImmutable(version)
    }
    class NotificationService {
        +queuePublishEmail(document, version)
        +emitPublishEvent(document, version)
    }
    class AuditLogService {
        +logPublished(actor, documentId, versionId)
        +logImmutableViolation(actor, documentId, versionId, action)
    }
    class Document {
        +UUID id
        +String status
        +UUID active_version_id
        +DateTime updated_at
    }
    class DocumentVersion {
        +UUID id
        +UUID document_id
        +String version_label
        +Boolean is_published
        +UUID published_by
        +DateTime published_at
    }
    class ReviewRequest {
        +UUID id
        +UUID version_id
        +String status
        +DateTime decision_at
    }

    PublishController --> PublishService
    PublishService --> VersionLifecyclePolicy
    PublishService --> NotificationService
    PublishService --> AuditLogService
    PublishService --> Document
    PublishService --> DocumentVersion
    PublishService --> ReviewRequest
    Document "1" --> "0..*" DocumentVersion
    DocumentVersion "1" --> "0..*" ReviewRequest : reviewed_by
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Publisher opens version candidates] --> B[Load versions + latest review status]
    B --> C[Select target version]
    C --> D{Actor role is manager/admin/system_admin?}
    D -- No --> D1[Reject publish 403]
    D -- Yes --> E{Version exists and not already published?}
    E -- No --> E1[Reject publish 400 or 409]
    E -- Yes --> F{Latest review is approved?}
    F -- No --> F1[Reject publish 409]
    F -- Yes --> G[Mark version published with actor and timestamp]
    G --> H[Set document status active]
    H --> I[Set active_version pointer]
    I --> J[Emit publish notifications and audit]

    J --> K[Post-publish immutability checks]
    K --> L{Any patch/delete request on published version?}
    L -- No --> M[Continue serving active release]
    L -- Yes --> N[Reject mutation 400 and record immutable violation]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Publisher as Manager/Admin/System Admin
    actor Editor as Editor
    participant FE as Frontend
    participant VER as Versions API
    participant VERSVC as Version Service
    participant DB as Database
    participant MAIL as Email Service

    Publisher->>FE: Open version candidates
    FE->>VER: GET /api/v1/documents/{document_id}/versions
    VER->>VERSVC: get_versions
    VERSVC->>DB: Load versions and latest review per version
    VER-->>Publisher: version list with review status

    Publisher->>FE: Publish selected version
    FE->>VER: POST /api/v1/documents/{document_id}/versions/{version_id}/publish
    VER->>VERSVC: publish_version
    VERSVC->>DB: Validate version exists and is not already published
    VERSVC->>DB: Validate publisher role in manager/admin/system_admin
    VERSVC->>DB: Validate latest review exists and is approved
    alt Publish checks pass
        VERSVC->>DB: Set version.is_published=true, published_at, published_by
        VERSVC->>DB: Set document.status=active
        VERSVC->>MAIL: Queue optional publish email (if enabled)
        VERSVC-->>VER: serialized published version
        VER-->>Publisher: publish success payload
    else Check fails
        VER-->>Publisher: 400 or 403 or 409
    end

    Editor->>FE: Attempt to modify published version
    FE->>VER: PATCH or DELETE /api/v1/documents/{document_id}/versions/{version_id}
    VER->>VERSVC: update_version or delete_version
    VERSVC->>DB: Detect is_published=true
    VERSVC-->>VER: reject immutable operation
    VER-->>Editor: 400 cannot modify/delete published version
```
