import { useMemo } from 'react'
import Joyride from 'react-joyride'
import VisibilityChangeConfirmDialog from '@/components/VisibilityChangeConfirmDialog'
import { useTour } from '@/hooks/useTour'
import { documentsPageTour } from '@/lib/tour'
import PageHeader from '@/components/PageHeader'
import {
  CreateDocumentModal,
  DocumentsEmptyState,
  DocumentsFiltersToolbar,
  DocumentsQuickCreatePanel,
  DocumentsTable,
  QuickStartModal,
  UploadDocumentModal,
} from '@/pages/documents/components'
import { useDocumentsPageController } from '@/pages/documents/hooks'

export default function DocumentsPage() {
  const controller = useDocumentsPageController()
  const tourSteps = useMemo(
    () =>
      controller.isEditor
        ? documentsPageTour
        : documentsPageTour.filter(
            (step) => step.target !== '[data-tour="documents-create-button"]',
          ),
    [controller.isEditor],
  )
  const tour = useTour('documents-page', tourSteps)
  const totalDocuments = controller.documentsQuery.data?.total ?? 0
  const hasActiveFilters =
    controller.search.trim().length > 0 ||
    controller.statusFilter !== '' ||
    controller.visibilityFilter !== ''
  const showGuidedEmptyState =
    !controller.documentsQuery.isLoading &&
    (controller.documentsQuery.data?.items.length ?? 0) === 0

  return (
    <div className="space-y-8">
      <Joyride
        steps={tourSteps}
        run={tour.run}
        callback={tour.onJoyrideCallback}
        continuous
        showProgress
        showSkipButton
        disableScrolling
      />

      <PageHeader
        title="Documents"
        subtitle="Manage all documents"
        actions={
          controller.isEditor ? (
            <>
              <button
                onClick={() => controller.setShowUploadModal(true)}
                className="btn-secondary flex items-center gap-2"
              >
                <span>📤</span> Upload File
              </button>
              <button
                onClick={() => controller.setShowCreateModal(true)}
                className="btn-primary"
                data-tour="documents-create-button"
              >
                + New Document
              </button>
            </>
          ) : undefined
        }
      />

      {!controller.isQuickCreateMode && (
        <DocumentsFiltersToolbar
          isLoading={controller.documentsQuery.isLoading}
          totalDocuments={totalDocuments}
          search={controller.search}
          onSearchChange={controller.setSearch}
          statusFilter={controller.statusFilter}
          onStatusFilterChange={controller.setStatusFilter}
          visibilityFilter={controller.visibilityFilter}
          onVisibilityFilterChange={controller.setVisibilityFilter}
          statusDetailsRef={controller.statusDetailsRef}
          visibilityDetailsRef={controller.visibilityDetailsRef}
        />
      )}

      {controller.isQuickCreateMode && (
        <DocumentsQuickCreatePanel
          onCreate={() => controller.setShowCreateModal(true)}
          onUpload={() => controller.setShowUploadModal(true)}
        />
      )}

      {!controller.isQuickCreateMode && (
        showGuidedEmptyState ? (
          <DocumentsEmptyState
            hasActiveFilters={hasActiveFilters}
            canCreate={controller.isEditor}
            onCreate={() => controller.setShowCreateModal(true)}
            onUpload={() => controller.setShowUploadModal(true)}
            onClearFilters={controller.resetFilters}
          />
        ) : (
          <DocumentsTable
            data={controller.documentsQuery.data}
            isLoading={controller.documentsQuery.isLoading}
            isManager={controller.isManager}
            page={controller.page}
            visibilityOverrides={controller.visibilityOverrides}
            onDelete={controller.handleDelete}
            onVisibilityChange={controller.handleVisibilityChange}
            onPageChange={controller.setPage}
          />
        )
      )}

      <VisibilityChangeConfirmDialog
        isOpen={controller.pendingVisibilityChange !== null}
        fromVisibility={controller.pendingVisibilityChange?.currentVisibility ?? 'internal'}
        toVisibility={controller.pendingVisibilityChange?.nextVisibility ?? 'internal'}
        documentTitle={controller.pendingVisibilityChange?.title}
        onCancel={controller.cancelPendingVisibilityChange}
        onConfirm={controller.confirmPendingVisibilityChange}
        isSubmitting={controller.visibilityMutation.isPending}
      />

      {controller.showCreateModal && (
        <CreateDocumentModal onClose={() => controller.setShowCreateModal(false)} />
      )}

      {controller.showUploadModal && (
        <UploadDocumentModal onClose={() => controller.setShowUploadModal(false)} />
      )}

      {controller.showQuickStartModal && (
        <QuickStartModal
          onClose={() => controller.setShowQuickStartModal(false)}
          onCreate={() => {
            controller.setShowQuickStartModal(false)
            controller.setShowCreateModal(true)
          }}
          onUpload={() => {
            controller.setShowQuickStartModal(false)
            controller.setShowUploadModal(true)
          }}
        />
      )}
    </div>
  )
}
