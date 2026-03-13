import { Trash2, FileStack } from 'lucide-react'
import { useState } from 'react'
import {
  deleteDocumentTemplate,
  listDocumentTemplates,
  type DocumentTemplate,
} from '@/lib/documentTemplates'

type TemplateLibraryProps = {
  selectedTemplateId: string | null
  onSelectTemplate: (template: DocumentTemplate) => void
  onDeleteTemplate?: (templateId: string) => void
}

export default function TemplateLibrary({
  selectedTemplateId,
  onSelectTemplate,
  onDeleteTemplate,
}: TemplateLibraryProps) {
  const [templates, setTemplates] = useState<DocumentTemplate[]>(() => listDocumentTemplates())

  const handleDeleteTemplate = (templateId: string) => {
    deleteDocumentTemplate(templateId)
    setTemplates(listDocumentTemplates())
    onDeleteTemplate?.(templateId)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <FileStack className="h-4 w-4 text-sky-600" />
        Template Library
      </div>
      <p className="text-xs text-slate-500">
        Templates are kept separate from Documents. Custom templates are saved in this browser, and deleting a built-in template hides it only here.
      </p>
      <div className="grid gap-2">
        {templates.map((template) => {
          const isSelected = selectedTemplateId === template.id
          const isCustom = template.source === 'custom'
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => onSelectTemplate(template)}
              aria-label={`Use template ${template.name}`}
              className={`rounded-2xl border p-3 text-left transition-colors ${
                isSelected
                  ? 'border-sky-500 bg-sky-50 text-sky-900'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{template.name}</p>
                    {isCustom ? (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
                        Custom
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{template.description}</p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="rounded-full bg-white/80 px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                    {template.category}
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label={`Delete template ${template.name}`}
                    onClick={(event) => {
                      event.stopPropagation()
                      handleDeleteTemplate(template.id)
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        event.stopPropagation()
                        handleDeleteTemplate(template.id)
                      }
                    }}
                    className="rounded-full p-1 text-slate-400 transition-colors hover:bg-white hover:text-rose-600"
                    title={isCustom ? 'Delete template' : 'Hide template'}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </span>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
