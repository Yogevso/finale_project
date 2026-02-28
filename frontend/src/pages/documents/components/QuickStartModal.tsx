type QuickStartModalProps = {
  onClose: () => void
  onCreate: () => void
  onUpload: () => void
}

export function QuickStartModal({ onClose, onCreate, onUpload }: QuickStartModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-display font-bold text-slate-900">Start a new document</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl text-slate-500">
            x
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-6">Choose how you want to create your document.</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button onClick={onCreate} className="surface-card-hover rounded-2xl p-6 text-left">
            <div className="text-3xl mb-3">NEW</div>
            <div className="text-lg font-display font-semibold text-slate-900">New Document</div>
            <p className="text-sm text-slate-500 mt-2">Start from a blank document and add content.</p>
          </button>
          <button onClick={onUpload} className="surface-card-hover rounded-2xl p-6 text-left">
            <div className="text-3xl mb-3">UP</div>
            <div className="text-lg font-display font-semibold text-slate-900">Upload File</div>
            <p className="text-sm text-slate-500 mt-2">
              Upload a PDF or Word file and generate a document.
            </p>
          </button>
        </div>
      </div>
    </div>
  )
}

