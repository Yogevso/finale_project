# P3: Real-Time Collaboration (Endpoint-Level Phase Pack)

## Scope

Phase `P3` covers collaboration token minting, WebSocket authentication, state hydration/persistence, session/activity tracking, and snapshot management.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/auth/collab-token` | Editor, Viewer, Customer (with access) | document-specific permissions |
| `GET` | `/collaboration/documents/{id}/state` | Collab server (on behalf of user) | read permission |
| `PUT` | `/collaboration/documents/{id}/state` | Collab server (on behalf of user) | write permission |
| `DELETE` | `/collaboration/documents/{id}/state` | Write-capable role | write permission |
| `GET` | `/collaboration/documents/{id}/status` | Any user with read access | read permission |
| `POST` | `/collaboration/sessions/start` | Collaborator | read access |
| `POST` | `/collaboration/sessions/end` | Collaborator | own active session |
| `POST` | `/collaboration/activity` | Collaborator | valid activity type |
| `GET` | `/collaboration/documents/{id}/activity` | Collaborator | read access |
| `GET` | `/collaboration/documents/{id}/sessions` | Collaborator | read access |
| `POST/GET/GET/PATCH/DELETE` | `/collaboration/documents/{id}/snapshots...` | Read or write role by operation | write required for mutating ops |
| `POST` | `/collaboration/documents/{id}/auto-snapshot` | Collaborator | state exists and interval permits |

WebSocket endpoint:
- `ws://<collab-host>:8002/document/{documentId}?token=<collab-jwt>`

## Domain Class Diagram

