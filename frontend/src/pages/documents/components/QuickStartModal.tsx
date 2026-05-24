import { FilePlus, Upload, X } from 'lucide-react'
import { useFocusTrap } from '@/hooks/useAccessibility'

type QuickStartModalProps = {
  onClose: () => void
  onCreate: () => void
  onUpload: () => void
}

export function QuickStartModal({ onClose, onCreate, onUpload }: QuickStartModalProps) {
  const { containerRef } = useFocusTrap<HTMLDivElement>(onClose)

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-transparent"
        onClick={onClose}
        aria-label="Close start document dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Add New Document"
        tabIndex={-1}
        className="modal-content relative z-10 w-full max-w-2xl p-6"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="section-title text-xl">Add New Document</h2>
          <button type="button" onClick={onClose} className="btn-icon h-9 w-9 text-slate-500 hover:bg-slate-100" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="body-copy mb-6">
          Choose how you would like to create your document.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button type="button" onClick={onUpload} className="surface-card-hover rounded-2xl p-6 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600">
              <Upload className="h-6 w-6" />
            </div>
            <div className="card-title text-lg">From Existing File</div>
            <p className="body-copy mt-2">Upload a PDF, Word, or PowerPoint file and generate a working draft.</p>
            <p className="mt-3 text-sm text-slate-500">Best for existing policies, presentations, and source files.</p>
          </button>
          <button type="button" onClick={onCreate} className="surface-card-hover rounded-2xl p-6 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 text-blue-600">
              <FilePlus className="h-6 w-6" />
            </div>
            <div className="card-title text-lg">From Scratch</div>
            <p className="body-copy mt-2">Start from a blank document and build your content from scratch.</p>
            <p className="mt-3 text-sm text-slate-500">Best for net-new drafts, templates, and quick edits.</p>
          </button>
        </div>
      </div>
    </div>
  )
}
