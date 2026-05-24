import { RotateCcw, Trash2, X } from 'lucide-react'
import type { RemovedSection } from '@/pages/document-detail/hooks/useContentEditingFlow'

interface RemovedSectionsPanelProps {
  removedSections: RemovedSection[]
  onRestore: (section: RemovedSection) => void
  onClose: () => void
}

export function RemovedSectionsPanel({
  removedSections,
  onRestore,
  onClose,
}: RemovedSectionsPanelProps) {
  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close removed sections"
      />
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <Trash2 className="h-5 w-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900">Removed Sections</h2>
            {removedSections.length > 0 && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {removedSections.length}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {removedSections.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
                <Trash2 className="h-6 w-6 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-700">No removed sections</p>
              <p className="mt-1 text-sm text-slate-500">
                Sections you remove will appear here until a review is approved.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                These sections were removed from the document. They will be kept here until a review
                is submitted and approved. You can restore any section to add it back.
              </p>
              <ul className="space-y-3">
                {removedSections.map((section) => {
                  const plainText = section.html
                    .replace(/<[^>]*>/g, ' ')
                    .replace(/\s+/g, ' ')
                    .trim()
                  const preview = plainText.slice(0, 200) + (plainText.length > 200 ? '...' : '')
                  const removedDate = new Date(section.removedAt)
                  return (
                    <li
                      key={section.id + section.removedAt}
                      className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-slate-900 truncate">
                            {section.text}
                          </p>
                          <p className="mt-1 text-xs leading-relaxed text-slate-500">
                            {preview}
                          </p>
                          <p className="mt-2 text-xs text-slate-400">
                            Removed{' '}
                            {removedDate.toLocaleDateString(undefined, {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => onRestore(section)}
                          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100"
                          title={`Restore "${section.text}"`}
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          Restore
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
