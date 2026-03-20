import { FilePlus2, UploadCloud } from 'lucide-react'

type DocumentsQuickCreatePanelProps = {
  onCreate: () => void
  onUpload: () => void
}

export function DocumentsQuickCreatePanel({ onCreate, onUpload }: DocumentsQuickCreatePanelProps) {
  return (
    <div className="surface-card rounded-2xl p-6">
      <h2 className="section-title">Create a new document</h2>
      <p className="body-copy mt-2 mb-6">Choose how you want to start.</p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <button
          type="button"
          onClick={onCreate}
          className="surface-card-hover rounded-2xl p-6 text-left"
        >
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200">
            <FilePlus2 className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="card-title mt-4 text-lg">New Document</div>
          <p className="body-copy mt-2">Start from a blank document and add content.</p>
        </button>
        <button
          type="button"
          onClick={onUpload}
          className="surface-card-hover rounded-2xl p-6 text-left"
        >
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">
            <UploadCloud className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="card-title mt-4 text-lg">Upload File</div>
          <p className="body-copy mt-2">
            Upload a DOCX or PPTX file and generate a document.
          </p>
        </button>
      </div>
    </div>
  )
}
