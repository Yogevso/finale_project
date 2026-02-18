# P0: Access and Identity (Endpoint-Level Phase Pack)

## Scope

Phase `P0` covers invitation management, invitation acceptance, account bootstrap, login/session lifecycle, and password self-service endpoints.

## Endpoint Inventory

| Method | Endpoint | Primary Actors | Guard |
|---|---|---|---|
| `POST` | `/invitations` | System Admin, Admin, Manager | Role hierarchy + role-specific tenant assignment rules + duplicate email/invite checks |
| `GET` | `/invitations` | System Admin, Admin, Manager | Non-system-admin users are tenant-scoped |
| `GET` | `/invitations/{id}` | System Admin, Admin, Manager | Non-system-admin users are tenant-scoped |
| `POST` | `/invitations/{id}/resend` | System Admin, Admin, Manager | Cannot resend accepted invite; email must still be unregistered |
| `DELETE` | `/invitations/{id}` | System Admin, Admin, Manager | Pending only |
| `GET` | `/auth/invitation/{token}` | Public invitee | Token must exist, be pending, and not expired |
| `POST` | `/auth/invitation/accept` | Public invitee | Token valid + username/email uniqueness |
| `POST` | `/auth/register` | Public | Email/username uniqueness (role trusted from request payload) |
| `POST` | `/auth/login` | All users | Optional auth rate limiting + credential and active checks |
| `POST` | `/auth/forgot-password` | Public | Optional auth rate limiting + generic non-enumerating response |
| `POST` | `/auth/refresh` | All users | Refresh token hash must match unused, non-expired record |
| `POST` | `/auth/logout` | Authenticated user | Marks all user refresh records as used |
| `GET` | `/auth/me` | Authenticated user | Active access token required |
| `POST` | `/auth/change-password` | Authenticated user | Old password hash must match |

## Domain Class Diagram

```mermaid
classDiagram
    class AuthRouter {
        +POST /auth/login
        +POST /auth/forgot-password
        +POST /auth/refresh
        +POST /auth/logout
        +POST /auth/register
        +GET /auth/me
        +POST /auth/change-password
        +GET /auth/invitation/{token}
        +POST /auth/invitation/accept
    }

    class InvitationRouter {
        +POST /invitations
        +GET /invitations
        +GET /invitations/{id}
        +POST /invitations/{id}/resend
        +DELETE /invitations/{id}
    }

    class AuthService {
        +login(username, password)
        +refresh_access_token(refresh_token)
        +logout(user_id)
        +register(user_data)
        +change_password(user, old_password, new_password)
    }

    class AuthRateLimitService {
        +check_login_allowed(ip, username)
        +record_login_failure(ip, username)
        +record_login_success(ip, username)
        +check_forgot_password_allowed(ip, identifier)
        +record_forgot_password_request(ip, identifier)
    }

    class TenantContext {
        +tenant_id: int?
        +user_id: int
        +user_role: UserRole
        +is_system_admin: bool
    }

    class User {
        +id: int
        +email: str
        +username: str
        +full_name: str
        +hashed_password: str
        +role: UserRole
        +tenant_id: int?
        +is_active: bool
    }

    class Invitation {
        +id: int
        +email: str
        +token: str
        +role: UserRole
        +tenant_id: int?
        +invited_by: int
        +status: InvitationStatus
        +expires_at: datetime
        +accepted_at: datetime?
        +created_user_id: int?
    }

    class PasswordReset {
        +id: int
        +user_id: int
        +token_hash: str
        +expires_at: datetime
        +used_at: datetime?
    }

    class Tenant {
        +id: int
        +name: str
        +slug: str
    }

    AuthRouter --> AuthService
    AuthRouter --> AuthRateLimitService
    InvitationRouter --> TenantContext
    InvitationRouter --> Invitation
    AuthService --> User
    AuthService --> PasswordReset
    Invitation "0..1" --> "1" Tenant : tenant_id
```

## Phase Flow Diagram

