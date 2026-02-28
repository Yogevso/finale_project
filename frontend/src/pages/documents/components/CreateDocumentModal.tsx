import RichTextEditor from '@/components/RichTextEditor'
import { useCreateDocumentFlow } from '@/pages/documents/hooks/useCreateDocumentFlow'

export function CreateDocumentModal({ onClose }: { onClose: () => void }) {
  const {
    formData,
    setFormData,
    error,
    generateWord,
    setGenerateWord,
    createMutation,
    handleSubmit,
  } = useCreateDocumentFlow({ onClose })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h2 className="text-xl font-display font-bold text-slate-900">Create Document</h2>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-xl text-slate-500">
            x
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
          {error && (
            <div className="mx-4 mt-4 p-3 bg-rose-50 text-rose-700 rounded-xl text-sm">{error}</div>
          )}

          <div className="flex-1 flex overflow-hidden">
            <div className="w-80 p-4 border-r border-slate-200 overflow-y-auto space-y-4 surface-muted">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input-field"
                  placeholder="Enter document title"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="input-field"
                  rows={2}
                  placeholder="Brief description"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
                <input type="text" value="Draft" disabled className="input-field disabled:opacity-70" />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Visibility</label>
                <input
                  type="text"
                  value="Internal"
                  disabled
                  className="input-field disabled:opacity-70"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="input-field"
                  placeholder="e.g., Policy, Guide"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Release Branch</label>
                <input
                  type="text"
                  value={formData.release_branch || ''}
                  onChange={(e) => setFormData({ ...formData, release_branch: e.target.value })}
                  className="input-field"
                  placeholder="e.g., R580"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="input-field"
                  placeholder="Comma-separated"
                />
              </div>

              <div className="pt-2">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={generateWord}
                    onChange={(e) => setGenerateWord(e.target.checked)}
                    className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  Generate Word file (DOCX)
                </label>
                <p className="text-xs text-slate-400 mt-1">
                  Creates a Word attachment from the editor content.
                </p>
              </div>
            </div>

            <div className="flex-1 p-4 flex flex-col overflow-hidden min-h-0">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Content <span className="text-slate-400 font-normal">(start typing your document)</span>
              </label>
              <div className="flex-1 min-h-0">
                <RichTextEditor
                  content={formData.content || ''}
                  onChange={(html) => setFormData({ ...formData, content: html })}
                  editable={true}
                  scrollable
                  className="h-full"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 p-4 border-t border-slate-200 surface-muted">
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <span className="animate-spin">...</span>
                  Creating...
                </>
              ) : (
                'Create & Continue Editing'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

