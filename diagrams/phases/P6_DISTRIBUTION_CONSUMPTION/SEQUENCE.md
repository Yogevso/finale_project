# P6: Distribution and Consumption (Endpoint-Level Phase Pack)

## Scope

Phase `P6` covers runtime content delivery across public, customer, and internal channels, including attachment access paths.

## Endpoint Inventory

| Channel | Method | Endpoint | Guard |
|---|---|---|---|
| Public | `GET` | `/public/documents` | `visibility=public` and `status=active` |
| Public | `GET` | `/public/documents/{document_id}` | same as above |
| Public | `GET` | `/public/search` | same as above |
| Public | `GET` | `/public/categories`, `/public/topics`, `/public/stats`, `/public/platforms/history` | public filters |
| Public | `GET` | `/public/documents/{document_id}/attachments/{attachment_id}` | public doc required |
| Viewer | `GET` | `/viewer/documents` and `/viewer/documents/{id}` | active docs only |
| Viewer | `GET` | `/viewer/documents/{id}/versions`, `/attachments`, `/comments` | active docs only |
| Customer | `GET` | `/portal/documents` | customer role + active + visibility rules |
| Customer | `GET` | `/portal/documents/{id}` | customer role + access check |
| Customer | `GET` | `/portal/search`, `/portal/categories`, `/portal/dashboard/stats` | customer role |
| Customer | `GET` | `/portal/documents/{id}/attachments/{attachment_id}` | access and status checks |

## Domain Class Diagram

```mermaid
classDiagram
    class PublicContentController {
        +listPublicDocuments(filters)
        +getPublicDocument(documentId)
        +searchPublic(query)
        +getPublicTaxonomy()
        +getPublicAttachment(documentId, attachmentId)
    }
    class ViewerContentController {
        +listViewerDocuments(filters)
        +getViewerDocument(documentId)
        +getViewerVersions(documentId)
        +getViewerAttachments(documentId)
        +getViewerComments(documentId)
    }
    class PortalContentController {
        +listPortalDocuments(filters)
        +getPortalDocument(documentId)
        +searchPortal(query)
        +getPortalCategories()
        +getPortalStats()
        +getPortalAttachment(documentId, attachmentId)
    }
    class DistributionQueryService {
        +getActivePublicDocuments(filters)
        +getActiveScopedDocuments(actor, filters)
        +resolveLatestPublishedVersion(documentId)
    }
    class VisibilityPolicyService {
        +isPubliclyVisible(document)
        +isCustomerVisible(actor, document)
        +isViewerVisible(actor, document)
        +canDownloadAttachment(actor, document, attachment)
    }
    class SearchService {
        +searchPublicIndex(query)
        +searchPortalIndex(actor, query)
    }
    class Document {
        +UUID id
        +String title
        +String status
        +String visibility
        +UUID tenant_id
    }
    class DocumentVersion {
        +UUID id
        +UUID document_id
        +Boolean is_published
        +DateTime published_at
    }
    class Attachment {
        +UUID id
        +UUID document_id
        +String storage_path
        +String mime_type
    }
    class DocumentCompanyAssignment {
        +UUID document_id
        +UUID company_id
    }

    PublicContentController --> DistributionQueryService
    ViewerContentController --> DistributionQueryService
    PortalContentController --> DistributionQueryService
    PortalContentController --> VisibilityPolicyService
    PublicContentController --> VisibilityPolicyService
    ViewerContentController --> VisibilityPolicyService
    PublicContentController --> SearchService
    PortalContentController --> SearchService
    DistributionQueryService --> Document
    DistributionQueryService --> DocumentVersion
    DistributionQueryService --> Attachment
    VisibilityPolicyService --> DocumentCompanyAssignment
    Document "1" --> "0..*" DocumentVersion
    Document "1" --> "0..*" Attachment
    Document "1" --> "0..*" DocumentCompanyAssignment
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Request enters distribution layer] --> B{Channel type?}

    B -- Public --> C[Enforce document status active]
    C --> D[Enforce visibility public]
    D --> E[Return catalog/search/detail]
    E --> F{Attachment requested?}
    F -- No --> G[End response]
    F -- Yes --> H[Re-check public document + attachment ownership]
    H --> G

    B -- Customer --> I[Validate customer role + auth token]
    I --> J[Resolve customer tenant/company context]
    J --> K[Filter to active docs where visibility public or assigned company]
    K --> L[Return portal list/detail/search]
    L --> M{Attachment requested?}
    M -- No --> N[End response]
    M -- Yes --> O[Re-check access and active status then stream URL]
    O --> N

    B -- Internal Viewer --> P[Validate internal viewer role]
    P --> Q[Filter to active docs in tenant scope]
    Q --> R[Return viewer list/detail/versions/comments]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Public as Public User
    actor Customer as Customer
    actor Internal as Internal User
    participant FE as Frontend
    participant PUBLICAPI as Public and Viewer APIs
    participant PORTAL as Portal APIs
    participant ACL as Access and Visibility Logic
    participant DB as Database

    par Public channel
        Public->>FE: Browse catalog
        FE->>PUBLICAPI: GET /api/v1/public/documents and /public/topics
        PUBLICAPI->>DB: Query status=active and visibility=public
        PUBLICAPI-->>Public: public docs and topic metadata

        Public->>FE: Open doc and search
        FE->>PUBLICAPI: GET /api/v1/public/documents/{id} and /public/search
        PUBLICAPI->>DB: Load latest published version and filters
        PUBLICAPI-->>Public: content, snippets, attachment metadata
    and Customer channel
        Customer->>FE: Open portal docs
        FE->>PORTAL: GET /api/v1/portal/documents
        PORTAL->>ACL: require_customer plus tenant visibility checks
        PORTAL->>DB: Query active docs where visibility is public or assigned company
        PORTAL-->>Customer: scoped document list

        Customer->>FE: Open document and download attachment
        FE->>PORTAL: GET /api/v1/portal/documents/{id}
        PORTAL->>ACL: verify access to visibility and assignment
        PORTAL->>DB: Load latest published version and attachments
        PORTAL-->>Customer: scoped document detail
        FE->>PORTAL: GET /api/v1/portal/documents/{id}/attachments/{attachment_id}
        PORTAL->>ACL: re-check access and active status
        PORTAL-->>Customer: download URL mapping to attachment endpoint
    and Internal viewer channel
        Internal->>FE: Browse viewer endpoints
        FE->>PUBLICAPI: GET /api/v1/viewer/documents and /viewer/documents/{id}
        PUBLICAPI->>DB: Query active documents
        PUBLICAPI-->>Internal: viewer-friendly results
    end
```
