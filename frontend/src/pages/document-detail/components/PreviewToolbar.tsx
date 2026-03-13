import type { Attachment } from '@/types'
import type {
  DocumentFontSize,
  DocumentTheme,
} from '@/lib/documentReadingPreferences'

interface PreviewToolbarProps {
  previewableAttachments: Attachment[]
  selectedAttachment: Attachment | null
  onSelectAttachment: (attachment: Attachment | null) => void
  readerError: string | null
  onRetryReaderView: () => void
  fontSize: DocumentFontSize
  onSetFontSize: (value: DocumentFontSize) => void
  theme: DocumentTheme
  onSetTheme: (value: DocumentTheme) => void
}

export function PreviewToolbar({
  previewableAttachments,
  selectedAttachment,
  onSelectAttachment,
  readerError,
  onRetryReaderView,
  fontSize,
  onSetFontSize,
  theme,
  onSetTheme,
}: PreviewToolbarProps) {
  return (
    <div
      className="document-preview-toolbar border-b border-slate-200 p-3 bg-slate-50 flex flex-wrap items-center gap-3 justify-between"
      data-tour="document-preview-toolbar"
    >
      <div className="flex flex-wrap items-center gap-3">
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
            title="Select preview attachment"
          >
            {previewableAttachments.map((attachment) => (
              <option key={attachment.id} value={attachment.id}>
                {attachment.filename}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-sm font-medium text-slate-600">
            {selectedAttachment?.filename || 'Document preview'}
          </span>
        )}

        {readerError && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-amber-700">{readerError}</span>
            <button
              type="button"
              onClick={onRetryReaderView}
              className="px-2 py-1 text-xs rounded-md border border-amber-300 text-amber-700 hover:bg-amber-50"
            >
              Retry
            </button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div
          className="inline-flex items-center rounded-xl border border-slate-300 bg-white p-1"
          role="group"
          aria-label="Document font size"
        >
          <button
            type="button"
            onClick={() => onSetFontSize('small')}
            className={`px-2 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              fontSize === 'small'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            aria-label="Set small font size"
            title="Set small font size"
          >
            A-
          </button>
          <button
            type="button"
            onClick={() => onSetFontSize('default')}
            className={`px-2 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              fontSize === 'default'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            aria-label="Set default font size"
            title="Set default font size"
          >
            A
          </button>
          <button
            type="button"
            onClick={() => onSetFontSize('large')}
            className={`px-2 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              fontSize === 'large'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            aria-label="Set large font size"
            title="Set large font size"
          >
            A+
          </button>
        </div>

        <div
          className="inline-flex items-center rounded-xl border border-slate-300 bg-white p-1"
          role="group"
          aria-label="Document reading theme"
        >
          <button
            type="button"
            onClick={() => onSetTheme('light')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              theme === 'light'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            aria-label="Use light theme"
            title="Use light theme"
          >
            Light
          </button>
          <button
            type="button"
            onClick={() => onSetTheme('sepia')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              theme === 'sepia'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            aria-label="Use sepia theme"
            title="Use sepia theme"
          >
            Sepia
          </button>
          <button
            type="button"
            onClick={() => onSetTheme('dark')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              theme === 'dark'
                ? 'bg-sky-600 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
            aria-label="Use dark theme"
            title="Use dark theme"
          >
            Dark
          </button>
        </div>
      </div>
    </div>
  )
}
