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
        aria-label="Start a new document"
        tabIndex={-1}
        className="modal-content relative z-10 w-full max-w-2xl p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title text-xl">Start a new document</h2>
          <button type="button" onClick={onClose} className="btn-icon h-9 w-9 text-slate-500 hover:bg-slate-100" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="body-copy mb-6">Choose how you want to create your document.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button type="button" onClick={onCreate} className="surface-card-hover rounded-2xl p-6 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-sky-100 text-sky-600">
              <FilePlus className="h-6 w-6" />
            </div>
            <div className="card-title text-lg">New Document</div>
            <p className="body-copy mt-2">Start from a blank document and add content.</p>
          </button>
          <button type="button" onClick={onUpload} className="surface-card-hover rounded-2xl p-6 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600">
              <Upload className="h-6 w-6" />
            </div>
            <div className="card-title text-lg">Upload File</div>
            <p className="body-copy mt-2">
              Upload a DOCX or PPTX file and generate a document.
            </p>
          </button>
        </div>
      </div>
    </div>
  )
}
