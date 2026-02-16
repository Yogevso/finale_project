# P2: Authoring and Content Assembly - Additions and Logic Gaps

## Proposed Additions

| Priority | Addition | Why it matters | Suggested implementation |
|---|---|---|---|
| High | Content schema validation engine | Prevents malformed document payloads | Validate body/metadata against versioned JSON schema before persist |
| High | Attachment malware scanning | Reduces security risk from uploads | Asynchronous scan pipeline with quarantine and verdict status |
| High | Atomic document+version write transactions | Avoids partial state writes | Ensure create/update operations commit document and version as one unit |
| Medium | Auto-save draft checkpoints | Minimizes authoring data loss | Save periodic draft checkpoints separate from semantic versions |
| Medium | Rich diff and change summary generation | Improves review quality | Generate diff metadata per version transition |
| Medium | Comment policy matrix by role | Clarifies visibility and moderation | Explicit rules for who can view/edit/resolve by role and ownership |
| Low | Content quality linting | Catches style or structure issues early | Add lint hooks for title completeness, taxonomy coverage, dead links |
| Low | PII/secret scanner for content and attachments | Compliance and safety | Pre-publish scans with remediation workflow |

## Coverage Notes

1. Existing phase diagrams model core authoring endpoints and guards.
2. Additions target integrity, security, and authoring productivity.
3. Recommended before scaling large editor and reviewer populations.
