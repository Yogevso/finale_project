import { useMemo } from 'react'
import Joyride from 'react-joyride'
import VisibilityChangeConfirmDialog from '@/components/VisibilityChangeConfirmDialog'
import { useTour } from '@/hooks/useTour'
import { documentsPageTour } from '@/lib/tour'
import PageHeader from '@/components/PageHeader'
import {
  BulkMetadataEditModal,
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
    controller.visibilityFilter !== '' ||
    controller.categoryFilter.trim().length > 0 ||
    controller.companyIdFilter !== null ||
    controller.dateFrom !== '' ||
    controller.dateTo !== ''
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
          categoryFilter={controller.categoryFilter}
          onCategoryFilterChange={controller.setCategoryFilter}
          companyIdFilter={controller.companyIdFilter}
          onCompanyIdFilterChange={controller.setCompanyIdFilter}
          dateFrom={controller.dateFrom}
          onDateFromChange={controller.setDateFrom}
          dateTo={controller.dateTo}
          onDateToChange={controller.setDateTo}
          savedViews={controller.savedViews}
          activeSavedViewId={controller.activeSavedViewId}
          onApplySavedView={controller.applySavedView}
          onSaveCurrentView={() => {
            const viewName = window.prompt('Name this saved view')
            if (viewName && viewName.trim()) {
              controller.saveCurrentView(viewName.trim())
            }
          }}
          onDeleteSavedView={controller.deleteSavedView}
          companies={controller.companiesQuery.data?.items ?? []}
          statusDetailsRef={controller.statusDetailsRef}
          visibilityDetailsRef={controller.visibilityDetailsRef}
        />
      )}

      {!controller.isQuickCreateMode && controller.isManager && controller.selectedDocumentIds.length > 0 ? (
        <div className="surface-card flex flex-col gap-3 rounded-2xl p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-900">
              {controller.selectedDocumentIds.length} document(s) selected
            </p>
            <p className="text-sm text-slate-500">Bulk-update category, visibility, and company assignments.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={controller.clearSelection} className="btn-ghost">
              Clear selection
            </button>
            <button onClick={() => controller.setShowBulkEditModal(true)} className="btn-primary">
              Bulk edit metadata
            </button>
          </div>
        </div>
      ) : null}

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
            selectedDocumentIds={controller.selectedDocumentIds}
            onToggleDocumentSelection={controller.toggleDocumentSelection}
            onToggleAllVisibleDocuments={controller.toggleAllVisibleDocuments}
            onArchiveOrRestore={controller.handleArchiveOrRestore}
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

      {controller.showBulkEditModal ? (
        <BulkMetadataEditModal
          selectedCount={controller.selectedDocumentIds.length}
          documentIds={controller.selectedDocumentIds}
          isSubmitting={controller.bulkMetadataMutation.isPending}
          onClose={() => controller.setShowBulkEditModal(false)}
          onSubmit={(payload) => controller.bulkMetadataMutation.mutate(payload)}
        />
      ) : null}

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
