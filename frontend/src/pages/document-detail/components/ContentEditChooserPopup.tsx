import { X } from 'lucide-react'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'
import { useFocusTrap } from '@/hooks/useAccessibility'

interface ContentEditChooserPopupProps {
  sections: TocSection[]
  onClose: () => void
  onEditFullDocument: () => void
  onEditSection: (section: TocSection) => void
  onAddSection: (insertAfterIndex: number) => void
}

export function ContentEditChooserPopup({
  sections,
  onClose,
  onEditFullDocument,
  onEditSection,
  onAddSection,
}: ContentEditChooserPopupProps) {
  const { containerRef } = useFocusTrap<HTMLDivElement>(onClose)

  return (
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-transparent"
        onClick={onClose}
        aria-label="Close edit content options dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Edit Content Options"
        tabIndex={-1}
        className="modal-content relative z-10 flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden"
      >
        <div className="flex items-center justify-between border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700 px-6 py-4">
          <div>
            <h2 className="section-title text-xl !text-white">Edit Content Options</h2>
            <p className="helper-copy mt-1 !text-sky-100">
              Choose whether to edit an existing section or insert a new one.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="btn-icon h-9 w-9 border-white/20 bg-white/10 text-white hover:bg-white/20 hover:text-white"
            aria-label="Close edit options"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-6 overflow-auto p-6">
          <section className="surface-muted border-sky-200 bg-sky-50 p-4 dark:border-sky-900/60 dark:bg-sky-950/30">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="section-title text-base">Edit Entire Document</h3>
                <p className="body-copy mt-1">
                  Use this when you need to edit tables, mixed layouts, or content that spans multiple sections.
                </p>
              </div>
              <button
                type="button"
                onClick={onEditFullDocument}
                className="btn-primary table-action-btn"
              >
                Open Full Document Editor
              </button>
            </div>
          </section>

          <div className="grid gap-6 md:grid-cols-2">
          <section className="space-y-3">
            <h3 className="section-title text-base">Edit Existing Section</h3>
            <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
              {sections.map((section, idx) => (
                <button
                  key={`${section.id}-edit-${idx}`}
                  type="button"
                  onClick={() => onEditSection(section)}
                  className="surface-card-hover w-full p-3 text-left"
                >
                  <div className="helper-copy uppercase tracking-widest">
                    Section {idx + 1}
                  </div>
                  <div className="card-title mt-1 text-sm">{section.text}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="section-title text-base">Add New Section</h3>
            <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
              {sections.length === 0 && (
                <button
                  type="button"
                  onClick={() => onAddSection(-1)}
                  className="surface-card-hover w-full border-emerald-200 bg-emerald-50 p-3 text-left hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/30"
                >
                  <div className="card-title text-sm text-emerald-800 dark:text-emerald-200">Add first section</div>
                </button>
              )}

              {sections.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => onAddSection(-1)}
                    className="surface-card-hover w-full border-emerald-200 bg-emerald-50 p-3 text-left hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/30"
                  >
                    <div className="helper-copy uppercase tracking-widest text-emerald-700 dark:text-emerald-300">Insert</div>
                    <div className="card-title mt-1 text-sm text-emerald-800 dark:text-emerald-200">
                      Before "{sections[0]?.text}"
                    </div>
                  </button>

                  {sections.map((section, idx) => {
                    const nextSection = sections[idx + 1]
                    const label = nextSection
                      ? `Between "${section.text}" and "${nextSection.text}"`
                      : `After "${section.text}"`
                    return (
                      <button
                        key={`${section.id}-insert-${idx}`}
                        type="button"
                        onClick={() => onAddSection(idx)}
                        className="surface-card-hover w-full border-emerald-200 bg-emerald-50 p-3 text-left hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/30"
                      >
                        <div className="helper-copy uppercase tracking-widest text-emerald-700 dark:text-emerald-300">Insert</div>
                        <div className="card-title mt-1 text-sm text-emerald-800 dark:text-emerald-200">{label}</div>
                      </button>
                    )
                  })}
                </>
              )}
            </div>
          </section>
          </div>
        </div>
      </div>
    </div>
  )
}
