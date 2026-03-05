import { Profiler } from 'react'
import type { ProfilerOnRenderCallback } from 'react'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import DocumentsPage from '@/pages/DocumentsPage'
import { useDocumentsPageController } from '@/pages/documents/hooks'

vi.mock('@/pages/documents/hooks', () => ({
  useDocumentsPageController: vi.fn(),
}))

vi.mock('@/components/PageHeader', () => ({
  default: ({ title }: { title: string }) => <div data-testid="page-header">{title}</div>,
}))

vi.mock('@/components/VisibilityChangeConfirmDialog', () => ({
  default: () => null,
}))

vi.mock('@/pages/documents/components', () => ({
  DocumentsFiltersToolbar: () => <div data-testid="filters-toolbar" />,
  DocumentsTable: ({ data }: { data?: { items?: unknown[] } }) => (
    <div data-testid="documents-table">{data?.items?.length ?? 0}</div>
  ),
  DocumentsQuickCreatePanel: () => <div data-testid="quick-create-panel" />,
  CreateDocumentModal: () => null,
  UploadDocumentModal: () => null,
  QuickStartModal: () => null,
}))

const mockedController = vi.mocked(useDocumentsPageController)

function buildControllerWithDocuments(count: number) {
  return {
    isEditor: true,
    isManager: true,
    isQuickCreateMode: false,
    showCreateModal: false,
    showUploadModal: false,
    showQuickStartModal: false,
    search: '',
    statusFilter: '',
    visibilityFilter: '',
    statusDetailsRef: { current: null },
    visibilityDetailsRef: { current: null },
    page: 1,
    visibilityOverrides: {},
    pendingVisibilityChange: null,
    visibilityMutation: { isPending: false },
    documentsQuery: {
      isLoading: false,
      data: {
        total: count,
        items: Array.from({ length: count }, (_, index) => ({
          id: index + 1,
          title: `Document ${index + 1}`,
        })),
      },
    },
    setShowUploadModal: vi.fn(),
    setShowCreateModal: vi.fn(),
    setShowQuickStartModal: vi.fn(),
    setSearch: vi.fn(),
    setStatusFilter: vi.fn(),
    setVisibilityFilter: vi.fn(),
    setPage: vi.fn(),
    handleDelete: vi.fn(),
    handleVisibilityChange: vi.fn(),
    cancelPendingVisibilityChange: vi.fn(),
    confirmPendingVisibilityChange: vi.fn(),
  }
}

describe('DocumentsPage render performance', () => {
  it('renders 100 documents in under 2 seconds', () => {
    mockedController.mockReturnValue(buildControllerWithDocuments(100) as never)

    let profilerDurationMs = 0
    const onRender: ProfilerOnRenderCallback = (
      _id,
      _phase,
      actualDuration,
    ) => {
      profilerDurationMs += actualDuration
    }

    const wallStartedAt = performance.now()
    render(
      <Profiler id="documents-page" onRender={onRender}>
        <DocumentsPage />
      </Profiler>,
    )
    const wallDurationMs = performance.now() - wallStartedAt

    expect(wallDurationMs).toBeLessThan(2000)
    expect(profilerDurationMs).toBeLessThan(2000)
  })
})
