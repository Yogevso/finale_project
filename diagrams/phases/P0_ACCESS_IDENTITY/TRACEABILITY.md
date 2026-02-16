# P0: Access and Identity - Traceability Matrix

## Regular Use Case Mapping

| Use Case ID | Use Case | Endpoint(s) | Rule(s) / Guard(s) | Notes |
|---|---|---|---|---|
| UC1 | Create invitation for target role | `POST /invitations` | Authenticated role hierarchy checks | Inviter must stay within allowed role bounds. |
| UC2 | List and inspect invitation status | `GET /invitations`, `GET /invitations/{id}` | Tenant-scoped unless system admin | Prevents cross-tenant invitation disclosure. |
| UC3 | Validate invitation token | `GET /auth/invitation/{token}` | Token validity and expiry checks | Public endpoint with strict token validation. |
| UC4 | Accept invitation and create account | `POST /auth/invitation/accept` | Token valid + username/email uniqueness | Completes account provisioning flow. |
| UC5 | Login and create session | `POST /auth/login` | Password verification + active status check | Returns access and refresh tokens on success. |
| UC6 | Refresh access token | `POST /auth/refresh` | Valid non-expired refresh token hash | Maintains active session without re-login. |
| UC7 | Read profile and change password | `GET /auth/me`, `POST /auth/change-password` | Active token required + old password match | Supports authenticated profile/self-service security. |
| UC8 | Logout and invalidate sessions | `POST /auth/logout` | Authenticated user + refresh token invalidation | Marks refresh tokens used. |

## Extreme and Edge Case Mapping

| Edge ID | Scenario | Endpoint(s) | Current Enforcement | Gap / Additional Control |
|---|---|---|---|---|
| EX1 | Expired/cancelled/accepted invitation token used | `GET /auth/invitation/{token}`, `POST /auth/invitation/accept` | Token status + expiry validation | Add stronger token telemetry for abuse correlation (`ADDITIONS.md`). |
| EX2 | Inviter attempts role escalation | `POST /invitations` | Role hierarchy checks | Add step-up auth for high-privilege invites (`ADDITIONS.md`). |
| EX3 | Username/email collision on acceptance | `POST /auth/invitation/accept` | Uniqueness constraints | Add pre-check UX hint to reduce repeated failures. |
| EX4 | Brute-force login attempts | `POST /auth/login` | Credential validation only | Add lockout/backoff + rate limits (`ADDITIONS.md`). |
| EX5 | Refresh replay/token reuse attempt | `POST /auth/refresh` | Hash match + expiry checks | Add rotating one-time refresh families (`ADDITIONS.md`). |
| EX6 | Suspicious session requires forced revocation | `POST /auth/logout` | User-initiated logout flow exists | Add admin/security global session kill switch (`ADDITIONS.md`). |
| EX7 | Wrong current password during password change | `POST /auth/change-password` | Old password must match | Add risk scoring and notification on repeated failures. |
| EX8 | Cross-tenant invitation visibility attempt | `GET /invitations`, `GET /invitations/{id}` | Tenant scoping guards | Add immutable access audit trail for denied reads. |

## Coverage and Gap Link

1. Endpoint coverage is mapped to `SEQUENCE.md`.
2. Use case intent is defined in `USE_CASE.md`.
3. Hardening and missing controls are captured in `ADDITIONS.md`.
