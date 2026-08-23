import { useMemo } from 'react'
import Joyride from 'react-joyride'

import { ErrorState } from '@/components/ErrorState'
import PageHeader from '@/components/PageHeader'
import VisibilityChangeConfirmDialog from '@/components/VisibilityChangeConfirmDialog'
import { useTour } from '@/hooks/useTour'
import { documentsPageTour } from '@/lib/tour'
import { DOCUMENT_INPUT_LIMITS, normalizeSingleLineInput } from '@/lib/uiInputRules'
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
  const currentPageItems = controller.documentsQuery.data?.items ?? []
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
  const hasDocumentsError = controller.documentsQuery.isError ?? false
  const visibleDocumentsCount = currentPageItems.length
  const publishedCount = currentPageItems.filter((document) => document.status === 'active').length
  const attentionCount = currentPageItems.filter(
    (document) => document.status === 'draft' || document.status === 'pending_review',
  ).length
  const companyScopedCount = currentPageItems.filter(
    (document) =>
      (controller.visibilityOverrides[document.id] || document.visibility || 'internal') === 'company',
  ).length
  const pageHeaderMeta = controller.showDeleted ? (
    <div className="flex flex-wrap gap-2">
      <span className="admin-summary-badge">{totalDocuments} recoverable</span>
      <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">
        Purge after 30 days
      </span>
      <span className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs font-medium text-slate-600">
        {controller.isAdmin ? 'Admins can restore or purge.' : 'Recovery view only.'}
      </span>
    </div>
  ) : (
    <div className="grid gap-3 md:grid-cols-3">
      <div className="rounded-2xl border border-slate-200/80 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Current View</div>
        <div className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{visibleDocumentsCount}</div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          {hasActiveFilters ? 'documents match the current filters on this page.' : 'documents are visible on this page.'}
        </p>
      </div>
      <div className="rounded-2xl border border-slate-200/80 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Workflow</div>
        <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-100">
          Published {publishedCount} • Needs attention {attentionCount}
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Drafts and review items stay visible here until they are published or archived.
        </p>
      </div>
      <div className="rounded-2xl border border-slate-200/80 bg-white/80 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/70">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Audience</div>
        <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-100">
          Company-visible {companyScopedCount}
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          Assign companies in Details, then publish the document before customers can see it.
        </p>
      </div>
    </div>
  )

  return (
    <div className="page-stack-lg">
      <Joyride
        steps={tourSteps}
        run={tour.run}
        callback={tour.onJoyrideCallback}
        continuous
        showProgress
        showSkipButton
        disableScrolling
        disableOverlay
      />

      <PageHeader
        title="Documents"
        subtitle={
          controller.showDeleted
            ? 'Restore documents during the 30-day recovery window or permanently remove them when needed.'
            : 'Create, upload, filter, and manage audience access from a single workspace.'
        }
        meta={pageHeaderMeta}
        actions={
          controller.isEditor && !controller.showDeleted ? (
            <button
              type="button"
              onClick={() => controller.setShowQuickStartModal(true)}
              className="btn-primary table-action-btn"
              data-tour="documents-create-button"
            >
              + New Document
            </button>
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
          onResetFilters={controller.resetFilters}
          savedViews={controller.savedViews}
          activeSavedViewId={controller.activeSavedViewId}
          onApplySavedView={controller.applySavedView}
          onSaveCurrentView={() => {
            const viewName = window.prompt('Name this saved view')
            const normalizedViewName = normalizeSingleLineInput(
              viewName,
              DOCUMENT_INPUT_LIMITS.savedViewName,
            )
            if (normalizedViewName) {
              controller.saveCurrentView(normalizedViewName)
            }
          }}
          onDeleteSavedView={controller.deleteSavedView}
          companies={controller.companiesQuery.data?.items ?? []}
          categorySuggestions={controller.categorySuggestions}
          searchSuggestions={controller.searchSuggestions}
          statusDetailsRef={controller.statusDetailsRef}
          visibilityDetailsRef={controller.visibilityDetailsRef}
          isAdmin={controller.isAdmin}
          showDeleted={controller.showDeleted}
          onShowDeletedChange={controller.setShowDeleted}
        />
      )}

      {!controller.isQuickCreateMode &&
      controller.isManager &&
      !controller.showDeleted &&
      controller.selectedDocumentIds.length > 0 ? (
        <div className="surface-card flex flex-col gap-3 rounded-2xl p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
              {controller.selectedDocumentIds.length} document(s) selected
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Bulk-update category, visibility, and company assignments.
            </p>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={controller.clearSelection} className="btn-ghost">
              Clear selection
            </button>
            <button type="button" onClick={() => controller.setShowBulkEditModal(true)} className="btn-primary">
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

      {!controller.isQuickCreateMode &&
        (hasDocumentsError ? (
          <ErrorState
            title="Documents could not be loaded"
            message="We could not fetch the document list for this workspace."
            onRetry={() => void controller.documentsQuery.refetch?.()}
          />
        ) : showGuidedEmptyState ? (
          controller.showDeleted ? (
            <div className="surface-card rounded-2xl p-8 text-center text-slate-600">
              No documents are waiting in the delete recovery window.
            </div>
          ) : (
          <DocumentsEmptyState
            hasActiveFilters={hasActiveFilters}
            canCreate={controller.isEditor}
            onCreate={() => controller.setShowCreateModal(true)}
            onUpload={() => controller.setShowUploadModal(true)}
            onClearFilters={controller.resetFilters}
          />
          )
        ) : (
          <DocumentsTable
            data={controller.documentsQuery.data}
            isLoading={controller.documentsQuery.isLoading}
            isManager={controller.isManager}
            isAdmin={controller.isAdmin}
            showDeleted={controller.showDeleted}
            page={controller.page}
            visibilityOverrides={controller.visibilityOverrides}
            selectedDocumentIds={controller.selectedDocumentIds}
            onToggleDocumentSelection={controller.toggleDocumentSelection}
            onToggleAllVisibleDocuments={controller.toggleAllVisibleDocuments}
            onArchiveOrRestore={controller.handleArchiveOrRestore}
            onDelete={controller.handleDelete}
            onRestoreDeleted={controller.handleRestoreDeleted}
            onPurgeDeleted={controller.handlePurgeDeleted}
            onVisibilityChange={controller.handleVisibilityChange}
            onPageChange={controller.setPage}
          />
        ))}

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
