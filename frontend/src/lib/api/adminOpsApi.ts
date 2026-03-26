/**
 * Admin Operations API mixin (Wave Z)
 * System-admin only endpoints for tenant management, impersonation, etc.
 */

import type { ApiClientBase, Constructor } from './httpClient'

// ── Types ────────────────────────────────────────────────────────

export interface ImpersonationSession {
  id: number
  admin_user_id: number
  target_tenant_id: number
  target_tenant_name: string | null
  session_token: string
  started_at: string
  ended_at: string | null
  is_active: boolean
}

export interface AdminAction {
  id: number
  action_type: string
  status: string
  payload: string
  reason: string | null
  requested_by: number
  requester_name: string | null
  reviewed_by: number | null
  reviewer_name: string | null
  review_comment: string | null
  target_tenant_id: number | null
  target_tenant_name: string | null
  created_at: string
  reviewed_at: string | null
  executed_at: string | null
}

export interface TenantConfig {
  tenant_id: number
  tenant_name: string
  settings: Record<string, unknown>
}

export interface FeatureFlag {
  id: number
  tenant_id: number
  feature_key: string
  enabled: boolean
  updated_by: number | null
  created_at: string
  updated_at: string
}

export interface FeatureMatrix {
  tenants: Array<{
    tenant_id: number
    tenant_name: string
    features: Record<string, boolean>
  }>
}

export interface ServiceStatus {
  name: string
  status: string
  latency_ms: number | null
  details: string | null
}

export interface SystemStatus {
  overall: string
  services: ServiceStatus[]
  checked_at: string
}

export interface TenantPerformance {
  tenant_id: number
  tenant_name: string
  p50_ms: number
  p95_ms: number
  error_rate: number
  active_users: number
  period_start: string
  period_end: string
}

export interface TenantProvision {
  tenant_id: number
  tenant_name: string
  tenant_slug: string
  admin_user_id: number
  admin_username: string
}

export interface DomainVerification {
  id: number
  tenant_id: number
  domain: string
  verification_token: string
  status: string
  verified_at: string | null
  created_at: string
  expires_at: string
}

export interface TenantBranding {
  tenant_id: number
  logo_url: string | null
  primary_color: string | null
  accent_color: string | null
  portal_header_text: string | null
}

export interface TenantQuota {
  tenant_id: number
  max_users: number | null
  max_documents: number | null
  max_storage_mb: number | null
  current_users: number
  current_documents: number
  updated_at: string | null
}

export interface MaintenanceWindow {
  id: number
  title: string
  description: string | null
  scheduled_start: string
  scheduled_end: string
  is_read_only: boolean
  is_active: boolean
  notification_sent: boolean
  created_by: number
  created_at: string
}

export interface Runbook {
  name: string
  path: string
}

// ── Mixin ────────────────────────────────────────────────────────

