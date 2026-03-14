/**
 * Z-025: Component test for tenant configuration editor
 * Tests: modify quota, save, verify API payload
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

// Mock auth as system_admin
vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, full_name: 'System Admin', role: 'system_admin' },
  }),
}))

// Track API calls
const mockGetCompanies = vi.fn()
const mockGetTenantQuota = vi.fn()
const mockUpdateTenantQuota = vi.fn()
const mockGetSystemStatus = vi.fn()
const mockGetCurrentImpersonation = vi.fn()
const mockListAdminActions = vi.fn()
const mockGetFeatureMatrix = vi.fn()
const mockListMaintenanceWindows = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getCompanies: (...args: unknown[]) => mockGetCompanies(...args),
    getTenantQuota: (...args: unknown[]) => mockGetTenantQuota(...args),
    updateTenantQuota: (...args: unknown[]) => mockUpdateTenantQuota(...args),
    getSystemStatus: (...args: unknown[]) => mockGetSystemStatus(...args),
    getCurrentImpersonation: (...args: unknown[]) => mockGetCurrentImpersonation(...args),
    listAdminActions: (...args: unknown[]) => mockListAdminActions(...args),
    getFeatureMatrix: (...args: unknown[]) => mockGetFeatureMatrix(...args),
    listMaintenanceWindows: (...args: unknown[]) => mockListMaintenanceWindows(...args),
    startImpersonation: vi.fn(),
    endImpersonation: vi.fn(),
    suspendTenant: vi.fn(),
    reactivateTenant: vi.fn(),
    exportTenantData: vi.fn(),
    provisionTenant: vi.fn(),
    reviewAdminAction: vi.fn(),
    updateTenantFeatures: vi.fn(),
    createMaintenanceWindow: vi.fn(),
    activateMaintenanceWindow: vi.fn(),
    deactivateMaintenanceWindow: vi.fn(),
  },
}))

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import AdminOpsPage from './AdminOpsPage'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AdminOpsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminOpsPage – Tenant Quota Editor (Z-025)', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default: system status panel loads first
    mockGetSystemStatus.mockResolvedValue({
      overall: 'healthy',
      services: [
        { name: 'backend', status: 'healthy', details: 'running' },
      ],
    })

    mockGetCompanies.mockResolvedValue({
      items: [
        { id: 10, name: 'Acme Corp', slug: 'acme', is_active: true, user_count: 0, owned_document_count: 0, assigned_document_count: 0, customer_visible_document_count: 0, document_count: 0, company_type: 'customer', created_at: '', updated_at: '' },
      ],
      total: 1,
      page: 1,
      per_page: 25,
      pages: 1,
    })

    mockGetTenantQuota.mockResolvedValue({
      tenant_id: 10,
      max_users: 50,
      max_documents: 100,
      max_storage_mb: 1024,
      current_users: 12,
      current_documents: 45,
      updated_at: '2026-01-01T00:00:00Z',
    })

    mockUpdateTenantQuota.mockImplementation((_id: number, payload: unknown) =>
      Promise.resolve({
        tenant_id: 10,
        ...(payload as Record<string, unknown>),
        current_users: 12,
        current_documents: 45,
        updated_at: '2026-01-01T00:00:00Z',
      }),
    )
  })

  it('renders the admin ops page with system status tab by default', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Admin Operations')).toBeDefined()
    })
    expect(screen.getByText('System Status')).toBeDefined()
  })

  it('switches to Tenant Management tab and shows tenant list', async () => {
    renderPage()

    // Click Tenant Management tab
    await waitFor(() => {
      expect(screen.getByText('Tenant Management')).toBeDefined()
    })
    fireEvent.click(screen.getByText('Tenant Management'))

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeDefined()
    })
  })

  it('selects a tenant, shows quota editor, modifies and saves', async () => {
    renderPage()

    // Go to tenant management
    await waitFor(() => screen.getByText('Tenant Management'))
    fireEvent.click(screen.getByText('Tenant Management'))

    // Wait for tenant list to appear
    await waitFor(() => screen.getByText('Acme Corp'))

    // Click on the tenant to select it
    fireEvent.click(screen.getByText('Acme Corp'))

    // Wait for quota editor to render
    await waitFor(() => {
      expect(screen.getByText(/Quota/)).toBeDefined()
    })

    // Verify current quota values are displayed
    const maxUsersInput = screen.getByDisplayValue('50')
    expect(maxUsersInput).toBeDefined()

    // Modify quota — change max users to 75
    fireEvent.change(maxUsersInput, { target: { value: '75' } })

    // Click save
    fireEvent.click(screen.getByText('Save Quota'))

    // Verify API was called with updated payload
    await waitFor(() => {
      expect(mockUpdateTenantQuota).toHaveBeenCalledWith(10, expect.objectContaining({
        max_users: 75,
      }))
    })
  })

  it('shows current usage counts alongside limits', async () => {
    renderPage()

    await waitFor(() => screen.getByText('Tenant Management'))
    fireEvent.click(screen.getByText('Tenant Management'))

    await waitFor(() => screen.getByText('Acme Corp'))
    fireEvent.click(screen.getByText('Acme Corp'))

    await waitFor(() => {
      expect(screen.getByText(/Current: 12/)).toBeDefined()
      expect(screen.getByText(/Current: 45/)).toBeDefined()
    })
  })
})
