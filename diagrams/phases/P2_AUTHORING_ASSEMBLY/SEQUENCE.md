# P2: Authoring and Content Assembly (Endpoint-Level Phase Pack)

## Scope

Phase `P2` covers internal authoring operations: document lifecycle, version drafting/mutation, attachment handling, comments, and company assignment.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/documents` | Editor+ | `require_editor` + tenant-context document scope |
| `GET` | `/documents` | Internal users | `require_internal_user` + tenant-scoped query |
| `GET` | `/documents/{id}` | Internal users | `require_internal_user` + tenant-scoped lookup |
| `PUT` | `/documents/{id}` | Editor+ | `require_editor` + tenant-scoped access |
| `DELETE` | `/documents/{id}` | Manager+ | `require_manager` + tenant-scoped access |
| `POST` | `/documents/upload` | Editor+ | `require_editor`, upload validation, attachment write |
| `POST` | `/documents/{id}/generate-word` | Editor+ | `require_editor` + document access check |
| `GET` | `/documents/{id}/assigned-companies` | Internal users | `require_internal_user` |
| `POST/DELETE` | `/documents/{id}/assign-companies...` | Permission holders | `require_permission(assign_companies)` |
| `GET` | `/documents/{id}/versions`, `/documents/{id}/versions/{version_id}` | Authenticated users | Auth required (no explicit tenant guard in service) |
| `POST` | `/documents/{id}/versions` | Editor+ | Role check + blocked while any review is pending |
| `PATCH` | `/documents/{id}/versions/{version_id}` | Editor+ | Role check + cannot edit published/pending/approved version |
| `POST` | `/documents/{id}/versions/{version_id}/publish` | Manager+ | Role check + approved review required |
| `DELETE` | `/documents/{id}/versions/{version_id}` | Manager+ | Role check + unpublished only |
| `GET` | `/documents/{id}/attachments...` | Authenticated users | Auth required (download also accepts `?token=` query token) |
| `POST` | `/documents/{id}/attachments` | Admin, Manager, Editor, System Admin | Role check + type/size constraints |
| `DELETE` | `/documents/{id}/attachments/{attachment_id}` | Admin | Admin-only delete in service |
| `GET` | `/documents/{id}/comments...` | Authenticated users | Auth required + contributor-based visibility filtering |
| `POST` | `/documents/{id}/comments` | Authenticated users | Document existence check |
| `PATCH` | `/documents/{id}/comments/{comment_id}` | Author or admin/editor/manager | Content and resolve permission checks |
| `POST` | `/documents/{id}/comments/{comment_id}/resolve` | Admin, Manager, Editor | Resolve via comment update service |
| `DELETE` | `/documents/{id}/comments/{comment_id}` | Author, Admin, Manager, System Admin | Delete permission checks |

## Domain Class Diagram

```mermaid
classDiagram
    class DocumentRouter {
        +POST /documents
        +GET /documents
        +GET /documents/{document_id}
        +PUT /documents/{document_id}
        +DELETE /documents/{document_id}
        +POST /documents/upload
        +POST /documents/{document_id}/generate-word
        +POST /documents/{document_id}/assign-companies
    }

    class VersionRouter {
        +GET /documents/{document_id}/versions
        +POST /documents/{document_id}/versions
        +PATCH /documents/{document_id}/versions/{version_id}
        +POST /documents/{document_id}/versions/{version_id}/publish
        +DELETE /documents/{document_id}/versions/{version_id}
    }

    class AttachmentRouter {
        +GET /documents/{document_id}/attachments
        +GET /documents/{document_id}/attachments/{attachment_id}/download
        +GET /documents/{document_id}/attachments/{attachment_id}/reader-view
        +POST /documents/{document_id}/attachments
        +DELETE /documents/{document_id}/attachments/{attachment_id}
    }

    class CommentRouter {
        +GET /documents/{document_id}/comments
        +POST /documents/{document_id}/comments
        +PATCH /documents/{document_id}/comments/{comment_id}
        +POST /documents/{document_id}/comments/{comment_id}/resolve
        +DELETE /documents/{document_id}/comments/{comment_id}
    }

    class DocumentService {
        +create_document(...)
        +get_documents(...)
        +get_document(...)
        +update_document(...)
        +delete_document(...)
    }

    class VersionService {
        +create_version(...)
        +update_version(...)
        +publish_version(...)
        +delete_version(...)
    }

    class AttachmentService {
        +upload_attachment(...)
        +create_attachment_from_bytes(...)
        +get_reader_view(...)
        +delete_attachment(...)
    }

    class CommentService {
        +get_comments(...)
        +create_comment(...)
        +update_comment(...)
        +delete_comment(...)
    }

    class Document {
        +id: int
        +tenant_id: int?
        +document_number: str
        +status: DocumentStatus
        +visibility: DocumentVisibility
    }

    class Version {
        +id: int
        +document_id: int
        +version_number: int
        +semantic_version: str?
        +is_published: bool
    }

    class ReviewRequest {
        +document_id: int
        +version_id: int?
        +status: ReviewStatus
    }

    class Attachment {
        +id: int
        +document_id: int
        +mime_type: str
        +size_bytes: int?
        +sha256: str?
        +reader_html_status: str?
    }

    class Comment {
        +id: int
        +document_id: int
        +user_id: int
        +parent_id: int?
        +is_private: bool
        +is_resolved: bool
    }

    DocumentRouter --> DocumentService
    VersionRouter --> VersionService
    AttachmentRouter --> AttachmentService
    CommentRouter --> CommentService
    DocumentService --> Document
    VersionService --> Version
    VersionService --> ReviewRequest
    AttachmentService --> Attachment
    CommentService --> Comment
    Document "1" --> "0..*" Version
    Document "1" --> "0..*" Attachment
    Document "1" --> "0..*" Comment
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Editor creates document] --> B{Editor and tenant scope valid?}
    B -- No --> B1[403 denied]
    B -- Yes --> C[Persist document and initial version 1.0.0]

    C --> D[Editor updates document fields]
    D --> E{Visibility changed by manager+?}
    E -- No --> E1[403 if unauthorized visibility change]
    E -- Yes --> F[Apply visibility mutation]
    E1 --> G
    F --> G
    G --> H{Any tracked change applied?}
    H -- Yes --> I[Create patch version row]
    H -- No --> J[No version row created]

    I --> K[Version workflow]
    J --> K
    K --> L{Pending review exists for document?}
    L -- Yes --> L1[Block new version 409]
    L -- No --> M[Create next version]
    M --> N{Update target version is published/pending/approved?}
    N -- Yes --> N1[400 or 409]
    N -- No --> O[Persist version mutation]

    O --> P{Publish requested with approved review?}
    P -- No --> Q[Keep draft workflow]
    P -- Yes --> R[Mark version published and document active]

    R --> S[Attachment flow]
    Q --> S
    S --> T{Upload role allowed and file valid?}
    T -- No --> T1[403 or 400]
    T -- Yes --> U[Store binary and metadata]
    U --> V{PDF attachment?}
    V -- Yes --> V1[Queue reader-view generation]
    V -- No --> W[Skip reader artifact]
    V1 --> W

    W --> X[Comment flow]
    X --> Y[Create thread or reply]
    Y --> Z{Update/resolve permissions satisfied?}
    Z -- No --> Z1[403 denied]
    Z -- Yes --> AA[Persist comment change]

    AA --> AB[Assign companies]
    AB --> AC{assign_companies permission granted?}
    AC -- No --> AC1[403 denied]
    AC -- Yes --> AD[Persist company assignment links]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Editor as Editor
    actor Manager as Manager or Admin
    actor User as Authenticated User
    participant FE as Frontend
    participant DOC as Documents API
    participant VER as Versions API
    participant ATT as Attachments API
    participant COM as Comments API
    participant SVC as Domain Services
    participant DB as Database
    participant REV as Reviews API

    Note over Editor,User: Document creation and metadata lifecycle
    Editor->>FE: Create document
    FE->>DOC: POST /api/v1/documents
    DOC->>SVC: DocumentService.create_document
    SVC->>DB: Insert document and initial version
    DOC-->>Editor: 201 document payload

    Editor->>FE: Update document
    FE->>DOC: PUT /api/v1/documents/{document_id}
    DOC->>SVC: DocumentService.update_document
    SVC->>DB: Update fields and create patch version when changed
    DOC-->>Editor: updated document

    Note over Editor,User: Version workflow and review gating
    Editor->>FE: Create version
    FE->>VER: POST /api/v1/documents/{document_id}/versions
    VER->>SVC: VersionService.create_version
    SVC->>DB: Check pending review and insert next version
    VER-->>Editor: created version or 409

    Editor->>FE: Update version
    FE->>VER: PATCH /api/v1/documents/{document_id}/versions/{version_id}
    VER->>SVC: VersionService.update_version
    SVC->>DB: Reject published/pending/approved states or persist update
    VER-->>Editor: updated version or 400/409

    Manager->>FE: Publish version
    FE->>VER: POST /api/v1/documents/{document_id}/versions/{version_id}/publish
    VER->>SVC: VersionService.publish_version
    SVC->>DB: Require approved review for this version
    alt Approved review exists
        SVC->>DB: Mark version published and document status active
        VER-->>Manager: published version
    else Missing or invalid review state
        VER-->>Manager: 409 conflict
    end

    Note over Editor,User: Attachment processing
    Editor->>FE: Upload attachment
    FE->>ATT: POST /api/v1/documents/{document_id}/attachments
    ATT->>SVC: AttachmentService.upload_attachment
    SVC->>DB: Validate role and create attachment metadata
    SVC->>DB: Queue reader artifact generation for PDF
    ATT-->>Editor: upload response with checksum

    User->>FE: Download or preview attachment
    FE->>ATT: GET /api/v1/documents/{document_id}/attachments/{attachment_id}/download
    ATT->>SVC: open_original_stream
    ATT-->>User: streamed original bytes

    Note over Editor,User: Comments and assignments
    User->>FE: Create comment
    FE->>COM: POST /api/v1/documents/{document_id}/comments
    COM->>SVC: CommentService.create_comment
    SVC->>DB: Insert comment or reply
    COM-->>User: comment payload

    User->>FE: Update or resolve comment
    FE->>COM: PATCH /api/v1/documents/{document_id}/comments/{comment_id}
    COM->>SVC: CommentService.update_comment
    SVC->>DB: Enforce author/admin rules then persist
    COM-->>User: updated comment or 403

    Manager->>FE: Assign companies
    FE->>DOC: POST /api/v1/documents/{document_id}/assign-companies
    DOC->>DB: Validate company IDs and write assignments
    DOC-->>Manager: assignment result

    Editor->>FE: Submit review (outside P2 core but required for publish)
    FE->>REV: POST /api/v1/reviews/documents/{document_id}/submit
    REV-->>Editor: pending review
```
