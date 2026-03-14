# Y15-029: Nullable Column Audit Report

This document audits nullable columns in the database schema to identify fields
that should potentially have NOT NULL constraints.

## Executive Summary

The audit identified several nullable FK columns. Most are intentionally nullable
by design. One area requires attention for future improvement.

## Audit Results

### Intentionally Nullable Columns (No Action Required)

| Model       | Column           | Reason                                          |
| ----------- | ---------------- | ----------------------------------------------- |
| User        | tenant_id        | System Admins operate cross-tenant (no tenant)  |
| SystemSetting | updated_by     | Initial seed data has no user                   |
| RbacPolicy  | updated_by       | Initial seed data has no user                   |
| Document    | parent_id        | Root documents have no parent                   |
| Document    | platform_id      | Platform is optional metadata                   |
| Version     | published_by     | Draft versions aren't published                 |
| Comment     | parent_id        | Top-level comments have no parent               |
| AuditLog    | user_id          | System events may not have a user               |
| AuditLog    | document_id      | Some events aren't document-related             |
| Invitation  | tenant_id        | Some invitations are platform-wide              |
| Invitation  | created_user_id  | Pending invitations have no user               |
| CollaborationSnapshot | created_by | Auto-saves don't have a user context       |
| ReviewRequest | reviewed_by    | Pending reviews have no reviewer                |
| ReviewRequest | version_id     | Document-level reviews may not be version-specific |

### Optional Metadata Columns (No Action Required)

Many columns are nullable because they represent optional metadata:
- `description`, `image_url`, `thumbnail_url` - Optional display fields
- `message`, `response`, `comment` - Optional text content
- `scheduled_publish_at`, `expires_at` - Optional timestamps
- `notification_preferences`, `settings` - Optional JSON blobs

### Potential Improvement Areas

#### Document.tenant_id (Nullable = True)

**Current Behavior**: Documents can be created with `tenant_id=None` when:
1. System Admin creates a document without tenant context
2. No tenant context middleware is active

**Risk**: Documents without tenant_id may bypass tenant isolation checks.

**Recommendation**: 
- Add application-level validation requiring tenant_id on document creation
- For system-wide documents, consider a "system" tenant instead of NULL
- Migration to enforce NOT NULL would require backfilling existing NULL values

**Current Mitigation**:
- TenantContextMiddleware enforces tenant context for authenticated requests
- ServiceLocator requires tenant context for most operations

## Database-Level Constraints Added (Y15-028)

The following ON DELETE rules were added via migration `20260311_0020`:

| Relationship            | ON DELETE Action | Rationale                                    |
| ----------------------- | ---------------- | -------------------------------------------- |
| attachments → documents | CASCADE          | Remove attachments when document deleted     |
| comments → documents    | CASCADE          | Remove comments when document deleted        |
| versions → documents    | CASCADE          | Remove versions when document deleted        |
| sections → versions     | CASCADE          | Remove sections when version deleted         |
| documents → tenants     | SET NULL         | Preserve documents if tenant removed         |
| users → tenants         | SET NULL         | Preserve users if tenant removed             |

## Conclusion

The schema nullable constraints are largely intentional. The main area for future
hardening is requiring `Document.tenant_id` at the application level, which would
require careful migration planning for any existing NULL values.
