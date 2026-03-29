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
    <div className="surface-card rounded-3xl border border-slate-200 p-10 text-center">
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
          ? 'Try adjusting the filters below to widen the results without leaving the documents page.'
          : canCreate
            ? 'Start from a blank draft or upload an existing file. Visibility and company access can be configured after the draft exists.'
            : 'Documents will appear here once your team publishes or restores content for your workspace.'}
      </p>

      <div className={`mx-auto mt-6 grid max-w-4xl gap-3 ${hasActiveFilters ? 'md:grid-cols-3' : canCreate ? 'md:grid-cols-2' : 'md:grid-cols-1'}`}>
        {hasActiveFilters ? (
          <>
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-left">
              <div className="text-sm font-semibold text-slate-900">Search smarter</div>
              <p className="mt-1 text-sm text-slate-600">Search works on document title and document number.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-left">
              <div className="text-sm font-semibold text-slate-900">Filters stack together</div>
              <p className="mt-1 text-sm text-slate-600">Category, company, visibility, and date filters narrow the list at the same time.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-left">
              <div className="text-sm font-semibold text-slate-900">Reset quickly</div>
              <p className="mt-1 text-sm text-slate-600">Use the active chips or reset everything to get back to the full list.</p>
            </div>
          </>
        ) : canCreate ? (
          <>
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-left">
              <div className="text-sm font-semibold text-slate-900">New document</div>
              <p className="mt-1 text-sm text-slate-600">Best for net-new content, policies, and quick draft work.</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-left">
              <div className="text-sm font-semibold text-slate-900">Upload file</div>
              <p className="mt-1 text-sm text-slate-600">Import a DOCX or PPTX file and continue from existing source material.</p>
            </div>
          </>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-left">
            <div className="text-sm font-semibold text-slate-900">Need something here?</div>
            <p className="mt-1 text-sm text-slate-600">Ask an editor or manager to publish a document or restore one from the recovery window.</p>
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {hasActiveFilters ? (
          <button type="button" className="btn-primary" onClick={onClearFilters}>
            Reset all filters
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
