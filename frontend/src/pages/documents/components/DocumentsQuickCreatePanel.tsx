import { FilePlus2, UploadCloud } from 'lucide-react'

type DocumentsQuickCreatePanelProps = {
  onCreate: () => void
  onUpload: () => void
}

export function DocumentsQuickCreatePanel({ onCreate, onUpload }: DocumentsQuickCreatePanelProps) {
  return (
    <div className="surface-card rounded-3xl border border-slate-200 p-6 md:p-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Quick Start</div>
          <h2 className="section-title mt-2">How do you want to begin?</h2>
          <p className="body-copy mt-2 max-w-2xl">
            Choose the fastest starting point, then set visibility and company access after the draft is ready.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-medium text-slate-600">
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1">Blank draft</span>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1">DOCX / PPTX import</span>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1">Audience settings later</span>
        </div>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <button
          type="button"
          onClick={onCreate}
          className="surface-card-hover rounded-2xl border border-slate-200/80 p-6 text-left"
        >
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200">
            <FilePlus2 className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="card-title mt-4 text-lg">New Document</div>
          <p className="body-copy mt-2">Start from a blank document and add content from scratch.</p>
          <p className="mt-3 text-sm text-slate-500">Best for policies, announcements, and fast draft work.</p>
        </button>
        <button
          type="button"
          onClick={onUpload}
          className="surface-card-hover rounded-2xl border border-slate-200/80 p-6 text-left"
        >
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200">
            <UploadCloud className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="card-title mt-4 text-lg">Upload File</div>
          <p className="body-copy mt-2">Upload a DOCX or PPTX file and generate a working document.</p>
          <p className="mt-3 text-sm text-slate-500">Best for existing source material you want to keep editing in the platform.</p>
        </button>
      </div>
      <p className="helper-copy mt-5">
        After creation, open Details to assign companies, review visibility, and finish audience setup.
      </p>
    </div>
  )
}
