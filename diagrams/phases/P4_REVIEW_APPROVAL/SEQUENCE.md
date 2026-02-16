# P4: Review and Approval (Endpoint-Level Phase Pack)

## Scope

Phase `P4` covers submission, reviewer queues, approval/rejection/cancellation, and review history retrieval.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/reviews/documents/{document_id}/submit` | Editor+ | draft status + no pending review |
| `GET` | `/reviews/pending` | Reviewer roles | excludes own submissions |
| `GET` | `/reviews/my-submissions` | Submitter | own submissions |
| `GET` | `/reviews/{review_id}` | Submitter/reviewer roles | access check |
| `POST` | `/reviews/{review_id}/approve` | Reviewer roles | no self-approval + stale-version checks |
| `POST` | `/reviews/{review_id}/reject` | Reviewer roles | no self-action |
| `POST` | `/reviews/{review_id}/cancel` | Submitter | pending only |
| `GET` | `/reviews/documents/{document_id}/history` | Internal reviewer context | document exists |

## Domain Class Diagram

```mermaid
classDiagram
    class ReviewController {
        +submitReview(documentId, payload)
        +listPendingReviews(filters)
        +listMySubmissions(filters)
        +getReview(reviewId)
        +approveReview(reviewId, payload)
        +rejectReview(reviewId, payload)
        +cancelReview(reviewId)
        +getDocumentReviewHistory(documentId)
    }
    class ReviewService {
        +submit(actor, documentId, versionId)
        +approve(actor, reviewId, comment)
        +reject(actor, reviewId, comment)
        +cancel(actor, reviewId)
        +assertTransition(review, action)
    }
    class ReviewQueueService {
        +getPendingForReviewer(actor)
        +excludeSelfSubmissions(items, actorId)
    }
    class ReviewerPolicyService {
        +canSubmit(actor, document)
        +canReview(actor, review)
        +preventSelfApproval(actor, review)
        +detectStaleVersion(review, document)
    }
    class NotificationService {
        +notifyReviewSubmitted(review)
        +notifyReviewApproved(review)
        +notifyReviewRejected(review)
    }
    class AuditLogService {
        +logReviewSubmitted(actor, review)
        +logReviewApproved(actor, review)
        +logReviewRejected(actor, review)
        +logReviewCancelled(actor, review)
    }
    class ReviewRequest {
        +UUID id
        +UUID document_id
        +UUID version_id
        +UUID submitted_by
        +UUID reviewed_by
        +String status
        +String submit_comment
        +String review_comment
        +DateTime submitted_at
        +DateTime decision_at
    }
    class Document {
        +UUID id
        +String status
        +UUID latest_version_id
    }
    class DocumentVersion {
        +UUID id
        +UUID document_id
        +Boolean is_published
        +String review_status
    }

    ReviewController --> ReviewService
    ReviewController --> ReviewQueueService
    ReviewService --> ReviewerPolicyService
    ReviewService --> NotificationService
    ReviewService --> AuditLogService
    ReviewService --> ReviewRequest
    ReviewService --> Document
    ReviewService --> DocumentVersion
    Document "1" --> "0..*" DocumentVersion
    DocumentVersion "1" --> "0..*" ReviewRequest
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Submitter chooses draft/version for review] --> B{Role can submit and document is draft?}
    B -- No --> B1[Reject submit 400 or 403]
    B -- Yes --> C{Pending review already exists?}
    C -- Yes --> C1[Reject submit 409]
    C -- No --> D[Create pending review request]
    D --> E[Set document status to pending_review]
    E --> F[Emit review_submitted notifications + audit]

    F --> G[Reviewer opens pending queue]
    G --> H[Filter out self-submitted requests]
    H --> I[Reviewer selects request]
    I --> J{Authorized reviewer and pending state?}
    J -- No --> J1[Reject action 403 or 409]
    J -- Yes --> K{Approve or Reject?}

    K -- Approve --> L{Self-approval or stale version?}
    L -- Yes --> L1[Reject approval 403 or 409]
    L -- No --> M[Mark review approved]
    M --> N[Set document status to approved]
    N --> O[Audit + notify submitter approved]

    K -- Reject --> P[Mark review rejected with comments]
    P --> Q[Set document status back to draft]
    Q --> R[Audit + notify submitter rejected]

    D --> S[Submitter may cancel while pending]
    S --> T{Owner and pending state?}
    T -- No --> T1[Reject cancel 403 or 409]
    T -- Yes --> U[Mark review cancelled and restore draft status]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Submitter as Editor or Manager or Admin
    actor Reviewer as Editor/Manager/Admin/System Admin
    participant FE as Frontend
    participant REV as Reviews API
    participant DB as Database
    participant NOTIF as Notification Records
    participant AUD as Audit Log

    Submitter->>FE: Submit document for review
    FE->>REV: POST /api/v1/reviews/documents/{document_id}/submit
    REV->>DB: Validate role and document existence
    REV->>DB: Ensure document status is draft
    REV->>DB: Ensure no existing pending review
    REV->>DB: Validate target version if provided
    alt Validation passes
        REV->>DB: Insert review_request status=pending
        REV->>DB: Update document status=pending_review
        REV->>AUD: Insert submit audit event
        REV->>NOTIF: Create review_submitted notifications for reviewer roles
        REV-->>Submitter: review payload
    else Validation fails
        REV-->>Submitter: 400 or 404 or 409
    end

    Reviewer->>FE: Open pending queue
    FE->>REV: GET /api/v1/reviews/pending
    REV->>DB: Query pending reviews excluding submitter=self
    REV-->>Reviewer: pending items

    Reviewer->>FE: Approve review
    FE->>REV: POST /api/v1/reviews/{review_id}/approve
    REV->>DB: Validate pending state and reviewer authorization
    REV->>DB: Validate version not stale and not already published
    alt Approval accepted
        REV->>DB: Set review approved plus reviewer metadata
        REV->>DB: Set document status=approved
        REV->>AUD: Insert approval audit
        REV->>NOTIF: Notify submitter review_approved
        REV-->>Reviewer: approved review payload
    else Self-approval/stale/conflict
        REV-->>Reviewer: 403 or 409
    end

    Reviewer->>FE: Reject review
    FE->>REV: POST /api/v1/reviews/{review_id}/reject
    REV->>DB: Validate pending state and reviewer authorization
    alt Rejection accepted
        REV->>DB: Set review rejected plus reviewer comments
        REV->>DB: Set document status=draft
        REV->>AUD: Insert rejection audit
        REV->>NOTIF: Notify submitter review_rejected
        REV-->>Reviewer: rejected review payload
    else Invalid transition or permission
        REV-->>Reviewer: 403 or 409
    end

    Submitter->>FE: Cancel own pending review
    FE->>REV: POST /api/v1/reviews/{review_id}/cancel
    REV->>DB: Validate ownership and pending status
    REV->>DB: Set review cancelled and document status=draft
    REV->>AUD: Insert cancellation audit
    REV-->>Submitter: cancelled review payload

    Submitter->>FE: Check review status and history
    FE->>REV: GET /api/v1/reviews/my-submissions and /documents/{document_id}/history
    REV->>DB: Query review records
    REV-->>Submitter: timeline and statuses
```
