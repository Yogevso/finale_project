# P0: Access and Identity (Endpoint-Level Phase Pack)

## Scope

Phase `P0` covers invitation lifecycle, account provisioning, login, token refresh, and session/logout behavior.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/invitations` | System Admin, Admin, Manager | Authenticated role hierarchy checks |
| `GET` | `/invitations` | System Admin, Admin, Manager | Tenant-scoped unless system admin |
| `GET` | `/invitations/{id}` | System Admin, Admin, Manager | Tenant-scoped unless system admin |
| `POST` | `/invitations/{id}/resend` | System Admin, Admin, Manager | Cannot resend accepted invite |
| `DELETE` | `/invitations/{id}` | System Admin, Admin, Manager | Pending only |
| `GET` | `/auth/invitation/{token}` | Public | Token validity/expiry check |
| `POST` | `/auth/invitation/accept` | Public invitee | Token valid + email/username uniqueness |
| `POST` | `/auth/login` | All users | Password + active status |
| `POST` | `/auth/refresh` | All users | Valid non-expired refresh token hash |
| `POST` | `/auth/logout` | Authenticated user | Marks refresh tokens used |
| `GET` | `/auth/me` | Authenticated user | Active token required |
| `POST` | `/auth/change-password` | Authenticated user | Old password must match |

## Domain Class Diagram

```mermaid
classDiagram
    class InvitationController {
        +createInvitation(payload)
        +listInvitations(filters)
        +getInvitation(id)
        +resendInvitation(id)
        +cancelInvitation(id)
    }
    class AuthController {
        +validateInvitationToken(token)
        +acceptInvitation(payload)
        +login(credentials)
        +refresh(refreshToken)
        +logout(userId)
        +me(userId)
        +changePassword(userId, oldPassword, newPassword)
    }
    class InvitationService {
        +issueInvitation(inviter, payload)
        +validateToken(token)
        +accept(token, registration)
        +markAccepted(id, acceptedBy)
        +markCancelled(id, cancelledBy)
    }
    class AuthService {
        +authenticate(username, password)
        +createSession(user)
        +rotateAccessToken(refreshToken)
        +invalidateSessions(userId)
        +updatePassword(userId, oldPassword, newPassword)
    }
    class TenantScopeGuard {
        +resolveActorScope(actor)
        +assertInvitationScope(actor, tenantId)
        +assertRoleHierarchy(actorRole, targetRole)
    }
    class TokenService {
        +issueAccessToken(user)
        +issueRefreshToken(user)
        +hashRefreshToken(token)
        +verifyRefreshToken(token, hash)
    }
    class PasswordHasher {
        +hashPassword(raw)
        +verifyPassword(raw, hash)
    }
    class Invitation {
        +UUID id
        +String email
        +String role
        +String token
        +String status
        +DateTime expires_at
        +UUID invited_by
        +UUID tenant_id
        +UUID company_id
    }
    class User {
        +UUID id
        +String username
        +String email
        +String role
        +Boolean is_active
        +String hashed_password
        +UUID tenant_id
        +UUID company_id
    }
    class RefreshToken {
        +UUID id
        +UUID user_id
        +String token_hash
        +DateTime expires_at
        +Boolean is_used
        +DateTime used_at
    }
    class AuditEvent {
        +UUID id
        +String action
        +UUID actor_id
        +String target_type
        +UUID target_id
        +DateTime created_at
    }

    InvitationController --> InvitationService
    InvitationController --> TenantScopeGuard
    AuthController --> AuthService
    AuthController --> InvitationService
    AuthService --> TokenService
    AuthService --> PasswordHasher
    InvitationService --> PasswordHasher
    InvitationService --> Invitation
    InvitationService --> User
    AuthService --> User
    AuthService --> RefreshToken
    InvitationService --> AuditEvent
    AuthService --> AuditEvent
    Invitation "1" --> "0..1" User : accepted_by
    User "1" --> "0..*" RefreshToken : sessions
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Inviter chooses role and tenant/company] --> B{Actor has hierarchy permission?}
    B -- No --> B1[Reject request 403]
    B -- Yes --> C{Duplicate user or pending invite exists?}
    C -- Yes --> C1[Reject request 400]
    C -- No --> D[Create invitation token + expiry + audit]
    D --> E[Invitee opens validation endpoint]
    E --> F{Invitation token pending and not expired?}
    F -- No --> F1[Return invalid token state]
    F -- Yes --> G[Invitee submits registration payload]
    G --> H{Username/email unique?}
    H -- No --> H1[Reject request 400]
    H -- Yes --> I[Hash password and create user]
    I --> J[Mark invitation accepted]
    J --> K[Issue access + refresh tokens]
    K --> L[Session established]

    L --> M[User login attempts]
    M --> N{Credentials valid and account active?}
    N -- No --> N1[Return 401 or 403]
    N -- Yes --> O[Create session token records]
    O --> P[User accesses /auth/me and protected APIs]
    P --> Q[Client calls refresh before access expiry]
    Q --> R{Refresh token hash valid and unexpired?}
    R -- No --> R1[Reject refresh and require login]
    R -- Yes --> S[Issue new access token]
    S --> T[Optional password change]
    T --> U{Old password matches hash?}
    U -- No --> U1[Reject change 400]
    U -- Yes --> V[Persist new hash]
    V --> W[Logout marks refresh tokens used]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Inviter as System Admin/Admin/Manager
    actor Invitee as Invited User
    actor User as Authenticated User
    participant FE as Frontend
    participant API as Auth and Invitation API
    participant TENANT as Tenant Context Rules
    participant DB as Database
    participant HASH as Password and Token Hashing

    Note over Inviter,User: Invitation issuance and management
    Inviter->>FE: Create invitation
    FE->>API: POST /api/v1/invitations
    API->>TENANT: Validate role hierarchy and tenant scope
    TENANT-->>API: Allowed or denied
    alt Allowed
        API->>DB: Check duplicate user and pending invite
        API->>DB: Insert invitation with token and expires_at
        API-->>Inviter: 201 invitation payload
    else Denied or invalid
        API-->>Inviter: 400 or 403
    end

    Inviter->>FE: Inspect invitation status
    FE->>API: GET /api/v1/invitations and GET /api/v1/invitations/{id}
    API->>TENANT: Apply tenant filtering
    API->>DB: Query invitations
    API-->>Inviter: list/details

    Note over Inviter,User: Public validation and acceptance
    Invitee->>FE: Open invitation link
    FE->>API: GET /api/v1/auth/invitation/{token}
    API->>DB: Lookup invitation by token
    alt Valid and pending
        API-->>Invitee: valid true plus role and company metadata
    else Expired/cancelled/accepted
        API-->>Invitee: valid false
    end

    Invitee->>FE: Submit username/full_name/password
    FE->>API: POST /api/v1/auth/invitation/accept
    API->>DB: Re-validate invitation and uniqueness constraints
    API->>HASH: Hash password
    API->>DB: Create user and mark invitation accepted
    API->>HASH: Create access token and refresh token hash record
    API-->>Invitee: access_token and refresh_token

    Note over Inviter,User: Session lifecycle
    User->>FE: Login
    FE->>API: POST /api/v1/auth/login
    API->>DB: Load user by username
    API->>HASH: Verify password hash
    alt Auth success and active user
        API->>HASH: Issue access token and refresh token hash
        API->>DB: Persist refresh token hash record
        API-->>User: access_token and refresh_token
    else Invalid credentials or inactive
        API-->>User: 401 or 403
    end

    User->>FE: Refresh token
    FE->>API: POST /api/v1/auth/refresh
    API->>DB: Query candidate refresh token hashes
    API->>HASH: Compare provided token against hashes
    alt Valid refresh token
        API-->>User: new access_token
    else Invalid or expired refresh token
        API-->>User: 401
    end

    User->>FE: Fetch profile and change password
    FE->>API: GET /api/v1/auth/me and POST /api/v1/auth/change-password
    API->>DB: Resolve user and update hashed_password when valid
    API-->>User: profile and success message

    User->>FE: Logout
    FE->>API: POST /api/v1/auth/logout
    API->>DB: Mark outstanding refresh tokens used
    API-->>User: logged out
```
