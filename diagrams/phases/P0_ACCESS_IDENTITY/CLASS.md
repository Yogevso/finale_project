# P0: Access and Identity - Class Diagram

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
