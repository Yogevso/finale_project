# P2: Authoring and Content Assembly - Class Diagram

```mermaid
classDiagram
    class DocumentRouter {
        +create_document(payload)
        +list_documents(filters)
        +get_document(document_id)
        +update_document(document_id, payload)
        +delete_document(document_id)
        +upload_document(payload)
        +generate_word_attachment(document_id, payload)
        +get_assigned_companies(document_id)
        +assign_companies(document_id, payload)
        +remove_company_assignment(document_id, company_id)
    }

    class VersionRouter {
        +list_versions(document_id)
        +get_version(document_id, version_id)
        +create_version(document_id, payload)
        +update_version(document_id, version_id, payload)
        +publish_version(document_id, version_id)
        +delete_version(document_id, version_id)
    }

    class AttachmentRouter {
        +list_attachments(document_id)
        +get_attachment(document_id, attachment_id)
        +download_attachment(document_id, attachment_id)
        +preview_attachment(document_id, attachment_id)
        +get_attachment_outline(document_id, attachment_id)
        +get_attachment_reader_view(document_id, attachment_id)
        +upload_attachment(document_id, file)
        +delete_attachment(document_id, attachment_id)
    }

    class CommentRouter {
        +list_comments(document_id)
        +get_comment_stats(document_id)
        +get_comment(document_id, comment_id)
        +create_comment(document_id, payload)
        +update_comment(document_id, comment_id, payload)
        +resolve_comment(document_id, comment_id)
        +delete_comment(document_id, comment_id)
    }

    class DocumentService {
        +create_document(document_data, user)
        +get_documents(skip, limit, filters)
        +get_document(document_id)
        +update_document(document_id, document_data, user)
        +delete_document(document_id, user)
    }

    class VersionService {
        +create_version(document_id, version_data, user)
        +update_version(document_id, version_id, version_data, user)
        +publish_version(document_id, version_id, user)
        +delete_version(document_id, version_id, user)
    }

    class AttachmentService {
        +upload_attachment(document_id, file, user)
        +create_attachment_from_bytes(...)
        +get_reader_view(document_id, attachment_id, user)
        +get_pdf_outline(document_id, attachment_id, user)
        +open_original_stream(document_id, attachment_id, user)
        +delete_attachment(document_id, attachment_id, user)
    }

    class CommentService {
        +get_comments(document_id, user)
        +create_comment(document_id, payload, user)
        +update_comment(document_id, comment_id, payload, user)
        +delete_comment(document_id, comment_id, user)
    }

    class Document {
        +id: int
        +tenant_id: int?
        +title: str
        +document_number: str
        +status: DocumentStatus
        +visibility: DocumentVisibility
        +platform_id: int?
        +parent_id: int?
        +created_by: int
    }

    class Version {
        +id: int
        +document_id: int
        +version_number: int
        +semantic_version: str?
        +bump_type: VersionBumpType
        +content: str?
        +changes_summary: str?
        +is_published: bool
        +published_at: datetime?
        +published_by: int?
    }

    class ReviewRequest {
        +id: int
        +document_id: int
        +version_id: int?
        +status: ReviewStatus
    }

    class Attachment {
        +id: int
        +document_id: int
        +original_filename: str
        +mime_type: str
        +size_bytes: int?
        +sha256: str?
        +reader_html_status: str?
        +uploaded_by: int
    }

    class Comment {
        +id: int
        +document_id: int
        +user_id: int
        +parent_id: int?
        +content: str
        +is_private: bool
        +is_resolved: bool
    }

    class Tenant {
        +id: int
        +name: str
        +slug: str
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
    Document "0..*" --> "0..*" Tenant : assigned_companies
```
