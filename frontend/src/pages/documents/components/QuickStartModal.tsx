import { FilePlus, Upload, X } from 'lucide-react'
import { useFocusTrap } from '@/hooks/useAccessibility'

type QuickStartModalProps = {
  onClose: () => void
  onCreate: () => void
  onUpload: () => void
}

export function QuickStartModal({ onClose, onCreate, onUpload }: QuickStartModalProps) {
  const { containerRef, handleKeyDown } = useFocusTrap(onClose)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div ref={containerRef} role="dialog" aria-modal="true" aria-label="Start a new document" className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6" onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-display font-bold text-slate-900">Start a new document</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl text-slate-500" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-6">Choose how you want to create your document.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button onClick={onCreate} className="surface-card-hover rounded-2xl p-6 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-sky-100 text-sky-600">
              <FilePlus className="h-6 w-6" />
            </div>
            <div className="text-lg font-display font-semibold text-slate-900">New Document</div>
            <p className="text-sm text-slate-500 mt-2">Start from a blank document and add content.</p>
          </button>
          <button onClick={onUpload} className="surface-card-hover rounded-2xl p-6 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600">
              <Upload className="h-6 w-6" />
            </div>
            <div className="text-lg font-display font-semibold text-slate-900">Upload File</div>
            <p className="text-sm text-slate-500 mt-2">
              Upload a DOCX or PPTX file and generate a document.
            </p>
          </button>
        </div>
      </div>
    </div>
  )
}
