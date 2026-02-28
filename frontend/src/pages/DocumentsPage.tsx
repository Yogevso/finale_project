import PageHeader from '@/components/PageHeader'
import {
  CreateDocumentModal,
  DocumentsFiltersToolbar,
  DocumentsQuickCreatePanel,
  DocumentsTable,
  QuickStartModal,
  UploadDocumentModal,
} from '@/pages/documents/components'
import { useDocumentsPageController } from '@/pages/documents/hooks'

export default function DocumentsPage() {
  const controller = useDocumentsPageController()
  const totalDocuments = controller.documentsQuery.data?.total ?? 0

  return (
    <div className="space-y-8">
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
      )}

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

