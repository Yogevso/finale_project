import { FileStack } from 'lucide-react'
import { documentTemplates, type DocumentTemplate } from '@/lib/documentTemplates'

type TemplateLibraryProps = {
  selectedTemplateId: string | null
  onSelectTemplate: (template: DocumentTemplate) => void
}

export default function TemplateLibrary({
  selectedTemplateId,
  onSelectTemplate,
}: TemplateLibraryProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <FileStack className="h-4 w-4 text-sky-600" />
        Template Library
      </div>
      <div className="grid gap-2">
        {documentTemplates.map((template) => {
          const isSelected = selectedTemplateId === template.id
          return (
            <button
              key={template.id}
              type="button"
              onClick={() => onSelectTemplate(template)}
              className={`rounded-2xl border p-3 text-left transition-colors ${
                isSelected
                  ? 'border-sky-500 bg-sky-50 text-sky-900'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{template.name}</p>
                  <p className="mt-1 text-xs text-slate-500">{template.description}</p>
                </div>
                <span className="rounded-full bg-white/80 px-2 py-1 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                  {template.category}
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
