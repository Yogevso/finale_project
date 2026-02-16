# P0: Access and Identity - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Invitation rate limiting per inviter and tenant | Prevent invitation abuse and email flooding | Add per-actor and per-tenant throttles on invitation endpoints |
| High | Refresh token rotation with one-time-use enforcement | Reduces replay attack blast radius | Rotate refresh token on each refresh; revoke token family on replay detection |
| High | Admin/manager step-up authentication | Protects privileged actions | Require MFA challenge for invitation creation to high-privilege roles |
| High | Login anomaly detection | Detects compromised accounts | Store login metadata and trigger risk rules (geo, device, impossible travel) |
| Medium | Account lockout and progressive delays | Slows brute-force attempts | Track failed login counter and exponential backoff by account/IP |
| Medium | Password breach check | Improves account hygiene | Check new passwords against known compromised-password list |
| Medium | Global session kill switch | Speeds incident response | Add endpoint for security/admin to revoke all sessions for a user |
| Low | Invitation token binding option | Hardens invitation acceptance | Optionally bind invite acceptance to invited email identity proof |

## Coverage Notes

1. Existing diagrams cover invitation, login, refresh, and logout flows.
2. The items above are security-hardening and operational controls not fully modeled yet.
3. Add these controls before high-scale rollout or strict compliance onboarding.
