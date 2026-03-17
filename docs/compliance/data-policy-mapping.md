# Data Policy Mapping — GDPR & CCPA Compliance

> **AA-011** | Last updated: 2026-03-17  
> Maps every personal data field to its legal basis, retention period, and deletion procedure.

---

## 1. Overview

This document maps all personal data collected and processed by the Documentation Platform to the relevant GDPR (EU) and CCPA (California) requirements.

| Regulation | Scope | Key Rights |
|-----------|-------|------------|
| **GDPR** | EU/EEA residents | Access (Art. 15), Portability (Art. 20), Erasure (Art. 17), Rectification (Art. 16) |
| **CCPA** | California residents | Right to Know, Right to Delete, Right to Opt-Out, Right to Non-Discrimination |

---

## 2. Data Field Mapping

### 2.1 User Profile Data

| Field | Legal Basis (GDPR) | CCPA Category | Retention | Deletion Procedure |
|-------|-------------------|---------------|-----------|-------------------|
| `email` | Contractual necessity (Art. 6.1b) | Personal identifiers | Account lifetime + 30 days | Anonymized to `deleted-user-{id}@anonymized.local` |
| `username` | Contractual necessity | Personal identifiers | Account lifetime + 30 days | Anonymized to `deleted-user-{id}` |
| `full_name` | Contractual necessity | Personal identifiers | Account lifetime + 30 days | Replaced with "Deleted User" |
| `hashed_password` | Contractual necessity | N/A (not disclosed) | Account lifetime | Set to `ACCOUNT_DELETED` |
| `avatar_url` | Consent (Art. 6.1a) | Personal identifiers | Account lifetime | Set to NULL |
| `timezone` | Legitimate interest (Art. 6.1f) | Internet activity | Account lifetime | Reset to "UTC" |
| `locale` | Legitimate interest | Internet activity | Account lifetime | Reset to "en" |
| `notification_preferences` | Consent | Internet activity | Account lifetime | Set to NULL |

### 2.2 Authentication & Security Data

| Field | Legal Basis (GDPR) | CCPA Category | Retention | Deletion Procedure |
|-------|-------------------|---------------|-----------|-------------------|
| `last_login_ip` | Legitimate interest (security) | Internet activity | Account lifetime | Set to NULL on deletion |
| `last_login_user_agent` | Legitimate interest (security) | Internet activity | Account lifetime | Set to NULL on deletion |
| `failed_login_attempts` | Legitimate interest (security) | Internet activity | Account lifetime | Reset to 0 on deletion |
| `locked_until` | Legitimate interest (security) | N/A | Until unlock | Cleared on deletion |
| Security events (`security_events`) | Legitimate interest | Internet activity | 1 year | Hard-deleted on account deletion |
| User sessions (`user_sessions`) | Contractual necessity | Internet activity | 30 days inactivity | Hard-deleted on account deletion |
| Password resets (`password_resets`) | Contractual necessity | N/A | 24 hours (token expiry) | Hard-deleted on account deletion |

### 2.3 Content & Activity Data

| Field | Legal Basis (GDPR) | CCPA Category | Retention | Deletion Procedure |
|-------|-------------------|---------------|-----------|-------------------|
| Documents (`documents`) | Contractual necessity | Commercial info | Indefinite (org asset) | Ownership shows "Deleted User" — content preserved for business continuity |
| Comments (`comments`) | Legitimate interest | Internet activity | Document lifetime | Hard-deleted on account deletion |
| Bookmarks (`bookmarks`) | Consent | Internet activity | Account lifetime | Hard-deleted on account deletion |
| Feedback (`feedbacks`) | Consent | Consumer feedback | Account lifetime | Hard-deleted on account deletion |
| Reading progress (`reading_progress`) | Legitimate interest | Internet activity | Account lifetime | Hard-deleted on account deletion |
| Notifications (`notifications`) | Contractual necessity | N/A | 90 days | Hard-deleted on account deletion |

### 2.4 Audit & Compliance Data

