import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import SystemSetupPage from './SystemSetupPage'

const toastSuccessMock = vi.fn()
const toastErrorMock = vi.fn()

const mockGetSystemSettings = vi.fn()
const mockUpdateSystemSettings = vi.fn()
const mockGetSystemDocumentLifecycleSettings = vi.fn()
const mockUpdateSystemDocumentLifecycleSettings = vi.fn()
const mockGetSystemEmailSettings = vi.fn()
const mockUpdateSystemEmailSettings = vi.fn()
const mockGetRbacPolicies = vi.fn()
const mockUpdateRbacPolicies = vi.fn()
const mockListAudienceAlertRules = vi.fn()
const mockCreateAudienceAlertRule = vi.fn()
const mockDeleteAudienceAlertRule = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    getSystemSettings: (...args: unknown[]) => mockGetSystemSettings(...args),
    updateSystemSettings: (...args: unknown[]) => mockUpdateSystemSettings(...args),
    getSystemDocumentLifecycleSettings: (...args: unknown[]) =>
      mockGetSystemDocumentLifecycleSettings(...args),
    updateSystemDocumentLifecycleSettings: (...args: unknown[]) =>
      mockUpdateSystemDocumentLifecycleSettings(...args),
    getSystemEmailSettings: (...args: unknown[]) => mockGetSystemEmailSettings(...args),
    updateSystemEmailSettings: (...args: unknown[]) => mockUpdateSystemEmailSettings(...args),
    getRbacPolicies: (...args: unknown[]) => mockGetRbacPolicies(...args),
    updateRbacPolicies: (...args: unknown[]) => mockUpdateRbacPolicies(...args),
    listAudienceAlertRules: (...args: unknown[]) => mockListAudienceAlertRules(...args),
    createAudienceAlertRule: (...args: unknown[]) => mockCreateAudienceAlertRule(...args),
    deleteAudienceAlertRule: (...args: unknown[]) => mockDeleteAudienceAlertRule(...args),
  },
}))

