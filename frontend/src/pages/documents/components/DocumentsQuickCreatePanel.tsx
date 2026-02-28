type DocumentsQuickCreatePanelProps = {
  onCreate: () => void
  onUpload: () => void
}

export function DocumentsQuickCreatePanel({ onCreate, onUpload }: DocumentsQuickCreatePanelProps) {
  return (
    <div className="surface-card rounded-2xl p-6">
      <h2 className="text-lg font-display font-semibold text-slate-900 mb-2">Create a new document</h2>
      <p className="text-sm text-slate-500 mb-6">Choose how you want to start.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button onClick={onCreate} className="surface-card-hover rounded-2xl p-6 text-left">
          <div className="text-3xl mb-3">📝</div>
          <div className="text-lg font-display font-semibold text-slate-900">New Document</div>
          <p className="text-sm text-slate-500 mt-2">Start from a blank document and add content.</p>
        </button>
        <button onClick={onUpload} className="surface-card-hover rounded-2xl p-6 text-left">
          <div className="text-3xl mb-3">📤</div>
          <div className="text-lg font-display font-semibold text-slate-900">Upload File</div>
          <p className="text-sm text-slate-500 mt-2">
            Upload a PDF or Word file and generate a document.
          </p>
        </button>
      </div>
    </div>
  )
}

