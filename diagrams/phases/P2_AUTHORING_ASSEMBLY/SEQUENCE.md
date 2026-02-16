# P2: Authoring and Content Assembly (Endpoint-Level Phase Pack)

## Scope

Phase `P2` covers internal content creation, metadata updates, version drafting, attachments, comments, and company assignment.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/documents` | Editor+ | `require_editor` + tenant context |
| `POST` | `/documents/upload` | Editor+ | file/type/size checks |
| `POST` | `/documents/{id}/generate-word` | Editor+ | document access check |
| `GET` | `/documents` | Internal user | `require_internal_user` |
| `GET` | `/documents/{id}` | Internal user | tenant-scoped |
| `PUT` | `/documents/{id}` | Editor+ | content update and versioning rules |
| `POST` | `/documents/{id}/assign-companies` | Manager+ (permission) | `assign_companies` |
| `DELETE` | `/documents/{id}/assign-companies/{company_id}` | Manager+ (permission) | `assign_companies` |
| `POST` | `/documents/{id}/versions` | Editor+ | blocks if pending review exists |
| `PATCH` | `/documents/{id}/versions/{version_id}` | Editor+ | cannot edit published/approved/pending-review version |
| `POST` | `/documents/{id}/attachments` | Authenticated internal role with service checks | upload constraints |
| `GET` | `/documents/{id}/attachments...` | Authenticated user | access and metadata checks |
| `POST` | `/documents/{id}/comments` | Authenticated user | role-based visibility rules in service |
| `PATCH` | `/documents/{id}/comments/{comment_id}` | Author or admin/editor for resolve | ownership/role checks |
| `POST` | `/documents/{id}/comments/{comment_id}/resolve` | Admin/Editor | resolve-only operation |

## Domain Class Diagram

```mermaid
classDiagram
    class DocumentController {
        +createDocument(payload)
        +listDocuments(filters)
        +getDocument(id)
        +updateDocument(id, payload)
        +assignCompanies(id, companyIds)
        +unassignCompany(id, companyId)
        +generateWord(id)
    }
    class VersionController {
        +createVersion(documentId, payload)
        +updateVersion(documentId, versionId, payload)
        +getVersions(documentId)
    }
    class AttachmentController {
        +uploadAttachment(documentId, file)
        +listAttachments(documentId)
        +getAttachment(documentId, attachmentId)
    }
    class CommentController {
        +createComment(documentId, payload)
        +updateComment(documentId, commentId, payload)
        +resolveComment(documentId, commentId)
    }
    class DocumentService {
        +createDraft(actor, payload)
        +updateDraft(actor, documentId, payload)
        +validateVisibilityAndScope(actor, documentId)
    }
    class VersionService {
        +createDraftVersion(actor, documentId)
        +updateDraftVersion(actor, documentId, versionId, payload)
        +assertVersionEditable(version)
    }
    class AttachmentService {
        +storeFile(documentId, file)
        +generateWordArtifact(documentId)
        +buildDownloadReference(attachment)
    }
    class CommentService {
        +createThreadEntry(actor, documentId, payload)
        +updateThreadEntry(actor, commentId, payload)
        +resolveThread(actor, commentId)
    }
    class PermissionService {
        +requireEditor(actor)
        +requireInternalUser(actor)
        +requirePermission(actor, permission)
    }
    class Document {
        +UUID id
        +UUID tenant_id
        +UUID company_id
        +String title
        +String status
        +String visibility
        +UUID created_by
    }
    class DocumentVersion {
        +UUID id
        +UUID document_id
        +String version_label
        +Boolean is_published
        +String review_status
        +UUID created_by
    }
    class Attachment {
        +UUID id
        +UUID document_id
        +String storage_path
        +String mime_type
        +Integer size_bytes
        +UUID uploaded_by
    }
    class Comment {
        +UUID id
        +UUID document_id
        +UUID author_id
        +UUID parent_id
        +String body
        +Boolean resolved
    }
    class DocumentCompanyAssignment {
        +UUID document_id
        +UUID company_id
        +UUID assigned_by
    }

    DocumentController --> DocumentService
    VersionController --> VersionService
    AttachmentController --> AttachmentService
    CommentController --> CommentService
    DocumentService --> PermissionService
    VersionService --> PermissionService
    AttachmentService --> PermissionService
    CommentService --> PermissionService
    DocumentService --> Document
    VersionService --> DocumentVersion
    AttachmentService --> Attachment
    CommentService --> Comment
    Document "1" --> "0..*" DocumentVersion
    Document "1" --> "0..*" Attachment
    Document "1" --> "0..*" Comment
    Document "1" --> "0..*" DocumentCompanyAssignment
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Editor starts authoring] --> B{Editor role and tenant scope valid?}
    B -- No --> B1[Reject 403]
    B -- Yes --> C[Create document shell + initial draft version]
    C --> D[Update metadata, visibility, and structured content]
    D --> E{Pending review already exists?}
    E -- Yes --> E1[Block new version 409]
    E -- No --> F[Create additional draft version]
    F --> G{Version is published or in review terminal lock?}
    G -- Yes --> G1[Block edits 400 or 409]
    G -- No --> H[Persist version patch]

    H --> I[Upload attachments]
    I --> J{File type and size pass service rules?}
    J -- No --> J1[Reject upload 400]
    J -- Yes --> K[Persist blob and attachment metadata]
    K --> L[Optional generated Word artifact]

    L --> M[Collaborators create comments/replies]
    M --> N{Author or privileged actor editing/resolving?}
    N -- No --> N1[Reject comment update 403]
    N -- Yes --> O[Persist comment mutation and resolution flags]

    O --> P[Manager/Admin assigns document to companies]
    P --> Q{assign_companies permission granted?}
    Q -- No --> Q1[Reject assignment 403]
    Q -- Yes --> R[Persist company linkage and access scope]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Editor as Editor
    actor Manager as Manager or Admin
    actor Internal as Internal Collaborator
    participant FE as Frontend
    participant DOCAPI as Documents and Versions APIs
    participant ATT as Attachments API
    participant COM as Comments API
    participant PERM as Permission and Tenant Guards
    participant STORE as Storage Backend
    participant DB as Database

    Note over Editor,Internal: Draft document creation and metadata lifecycle
    Editor->>FE: Create document
    FE->>DOCAPI: POST /api/v1/documents
    DOCAPI->>PERM: require_editor plus tenant context
    DOCAPI->>DB: Insert document and initial version
    DOCAPI-->>Editor: document created

    Editor->>FE: Update document metadata/content
    FE->>DOCAPI: PUT /api/v1/documents/{document_id}
    DOCAPI->>PERM: require_editor plus document access
    DOCAPI->>DB: Update document and version fields
    DOCAPI-->>Editor: updated payload

    Editor->>FE: Add draft version
    FE->>DOCAPI: POST /api/v1/documents/{document_id}/versions
    DOCAPI->>PERM: role must be editor or above
    DOCAPI->>DB: Check pending review conflict
    alt No pending review
        DOCAPI->>DB: Insert next semantic/unpublished version
        DOCAPI-->>Editor: created version
    else Pending review exists
        DOCAPI-->>Editor: 409 conflict
    end

    Editor->>FE: Modify version
    FE->>DOCAPI: PATCH /api/v1/documents/{document_id}/versions/{version_id}
    DOCAPI->>DB: Validate not published and not pending/approved review state
    alt Editable
        DOCAPI->>DB: Persist version changes
        DOCAPI-->>Editor: updated version
    else Blocked by immutability/workflow
        DOCAPI-->>Editor: 400 or 409
    end

    Note over Editor,Internal: Attachments and generated artifacts
    Editor->>FE: Upload attachment
    FE->>ATT: POST /api/v1/documents/{document_id}/attachments
    ATT->>PERM: authenticated access and service-level role checks
    ATT->>STORE: Save file blob
    STORE-->>ATT: storage path and metadata
    ATT->>DB: Insert attachment row
    ATT-->>Editor: upload response with download URL

    Editor->>FE: Generate Word attachment
    FE->>DOCAPI: POST /api/v1/documents/{document_id}/generate-word
    DOCAPI->>PERM: require_editor and document access
    DOCAPI->>STORE: Persist generated docx bytes
    DOCAPI->>DB: Insert generated attachment metadata
    DOCAPI-->>Editor: generated attachment response

    Note over Editor,Internal: Commenting and thread resolution
    Internal->>FE: Add comment or reply
    FE->>COM: POST /api/v1/documents/{document_id}/comments
    COM->>PERM: authenticated user
    COM->>DB: Insert comment and visibility fields
    COM-->>Internal: comment response

    Internal->>FE: Resolve or edit thread
    FE->>COM: PATCH /api/v1/documents/{document_id}/comments/{comment_id}
    COM->>DB: Validate author/edit/resolve privileges
    COM->>DB: Persist update or resolution
    COM-->>Internal: updated comment

    Note over Editor,Internal: Company assignment for company-visible docs
    Manager->>FE: Assign companies to document
    FE->>DOCAPI: POST /api/v1/documents/{document_id}/assign-companies
    DOCAPI->>PERM: require_permission(assign_companies)
    DOCAPI->>DB: Validate company ids and attach associations
    DOCAPI-->>Manager: assignment success
```