```mermaid
classDiagram
    class CollaborationAuthController {
        +createCollabToken(documentId)
    }
    class CollaborationStateController {
        +getState(documentId)
        +saveState(documentId, binaryState)
        +deleteState(documentId)
        +getStatus(documentId)
    }
    class SessionController {
        +startSession(documentId)
        +endSession(sessionId)
        +logActivity(payload)
        +listSessions(documentId)
        +listActivity(documentId)
    }
    class SnapshotController {
        +createSnapshot(documentId, payload)
        +listSnapshots(documentId)
        +getSnapshot(documentId, snapshotId)
        +updateSnapshot(documentId, snapshotId, payload)
        +deleteSnapshot(documentId, snapshotId)
        +createAutoSnapshot(documentId)
    }
    class CollaborationPermissionService {
        +resolveDocumentAccess(actor, documentId)
        +canRead(actor, documentId)
        +canWrite(actor, documentId)
    }
    class CollaborationTokenService {
        +issueToken(actor, documentId, readOnlyFlag)
        +verifyToken(token)
    }
    class YjsStateService {
        +loadState(documentId)
        +persistState(documentId, bytes)
        +clearState(documentId)
    }
    class SessionService {
        +start(actor, documentId)
        +end(actor, sessionId)
        +recordActivity(actor, payload)
    }
    class SnapshotService {
        +createManualSnapshot(actor, documentId, payload)
        +createAutoSnapshot(actor, documentId)
        +enforceSnapshotPolicy(documentId)
    }
    class CollaborationSession {
        +UUID id
        +UUID document_id
        +UUID user_id
        +String status
        +DateTime started_at
        +DateTime ended_at
    }
    class CollaborationActivity {
        +UUID id
        +UUID document_id
        +UUID user_id
        +String activity_type
        +String payload_json
        +DateTime created_at
    }
    class CollaborationSnapshot {
        +UUID id
        +UUID document_id
        +UUID created_by
        +String source
        +String label
        +DateTime created_at
    }
    class YjsDocumentState {
        +UUID document_id
        +Binary yjs_state
        +DateTime updated_at
    }

    CollaborationAuthController --> CollaborationPermissionService
    CollaborationAuthController --> CollaborationTokenService
    CollaborationStateController --> CollaborationPermissionService
    CollaborationStateController --> YjsStateService
    SessionController --> CollaborationPermissionService
    SessionController --> SessionService
    SnapshotController --> CollaborationPermissionService
    SnapshotController --> SnapshotService
    SessionService --> CollaborationSession
    SessionService --> CollaborationActivity
    SnapshotService --> CollaborationSnapshot
    YjsStateService --> YjsDocumentState
    CollaborationSession "1" --> "0..*" CollaborationActivity : captures
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Collaborator opens document] --> B[Request collaboration token]
    B --> C{Read access to document?}
    C -- No --> C1[Reject 403]
    C -- Yes --> D[Issue collab JWT with read/write claims]
    D --> E[Client connects WebSocket with token]
    E --> F{Token valid and doc id matches?}
    F -- No --> F1[Reject connection]
    F -- Yes --> G[Set connection mode read-only or editable]

    G --> H[Load existing Yjs state]
    H --> I{State exists?}
    I -- No --> I1[Initialize empty CRDT doc]
    I -- Yes --> J[Hydrate CRDT from stored binary]
    I1 --> K[Start collaboration session]
    J --> K

    K --> L[Log USER_JOINED activity]
    L --> M[Realtime edit/presence loop]
    M --> N[Debounced state persist calls]
    N --> O{Write permission still valid?}
    O -- No --> O1[Drop write updates keep read-only stream]
    O -- Yes --> P[Persist Yjs binary state]
    P --> Q[Manual or auto snapshot checks]
    Q --> R{Snapshot interval/conditions met?}
    R -- No --> S[Continue collaboration]
    R -- Yes --> T[Persist snapshot metadata + state]
    T --> S
    S --> U[User ends session]
    U --> V[Mark session inactive and log USER_LEFT]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Collaborator as Editor/Viewer/Customer
    participant FE as Frontend useCollaboration
    participant API as Collaboration and Auth APIs
    participant COLLAB as Hocuspocus Server
    participant DB as Database

    Collaborator->>FE: Open collaborative document
    FE->>API: POST /api/v1/auth/collab-token
    API->>DB: Load document and compute read/write permissions
    alt Access granted
        API-->>FE: token plus permissions plus ws URL
    else Access denied
        API-->>FE: 403
    end

    FE->>COLLAB: Connect ws /document/{id}?token=...
    COLLAB->>COLLAB: Verify token and document id match
    alt Write permission included
        COLLAB->>COLLAB: Set editable mode
    else Read-only permissions
        COLLAB->>COLLAB: Set connection.readOnly=true
    end

    COLLAB->>API: GET /api/v1/collaboration/documents/{id}/state
    API->>DB: Read yjs_state for document
    alt State exists
        API-->>COLLAB: binary state
    else No state
        API-->>COLLAB: 404 no collaboration state
    end
    COLLAB-->>FE: Initial sync and awareness updates

    FE->>API: POST /api/v1/collaboration/sessions/start
    API->>DB: Insert collaboration_session plus USER_JOINED activity
    API-->>FE: session_id

    loop Live editing loop
        FE->>COLLAB: CRDT updates and presence
        COLLAB-->>FE: peer updates and awareness
        COLLAB->>API: PUT /api/v1/collaboration/documents/{id}/state
        API->>DB: Persist debounced yjs_state
        API-->>COLLAB: save acknowledgment
    end

    FE->>API: POST /api/v1/collaboration/activity
    API->>DB: Insert activity and update session counters
    API-->>FE: activity logged

    FE->>API: POST /api/v1/collaboration/documents/{id}/snapshots
    API->>DB: Validate write permission and snapshot preconditions
    API->>DB: Insert snapshot state and metadata
    API-->>FE: snapshot metadata

    FE->>API: POST /api/v1/collaboration/documents/{id}/auto-snapshot
    API->>DB: Check auto-save interval and state availability
    API-->>FE: created true or reason

    FE->>API: POST /api/v1/collaboration/sessions/end
    API->>DB: Mark session inactive and log USER_LEFT activity
    API-->>FE: session ended
```
