import { FilePlus2, FileSearch, UploadCloud } from 'lucide-react'

type DocumentsEmptyStateProps = {
  hasActiveFilters: boolean
  canCreate: boolean
  onCreate: () => void
  onUpload: () => void
  onClearFilters: () => void
}

export function DocumentsEmptyState({
  hasActiveFilters,
  canCreate,
  onCreate,
  onUpload,
  onClearFilters,
}: DocumentsEmptyStateProps) {
  return (
    <div className="surface-card rounded-2xl border border-slate-200 p-10 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-sky-100 text-sky-700">
        {hasActiveFilters ? (
          <FileSearch className="h-7 w-7" />
        ) : (
          <FilePlus2 className="h-7 w-7" />
        )}
      </div>

      <h3 className="mt-4 text-xl font-display font-semibold text-slate-900">
        {hasActiveFilters ? 'No documents match your filters' : 'No documents yet'}
      </h3>

      <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600">
        {hasActiveFilters
          ? 'Try clearing search and filters to see more results.'
          : canCreate
            ? 'Start by creating your first document or uploading an existing file.'
            : 'Documents will appear here once your team publishes content.'}
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {hasActiveFilters ? (
          <button type="button" className="btn-primary" onClick={onClearFilters}>
            Clear filters
          </button>
        ) : canCreate ? (
          <>
            <button type="button" className="btn-primary" onClick={onCreate}>
              Create document
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex items-center gap-2"
              onClick={onUpload}
            >
              <UploadCloud className="h-4 w-4" />
              Upload file
            </button>
          </>
        ) : null}
      </div>
    </div>
  )
}
