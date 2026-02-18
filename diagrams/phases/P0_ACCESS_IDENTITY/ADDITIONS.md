# P0: Access and Identity - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Refresh token rotation and family revocation | Current refresh flow issues access tokens without rotating refresh tokens | Rotate refresh token on refresh and revoke token families on replay detection |
| High | Scope refresh-token lookup by user/session identifier | Current hash verification scans all active refresh rows | Store token identifier and query a narrowed candidate set before hash compare |
| High | Enforce server-side role constraints on `/auth/register` | Current endpoint accepts role from public payload | Restrict self-registration to safe default roles or require invitation for elevated roles |
| High | Durable distributed auth rate limiting | Current limiter is in-memory per process | Move limiter state to Redis or equivalent shared backend |
| Medium | Real password reset completion flow | `forgot-password` currently returns generic message only | Add reset token issue/verify endpoints with one-time token invalidation |
| Medium | Invitation and auth denial audit trail | Invitation/auth paths currently do not emit audit logs | Persist structured audit events for sensitive allow/deny outcomes |
| Medium | Session/device-level logout options | Logout invalidates all refresh tokens for a user | Add single-session/device logout and active-session listing |
| Low | Invitation resend and expiry observability | Hard to detect invitation abuse patterns | Add metrics on resend volume, expiry rate, and acceptance funnel |

## Coverage Notes

1. Core invitation and auth flows are implemented and represented in diagrams.
2. Login and forgot-password rate limiting are already present, but in-memory only.
3. Highest priority gaps are token lifecycle hardening and stronger server-side registration controls.