export const AdminOpsApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    // Z-001: Impersonation
    async startImpersonation(targetTenantId: number): Promise<ImpersonationSession> {
      const { data } = await this.client.post('/admin/impersonate', { target_tenant_id: targetTenantId })
      return data
    }

    async endImpersonation(): Promise<{ ended: boolean }> {
      const { data } = await this.client.post('/admin/impersonate/end')
      return data
    }

    async getCurrentImpersonation(): Promise<ImpersonationSession | null> {
      const { data } = await this.client.get('/admin/impersonate/current')
      return data
    }

    // Z-002: Admin Actions
    async createAdminAction(params: {
      action_type: string
      payload: Record<string, unknown>
      reason?: string
      target_tenant_id?: number
    }): Promise<AdminAction> {
      const { data } = await this.client.post('/admin/actions', params)
      return data
    }

    async listAdminActions(status?: string): Promise<AdminAction[]> {
      const { data } = await this.client.get('/admin/actions', { params: status ? { status } : {} })
      return data
    }

    async reviewAdminAction(actionId: number, approved: boolean, comment?: string): Promise<AdminAction> {
      const { data } = await this.client.put(`/admin/actions/${actionId}/review`, { approved, comment })
      return data
    }

    // Z-003: Bulk Operations
    async bulkUpdateTenantSettings(tenantIds: number[], settings: Record<string, unknown>): Promise<{ updated: number }> {
      const { data } = await this.client.post('/admin/bulk/settings', { tenant_ids: tenantIds, settings })
      return data
    }

    async bulkSendAnnouncement(message: string, type?: string, tenantIds?: number[]): Promise<{ created: boolean; announcement_id: number }> {
      const { data } = await this.client.post('/admin/bulk/announcements', { message, type: type || 'info', tenant_ids: tenantIds })
      return data
    }

    // Z-004: Tenant Config
    async getTenantConfig(tenantId: number): Promise<TenantConfig> {
      const { data } = await this.client.get(`/admin/tenants/${tenantId}/config`)
      return data
    }

    async updateTenantConfig(tenantId: number, settings: Record<string, unknown>): Promise<TenantConfig> {
      const { data } = await this.client.put(`/admin/tenants/${tenantId}/config`, { settings })
      return data
    }

    // Z-005: Feature Matrix
    async getFeatureMatrix(): Promise<FeatureMatrix> {
      const { data } = await this.client.get('/admin/features')
      return data
    }

    async updateTenantFeatures(tenantId: number, flags: Array<{ feature_key: string; enabled: boolean }>): Promise<FeatureFlag[]> {
      const { data } = await this.client.put(`/admin/tenants/${tenantId}/features`, flags)
      return data
    }

    // Z-006: System Status
    async getSystemStatus(): Promise<SystemStatus> {
      const { data } = await this.client.get('/admin/status')
      return data
    }

    // Z-007: Tenant Performance
    async getTenantPerformance(tenantId: number, days?: number): Promise<TenantPerformance> {
      const { data } = await this.client.get(`/admin/tenants/${tenantId}/performance`, { params: { days: days || 30 } })
      return data
    }

    // Z-008: Provisioning
    async provisionTenant(params: {
      tenant_name: string
      tenant_slug: string
      admin_username: string
      admin_email: string
      admin_password: string
      company_type?: string
      contact_email?: string
    }): Promise<TenantProvision> {
      const { data } = await this.client.post('/admin/tenants/provision', params)
      return data
    }

    // Z-009: Suspension
    async suspendTenant(tenantId: number, reason?: string): Promise<{ suspended: boolean }> {
      const { data } = await this.client.post(`/admin/tenants/${tenantId}/suspend`, { reason })
      return data
    }

    async reactivateTenant(tenantId: number): Promise<{ reactivated: boolean }> {
      const { data } = await this.client.post(`/admin/tenants/${tenantId}/reactivate`)
      return data
    }

    // Z-010: Domain Verification
    async createDomainVerification(tenantId: number, domain: string): Promise<DomainVerification> {
      const { data } = await this.client.post(`/admin/tenants/${tenantId}/domains`, { domain })
      return data
    }

    async listDomainVerifications(tenantId: number): Promise<DomainVerification[]> {
      const { data } = await this.client.get(`/admin/tenants/${tenantId}/domains`)
      return data
    }

    async verifyDomain(tenantId: number, domainId: number): Promise<{ verified: boolean; domain: string }> {
      const { data } = await this.client.post(`/admin/tenants/${tenantId}/domains/${domainId}/verify`)
      return data
    }

    // Z-011: Branding
    async getTenantBranding(tenantId: number): Promise<TenantBranding> {
      const { data } = await this.client.get(`/admin/tenants/${tenantId}/branding`)
      return data
    }

    async updateTenantBranding(tenantId: number, branding: Partial<TenantBranding>): Promise<TenantBranding> {
      const { data } = await this.client.put(`/admin/tenants/${tenantId}/branding`, branding)
      return data
    }

    // Z-012: Quotas
    async getTenantQuota(tenantId: number): Promise<TenantQuota> {
      const { data } = await this.client.get(`/admin/tenants/${tenantId}/quota`)
      return data
    }

    async updateTenantQuota(tenantId: number, quota: { max_users?: number; max_documents?: number; max_storage_mb?: number }): Promise<TenantQuota> {
      const { data } = await this.client.put(`/admin/tenants/${tenantId}/quota`, quota)
      return data
    }

    // Z-015: Export
    async exportTenantData(tenantId: number): Promise<{ tenant_id: number; tenant_name: string; export_data: Record<string, unknown>; exported_at: string }> {
      const { data } = await this.client.get(`/admin/tenants/${tenantId}/export`)
      return data
    }

    // Z-017: Rate Limits
    async getRateLimits(): Promise<{ admin_requests_per_minute: number; regular_requests_per_minute: number }> {
      const { data } = await this.client.get('/admin/rate-limits')
      return data
    }

    // Z-018: Maintenance Windows
    async createMaintenanceWindow(params: {
      title: string
      description?: string
      scheduled_start: string
      scheduled_end: string
      is_read_only?: boolean
    }): Promise<MaintenanceWindow> {
      const { data } = await this.client.post('/admin/maintenance', params)
      return data
    }

    async listMaintenanceWindows(): Promise<MaintenanceWindow[]> {
      const { data } = await this.client.get('/admin/maintenance')
      return data
    }

    async activateMaintenanceWindow(windowId: number): Promise<{ activated: boolean }> {
      const { data } = await this.client.post(`/admin/maintenance/${windowId}/activate`)
      return data
    }

    async deactivateMaintenanceWindow(windowId: number): Promise<{ deactivated: boolean }> {
      const { data } = await this.client.post(`/admin/maintenance/${windowId}/deactivate`)
      return data
    }

    // Z-014: Runbooks
    async listRunbooks(): Promise<{ runbooks: Runbook[] }> {
      const { data } = await this.client.get('/admin/runbooks')
      return data
    }
  }
