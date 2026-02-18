# P0: Access and Identity - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Manage invitations | `POST /invitations`, `GET /invitations`, `GET /invitations/{id}`, `POST /invitations/{id}/resend`, `DELETE /invitations/{id}` | Role hierarchy + role-specific tenant rules + non-system tenant scoping on read/manage | Managers can only invite editor/viewer/customer. |
| UC2 | Validate invitation token | `GET /auth/invitation/{token}` | Token must exist, be pending, and not be expired | Expired tokens are marked `expired` in persistence. |
| UC3 | Accept invitation and create account | `POST /auth/invitation/accept` | Token validity + username/email uniqueness | Creates user from invitation role and tenant, then logs in. |
| UC4 | Self-register account | `POST /auth/register` | Email/username uniqueness | Current server trusts requested role field. |
| UC5 | Login with session bootstrap | `POST /auth/login` | Optional per-IP+username limiter + password and active checks | On success, hashed refresh token record is persisted. |
| UC6 | Refresh access token | `POST /auth/refresh` | Refresh token must match unused and unexpired hash record | Returns new access token (refresh token is not rotated). |
| UC7 | Read profile and change password | `GET /auth/me`, `POST /auth/change-password` | Active token + old-password verification for change | Password change persists new bcrypt hash. |
| UC8 | Logout and invalidate sessions | `POST /auth/logout` | Authenticated user required | Marks all user refresh records `used_at`. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Invalid/expired/cancelled invitation token | `GET /auth/invitation/{token}`, `POST /auth/invitation/accept` | Status and expiry checks | Add invitation abuse telemetry and alerting. |
| EX2 | Duplicate identity at invite acceptance | `POST /auth/invitation/accept` | Existing email/username checks | Add pre-flight availability endpoint for UX. |
| EX3 | Inviter attempts role escalation | `POST /invitations` | `can_invite_role` hierarchy rules | Add policy-driven hierarchy loaded from RBAC service. |
| EX4 | Out-of-scope invitation access attempt | Invitation management endpoints | Tenant-context filtering and role/scope checks | Add immutable audit logging for denied attempts. |
| EX5 | Repeated failed login attempts | `POST /auth/login` | In-memory sliding-window rate limiter | Add distributed limiter for multi-instance deployment. |
| EX6 | Refresh replay or invalid token use | `POST /auth/refresh` | Hash match over unused, non-expired records | Add token rotation and family revocation semantics. |
| EX7 | Inactive account login attempt | `POST /auth/login` | `is_active` check returns `403` | Add explicit account-status telemetry and notifications. |
| EX8 | Forgot-password abuse | `POST /auth/forgot-password` | Dedicated in-memory limiter + generic response | Add durable reset workflow with one-time reset tokens. |

## Coverage and Gap Link

1. Endpoint coverage is mapped in `SEQUENCE.md`.
2. Behavioral intent is summarized in `USE_CASE.md`.
3. Security and operability improvements are listed in `ADDITIONS.md`.
