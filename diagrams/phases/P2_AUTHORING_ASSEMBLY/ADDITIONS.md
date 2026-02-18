# P2: Authoring and Content Assembly - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Add tenant/document access guards to versions, attachments, and comments services | Several endpoints rely on auth/role checks without consistent tenant visibility enforcement | Reuse a shared document-access validator in all service entry points |
| High | Standardize attachment delete policy | Current delete path is admin-only while other authoring mutations allow manager/system-admin | Align with explicit policy and enforce consistently in dependency + service layers |
| High | Transactional import flow for `/documents/upload` with release-note child doc | Multi-step write can leave partial state on failures outside main attachment try block | Wrap document + attachment + optional child creation in atomic transaction/outbox |
| High | Content schema validation for version content payloads | Arbitrary content structure can be persisted | Validate against versioned schema before create/update |
| Medium | Attachment malware and secret scanning pipeline | Current validation checks type/size only | Asynchronous scan with quarantine status before download eligibility |
| Medium | Comment authorization model hardening | Contributor-based visibility can be broader than intended | Move to explicit document access + role policy matrix |
| Medium | Reader-view processing observability and retries | Async generation can fail without centralized operations view | Add job status metrics, retries, and dead-letter handling |
| Low | Rich diff generation between versions | Improves downstream review quality | Persist semantic diff metadata per version transition |

## Coverage Notes

1. Core authoring endpoints are implemented and reflected in phase diagrams.
2. Review-state gating on versions is already in place and linked to publish behavior.
3. Highest-impact gaps are consistent scope enforcement and hardened attachment/content pipelines.
