import { X } from 'lucide-react'
import type { TocSection } from '@/pages/document-detail/helpers/previewHelpers'

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
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-sky-600 to-sky-700">
          <div>
            <h2 className="text-lg font-display font-semibold text-white">Edit Content Options</h2>
            <p className="text-xs text-sky-100 mt-1">
              Choose whether to edit an existing section or insert a new one.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-6 p-6 overflow-auto">
          <section className="rounded-2xl border border-sky-200 bg-sky-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="font-display font-semibold text-slate-900">Edit Entire Document</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Use this when you need to edit tables, mixed layouts, or content that spans multiple sections.
                </p>
              </div>
              <button
                type="button"
                onClick={onEditFullDocument}
                className="btn-primary"
              >
                Open Full Document Editor
              </button>
            </div>
          </section>

          <div className="grid md:grid-cols-2 gap-6">
          <section className="space-y-3">
            <h3 className="font-display font-semibold text-slate-900">Edit Existing Section</h3>
            <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
              {sections.map((section, idx) => (
                <button
                  key={`${section.id}-edit-${idx}`}
                  type="button"
                  onClick={() => onEditSection(section)}
                  className="w-full text-left p-3 rounded-xl border border-slate-200 hover:border-sky-300 hover:bg-sky-50 transition-colors"
                >
                  <div className="text-xs uppercase tracking-widest text-slate-400">
                    Section {idx + 1}
                  </div>
                  <div className="text-sm font-medium text-slate-900 mt-1">{section.text}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-3">
            <h3 className="font-display font-semibold text-slate-900">Add New Section</h3>
            <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-1">
              {sections.length === 0 && (
                <button
                  type="button"
                  onClick={() => onAddSection(-1)}
                  className="w-full text-left p-3 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                >
                  <div className="text-sm font-medium text-emerald-800">Add first section</div>
                </button>
              )}

              {sections.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => onAddSection(-1)}
                    className="w-full text-left p-3 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                  >
                    <div className="text-xs uppercase tracking-widest text-emerald-700">Insert</div>
                    <div className="text-sm font-medium text-emerald-800 mt-1">
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
                        className="w-full text-left p-3 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 transition-colors"
                      >
                        <div className="text-xs uppercase tracking-widest text-emerald-700">Insert</div>
                        <div className="text-sm font-medium text-emerald-800 mt-1">{label}</div>
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