vi.mock('@/lib/toast', () => ({
  extractApiErrorMessage: (_error: unknown, fallback: string) => fallback,
  useToast: () => ({
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: (...args: unknown[]) => toastErrorMock(...args),
    info: vi.fn(),
  }),
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SystemSetupPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SystemSetupPage email delivery', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    mockGetSystemSettings.mockResolvedValue({
      settings: {
        'documents.max_versions': 25,
      },
    })
    mockGetSystemDocumentLifecycleSettings.mockResolvedValue({
      settings: {
        auto_archive_enabled: false,
        auto_archive_after_value: 12,
        auto_archive_after_unit: 'months',
        auto_archive_basis: 'last_published',
        delete_grace_days: 30,
      },
      source: 'default',
      updated_at: null,
      updated_by: null,
    })
    mockGetSystemEmailSettings.mockResolvedValue({
      settings: {
        enabled: true,
        host: 'smtp.gmail.com',
        port: 587,
        security: 'starttls',
        username: 'try1@gmail.com',
        from_email: 'try1@gmail.com',
        from_name: 'Try One',
        password_configured: true,
        password_masked: '••••1234',
      },
      source: 'environment',
      updated_at: null,
      updated_by: null,
    })
    mockGetRbacPolicies.mockResolvedValue({ policies: [] })
    mockListAudienceAlertRules.mockResolvedValue([])
    mockUpdateSystemSettings.mockResolvedValue({ settings: {} })
    mockUpdateRbacPolicies.mockResolvedValue({ policies: [] })
    mockCreateAudienceAlertRule.mockResolvedValue({
      id: 'rule-1',
      metric: 'visibility_changes_per_document',
      threshold: 5,
      window_minutes: 60,
      enabled: true,
      created_at: '2026-03-27T10:00:00Z',
      updated_at: '2026-03-27T10:00:00Z',
    })
    mockDeleteAudienceAlertRule.mockResolvedValue({ ok: true })
    mockUpdateSystemDocumentLifecycleSettings.mockImplementation(
      async (payload: Record<string, unknown>) => ({
        settings: {
          auto_archive_enabled: payload.auto_archive_enabled,
          auto_archive_after_value: payload.auto_archive_after_value,
          auto_archive_after_unit: payload.auto_archive_after_unit,
          auto_archive_basis: 'last_published',
          delete_grace_days: 30,
        },
        source: 'database',
        updated_at: '2026-03-28T09:15:00Z',
        updated_by: 1,
      }),
    )
    mockUpdateSystemEmailSettings.mockImplementation(async (payload: Record<string, unknown>) => ({
      settings: {
        enabled: payload.enabled,
        host: payload.host,
        port: payload.port,
        security: payload.security,
        username: payload.username,
        from_email: payload.from_email,
        from_name: payload.from_name,
        password_configured: payload.clear_password ? false : true,
        password_masked: payload.clear_password ? null : '••••5678',
      },
      source: 'database',
      updated_at: '2026-03-27T12:00:00Z',
      updated_by: 1,
    }))
  })

  it('renders the current runtime sender metadata', async () => {
    renderPage()

    expect(await screen.findByTestId('system-email-from-email')).toBeInTheDocument()
    expect(screen.getByText(/environment default/i)).toBeInTheDocument()
    expect(screen.getByTestId('system-email-from-email')).toHaveValue('try1@gmail.com')
    expect(screen.getByTestId('system-email-from-name')).toHaveValue('Try One')
    expect(screen.getAllByText(/••••1234/i)).toHaveLength(2)
  })

  it('renders the current document lifecycle metadata', async () => {
    renderPage()

    expect(await screen.findByTestId('document-lifecycle-value')).toBeInTheDocument()
    expect(screen.getAllByText(/system default/i)).toHaveLength(2)
    expect(screen.getByText(/30 days/i)).toBeInTheDocument()
    expect(screen.getByTestId('document-lifecycle-value')).toHaveValue(12)
    expect(screen.getByTestId('document-lifecycle-unit')).toHaveValue('months')
  })

  it('saves updated document lifecycle settings', async () => {
    renderPage()

    await screen.findByTestId('document-lifecycle-value')

    fireEvent.click(screen.getByTestId('document-lifecycle-enabled-toggle'))
    fireEvent.change(screen.getByTestId('document-lifecycle-value'), {
      target: { value: '18' },
    })
    fireEvent.change(screen.getByTestId('document-lifecycle-unit'), {
      target: { value: 'months' },
    })
    fireEvent.click(screen.getByTestId('document-lifecycle-save'))

    await waitFor(() => {
      expect(mockUpdateSystemDocumentLifecycleSettings).toHaveBeenCalledWith({
        auto_archive_enabled: true,
        auto_archive_after_value: 18,
        auto_archive_after_unit: 'months',
      })
    })

    expect(toastSuccessMock).toHaveBeenCalledWith(
      'Document lifecycle settings saved',
      'Auto-archive enabled',
    )
  })

  it('saves updated email delivery settings', async () => {
    renderPage()

    await screen.findByTestId('system-email-from-email')

    fireEvent.change(screen.getByTestId('system-email-from-email'), {
      target: { value: 'try2@gmail.com' },
    })
    fireEvent.change(screen.getByTestId('system-email-from-name'), {
      target: { value: 'Try Two' },
    })
    fireEvent.change(screen.getByTestId('system-email-password'), {
      target: { value: 'app-password-2' },
    })
    fireEvent.click(screen.getByTestId('system-email-save'))

    await waitFor(() => {
      expect(mockUpdateSystemEmailSettings).toHaveBeenCalledWith({
        enabled: true,
        host: 'smtp.gmail.com',
        port: 587,
        security: 'starttls',
        username: 'try1@gmail.com',
        password: 'app-password-2',
        clear_password: false,
        from_email: 'try2@gmail.com',
        from_name: 'Try Two',
      })
    })

    expect(toastSuccessMock).toHaveBeenCalledWith(
      'Email delivery settings saved',
      'Try Two <try2@gmail.com>',
    )
  })

  it('allows clearing the stored password without entering a replacement', async () => {
    renderPage()

    await screen.findByTestId('system-email-clear-password')

    fireEvent.click(screen.getByTestId('system-email-clear-password'))
    fireEvent.click(screen.getByTestId('system-email-save'))

    await waitFor(() => {
      expect(mockUpdateSystemEmailSettings).toHaveBeenCalledWith({
        enabled: true,
        host: 'smtp.gmail.com',
        port: 587,
        security: 'starttls',
        username: 'try1@gmail.com',
        password: null,
        clear_password: true,
        from_email: 'try1@gmail.com',
        from_name: 'Try One',
      })
    })
  })
})