| Field | Legal Basis (GDPR) | CCPA Category | Retention | Deletion Procedure |
|-------|-------------------|---------------|-----------|-------------------|
| Audit logs (`audit_logs`) | Legal obligation (Art. 6.1c) | N/A (exempt) | **7 years** (regulatory) | **NOT deleted** — user FK preserved but user record anonymized. Immutable DB triggers prevent modification. |
| `audit_logs.ip_address` | Legitimate interest | Internet activity | 7 years | Retained for integrity — PII redacted in API responses for non-admins |
| `audit_logs.signature` | Legal obligation | N/A | 7 years | Preserved — HMAC integrity chain |

### 2.5 Organizational Data

| Field | Legal Basis (GDPR) | CCPA Category | Retention | Deletion Procedure |
|-------|-------------------|---------------|-----------|-------------------|
| Tenant (`tenants`) | Contractual necessity | Commercial info | Contract lifetime | Admin-initiated tenant deletion process |
| Tenant settings | Contractual necessity | Commercial info | Contract lifetime | Deleted with tenant |
| Company assignments | Contractual necessity | Commercial info | Document lifetime | Removed when document deleted |

---

## 3. Data Processing Activities

| Activity | Purpose | Legal Basis | Data Involved |
|----------|---------|-------------|---------------|
| User authentication | Service access | Contract | email, password hash, IP, user agent |
| Document creation/editing | Core service | Contract | user ID, document content |
| Audit logging | Compliance & security | Legal obligation | All user actions, IP, timestamp |
| Analytics dashboard | Service improvement | Legitimate interest | Aggregated usage metrics |
| Email notifications | Service communication | Contract / Consent | email, notification preferences |
| AI assistant | Feature delivery | Contract / Consent | Conversation content, document context |

---

## 4. Data Subject Rights Procedures

### 4.1 Right of Access / Right to Know (GDPR Art. 15, CCPA §1798.100)

- **Endpoint**: `POST /api/v1/gdpr/export`
- **Process**: User requests export → System generates ZIP with all personal data → Download link sent
- **SLA**: 30 days (GDPR), 45 days (CCPA)
- **Format**: Machine-readable JSON files in ZIP archive

### 4.2 Right to Erasure / Right to Delete (GDPR Art. 17, CCPA §1798.105)

- **Endpoint**: `POST /api/v1/gdpr/deletion`
- **Process**: User requests → Admin review → Approval → Anonymization executed
- **Exceptions**: Audit logs exempt under legal obligation basis (GDPR Art. 17.3.e)
- **SLA**: 30 days from approval

### 4.3 Right to Rectification (GDPR Art. 16)

- **Process**: Users can update their profile via the Settings page
- **Admin override**: System admins can update any user's profile via admin panel

### 4.4 Right to Data Portability (GDPR Art. 20)

- **Format**: JSON files (machine-readable, structured)
- **Scope**: All user-provided data and derived data
- **Delivery**: Secure download link (48-hour expiry)

---

## 5. Data Retention Schedule

| Data Category | Retention Period | Trigger for Deletion | Method |
|--------------|-----------------|---------------------|--------|
| Active user data | Account lifetime | Account deletion request | Anonymization |
| Inactive user sessions | 30 days | Last activity date | Automated cleanup |
| Password reset tokens | 24 hours | Token expiry | Automated cleanup |
| Email verification tokens | 24 hours | Token expiry | Automated cleanup |
| Audit logs | 7 years | Never (regulatory) | Immutable — no deletion |
| Document attachments | Document lifetime | Document hard-delete | Cascade delete |
| Collaboration snapshots | 7 days (auto-save) | TTL expiry | Automated cleanup |
| Security events | 1 year | Age-based | Automated cleanup |
| Notifications | 90 days | Age-based | Automated cleanup |

---

## 6. Third-Party Data Sharing

| Third Party | Data Shared | Purpose | Safeguards |
|------------|-------------|---------|------------|
| Ollama (local LLM) | Document excerpts, user queries | AI assistant | Runs locally — no external transmission |
| SMTP provider | Email addresses | Notifications | TLS encryption, configured per deployment |
| S3 storage (if enabled) | Document files | Storage | Encryption at rest, access keys |

> **Note**: In default configuration, all data remains on-premises. No data is shared with external third parties.

---

## 7. Data Protection Officer

For GDPR compliance inquiries:
- Contact: Configured via `EMAIL_FROM` setting
- Response SLA: 72 hours for initial acknowledgment
- Breach notification: Within 72 hours of discovery (GDPR Art. 33)
