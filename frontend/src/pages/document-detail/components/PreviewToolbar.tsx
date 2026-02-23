import type { Attachment } from '@/types'

interface PreviewToolbarProps {
  previewableAttachments: Attachment[]
  selectedAttachment: Attachment | null
  onSelectAttachment: (attachment: Attachment | null) => void
  isSelectedPdf: boolean
  isWordDoc: (attachment: Attachment | null) => boolean
  pdfPreviewMode: 'original' | 'reader'
  showingReaderView: boolean
  readerStatus: string | null
  readerError: string | null
  onSwitchToOriginalPdf: () => void
  onSwitchToReaderView: () => void
  onRetryReaderView: () => void
}

export function PreviewToolbar({
  previewableAttachments,
  selectedAttachment,
  onSelectAttachment,
  isSelectedPdf,
  isWordDoc,
  pdfPreviewMode,
  showingReaderView,
  readerStatus,
  readerError,
  onSwitchToOriginalPdf,
  onSwitchToReaderView,
  onRetryReaderView,
}: PreviewToolbarProps) {
  if (previewableAttachments.length <= 1 && !isSelectedPdf) {
    return null
  }

  return (
    <div className="border-b border-slate-200 p-3 bg-slate-50 flex flex-wrap items-center gap-3 justify-between">
      {previewableAttachments.length > 1 ? (
        <select
          value={selectedAttachment?.id || ''}
          onChange={(event) => {
            const attachment = previewableAttachments.find(
              (item) => item.id === Number(event.target.value),
            )
            onSelectAttachment(attachment || null)
          }}
          className="select-field text-sm min-w-[220px] max-w-md"
        >
          {previewableAttachments.map((attachment) => (
            <option key={attachment.id} value={attachment.id}>
              {attachment.filename} {isWordDoc(attachment) ? '(Word)' : ''}
            </option>
          ))}
        </select>
      ) : (
        <span className="text-sm font-medium text-slate-600">{selectedAttachment?.filename}</span>
      )}

      {isSelectedPdf && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-xl border border-slate-300 bg-white p-1">
            <button
              type="button"
              onClick={onSwitchToOriginalPdf}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                pdfPreviewMode === 'original'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              View Original (PDF)
            </button>
            <button
              type="button"
              onClick={onSwitchToReaderView}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                pdfPreviewMode === 'reader'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              Reader View
            </button>
          </div>

          {showingReaderView && (readerStatus === 'pending' || readerStatus === 'processing') && (
            <span className="text-xs text-slate-500">Generating Reader View...</span>
          )}

          {readerError && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-amber-700">{readerError}</span>
              {(readerStatus === 'failed' || readerStatus === 'ready') && (
                <button
                  type="button"
                  onClick={onRetryReaderView}
                  className="px-2 py-1 text-xs rounded-md border border-amber-300 text-amber-700 hover:bg-amber-50"
                >
                  Retry
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