```mermaid
flowchart TD
    A[Admin or manager submits invitation] --> B{Allowed to invite target role?}
    B -- No --> B1[403 role hierarchy violation]
    B -- Yes --> C{Tenant assignment valid for selected role rules?}
    C -- No --> C1[403 role or scope rule violation]
    C -- Yes --> D{Email already registered or pending invite exists?}
    D -- Yes --> D1[400 conflict]
    D -- No --> E[Create invitation token with 7-day expiry]

    E --> F[Invitee validates token]
    F --> G{Token pending and unexpired?}
    G -- No --> G1[Reject invalid or expired token]
    G -- Yes --> H[Accept invitation and create user]
    H --> I[Mark invitation accepted and link user]
    I --> J[Immediate login issues access plus refresh token]

    J --> K[User login]
    K --> L{Rate limiter allows attempt?}
    L -- No --> L1[429 Retry-After]
    L -- Yes --> M{Credentials valid and user active?}
    M -- No --> M1[401 or 403]
    M -- Yes --> N[Persist hashed refresh token record]

    N --> O[Forgot-password request]
    O --> P{Rate limiter allows request?}
    P -- No --> P1[429 Retry-After]
    P -- Yes --> Q[Return generic success message]

    Q --> R[Refresh access token]
    R --> S{Refresh token matches unused unexpired hash?}
    S -- No --> S1[401 invalid or expired refresh token]
    S -- Yes --> T[Issue new access token only]

    T --> U[Profile and password change]
    U --> V{Old password matches?}
    V -- No --> V1[400 incorrect current password]
    V -- Yes --> W[Persist new password hash]
    W --> X[Logout marks user refresh tokens used]
```

## Endpoint Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor AdminMgr as Admin or Manager
    actor Invitee as Invitee
    actor User as Authenticated User
    participant FE as Frontend
    participant INV as Invitations API
    participant AUTH as Auth API
    participant RL as AuthRateLimitService
    participant DB as Database

    Note over AdminMgr,Invitee: Invitation lifecycle
    AdminMgr->>FE: Create invitation
    FE->>INV: POST /api/v1/invitations
    INV->>DB: Enforce role hierarchy, role-specific tenant rules, duplicate checks
    alt Valid request
        INV->>DB: Insert pending invitation with token and 7-day expiry
        INV-->>AdminMgr: 201 invitation payload
    else Invalid role/scope/duplicate
        INV-->>AdminMgr: 400 or 403
    end

    Invitee->>FE: Open invite link
    FE->>AUTH: GET /api/v1/auth/invitation/{token}
    AUTH->>DB: Lookup invitation and expiry/status
    AUTH-->>Invitee: valid true or false

    Invitee->>FE: Accept invitation
    FE->>AUTH: POST /api/v1/auth/invitation/accept
    AUTH->>DB: Re-check token + email/username uniqueness
    AUTH->>DB: Create user and mark invitation accepted
    AUTH->>DB: Store hashed refresh token via login flow
    AUTH-->>Invitee: access_token and refresh_token

    Note over User,Invitee: Session and recovery flows
    User->>FE: Login
    FE->>AUTH: POST /api/v1/auth/login
    AUTH->>RL: check_login_allowed(ip, username)
    alt Rate-limited
        AUTH-->>User: 429 Retry-After
    else Allowed
        AUTH->>DB: Verify credentials and active status
        alt Invalid credentials
            AUTH->>RL: record_login_failure(ip, username)
            AUTH-->>User: 401
        else Success
            AUTH->>RL: record_login_success(ip, username)
            AUTH->>DB: Store hashed refresh token record
            AUTH-->>User: access_token and refresh_token
        end
    end

    User->>FE: Request password reset instructions
    FE->>AUTH: POST /api/v1/auth/forgot-password
    AUTH->>RL: check and record forgot-password attempts
    alt Rate-limited
        AUTH-->>User: 429 Retry-After
    else Allowed
        AUTH-->>User: Generic success message
    end

    User->>FE: Refresh session
    FE->>AUTH: POST /api/v1/auth/refresh
    AUTH->>DB: Match token against unused non-expired hashed records
    alt Match found
        AUTH-->>User: new access_token (no rotated refresh token)
    else No match
        AUTH-->>User: 401 invalid or expired refresh token
    end

    User->>FE: Logout
    FE->>AUTH: POST /api/v1/auth/logout
    AUTH->>DB: Mark all user refresh records used
    AUTH-->>User: Logged out successfully
```
