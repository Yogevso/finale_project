import { useState } from 'react'
import { X } from 'lucide-react'
import TemplateLibrary from '@/components/TemplateLibrary'
import CompanySelector from '@/components/CompanySelector'
import RichTextEditor from '@/components/RichTextEditor'
import {
  applyAudiencePreset,
  getAudienceDirtyHelperText,
  getAudienceVisibilityHelperText,
  listAudiencePresets,
} from '@/features/documents'
import type { DocumentTemplate } from '@/lib/documentTemplates'
import { useCreateDocumentFlow } from '@/pages/documents/hooks/useCreateDocumentFlow'
import { useFocusTrap } from '@/hooks/useAccessibility'

export function CreateDocumentModal({ onClose }: { onClose: () => void }) {
  const {
    formData,
    setFormData,
    error,
    setError,
    generateWord,
    setGenerateWord,
    selectedTemplateId,
    setSelectedTemplateId,
    saveAsTemplate,
    setSaveAsTemplate,
    templateName,
    setTemplateName,
    templateDescription,
    setTemplateDescription,
    copySourceSearch,
    setCopySourceSearch,
    selectedSourceDocument,
    copySourceResultsQuery,
    copySourceMutation,
    handleCopyFromDocument,
    clearCopiedSource,
    platformSuggestions,
    createMutation,
    duplicateCheckQuery,
    audienceDirtyState,
    handleSubmit,
    confirmClose,
  } = useCreateDocumentFlow({ onClose })
  const { containerRef, handleKeyDown: trapKeyDown } = useFocusTrap(onClose)
  const audiencePresets = listAudiencePresets()
  const audienceDirtyHelper = getAudienceDirtyHelperText(audienceDirtyState)
  const visibilityHelperText = getAudienceVisibilityHelperText(formData.visibility || 'internal')
  const duplicateMatches = duplicateCheckQuery.data?.matches ?? []
  const isTemplateMode = saveAsTemplate
  const hasDuplicates = !isTemplateMode && duplicateMatches.length > 0
  const [duplicateAcknowledged, setDuplicateAcknowledged] = useState(false)

  const handleTemplateSelect = (template: DocumentTemplate) => {
    setSelectedTemplateId(template.id)
    setFormData((previous) => ({
      ...previous,
      title: previous.title || template.name,
      category: template.category,
      tags: template.tags.join(', '),
      content: template.content,
      description: template.description,
    }))
    setError('')
  }

  const handlePresetApply = (presetId: (typeof audiencePresets)[number]['id']) => {
    setFormData((previous) => {
      const nextAudience = applyAudiencePreset(
        {
          visibility: previous.visibility || 'internal',
          company_ids: previous.company_ids || [],
        },
        presetId,
      )
      return {
        ...previous,
        visibility: nextAudience.visibility,
        company_ids: nextAudience.company_ids,
      }
    })
    setError('')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={confirmClose}>
      <div ref={containerRef} role="dialog" aria-modal="true" aria-label="Create Document" className="bg-white rounded-2xl shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()} onKeyDown={trapKeyDown}>
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h2 className="text-xl font-display font-bold text-slate-900">Create Document</h2>
          <button onClick={confirmClose} className="p-2 hover:bg-slate-100 rounded-xl text-slate-500" aria-label="Close create document dialog">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
          {error && (
            <div className="mx-4 mt-4 p-3 bg-rose-50 text-rose-700 rounded-xl text-sm">{error}</div>
          )}

          <div className="flex-1 flex overflow-hidden">
            <div className="w-80 p-4 border-r border-slate-200 overflow-y-auto space-y-4 surface-muted">
              {!isTemplateMode ? (
                <div className="rounded-2xl border border-slate-200 bg-white p-3 space-y-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">Start from existing document</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Load an existing document as an editable copy. The original document stays unchanged.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Search source document
                    </label>
                    <input
                      type="text"
                      value={copySourceSearch}
                      onChange={(event) => setCopySourceSearch(event.target.value)}
                      className="input-field"
                      placeholder="Search by title or document number"
                    />
                  </div>

                  {selectedSourceDocument ? (
                    <div className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                      <div className="font-medium">Copying from {selectedSourceDocument.title}</div>
                      <div className="text-xs text-sky-700">{selectedSourceDocument.document_number}</div>
                      <button
                        type="button"
                        onClick={clearCopiedSource}
                        className="mt-2 text-xs font-semibold uppercase tracking-wide text-sky-700 hover:text-sky-800"
                      >
                        Clear source
                      </button>
                    </div>
                  ) : null}

                  {copySourceSearch.trim().length >= 2 ? (
                    <div className="space-y-2">
                      {copySourceResultsQuery.isLoading ? (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                          Searching documents...
                        </div>
                      ) : null}

                      {(copySourceResultsQuery.data?.items ?? []).map((document) => (
                        <button
                          key={document.id}
                          type="button"
                          onClick={() =>
                            handleCopyFromDocument({
                              id: document.id,
                              title: document.title,
                              document_number: document.document_number,
                            })
                          }
                          disabled={copySourceMutation.isPending}
                          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-left transition-colors hover:border-slate-300 hover:bg-white disabled:opacity-60"
                        >
                          <div className="font-medium text-slate-900">{document.title}</div>
                          <div className="mt-1 text-xs text-slate-500">
                            {document.document_number}
                            {document.platform ? ` · ${document.platform}` : ''}
                          </div>
                        </button>
                      ))}

                      {copySourceResultsQuery.data && copySourceResultsQuery.data.items.length === 0 ? (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                          No matching documents found.
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              <TemplateLibrary
                selectedTemplateId={selectedTemplateId}
                onSelectTemplate={handleTemplateSelect}
                onDeleteTemplate={(templateId) => {
                  if (selectedTemplateId === templateId) {
                    setSelectedTemplateId(null)
                  }
                }}
              />

              <div className="rounded-2xl border border-slate-200 bg-white p-3">
                <label className="flex items-start gap-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={saveAsTemplate}
                    onChange={(event) => setSaveAsTemplate(event.target.checked)}
                    className="mt-0.5 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  <span>
                    <span className="block font-medium text-slate-900">
                      Create as template instead of document
                    </span>
                    <span className="mt-1 block text-xs text-slate-500">
                      Save this content into your personal Template Library without creating a document in the Documents list. Saved in this browser only.
                    </span>
                  </span>
                </label>

                {saveAsTemplate ? (
                  <div className="mt-3 space-y-3 border-t border-slate-100 pt-3">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Template name override
                      </label>
                      <input
                        type="text"
                        value={templateName}
                        onChange={(event) => setTemplateName(event.target.value)}
                        className="input-field"
                        placeholder={formData.title || 'Use the title as the template name'}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Template description override
                      </label>
                      <textarea
                        value={templateDescription}
                        onChange={(event) => setTemplateDescription(event.target.value)}
                        className="input-field"
                        rows={2}
                        placeholder={formData.description || 'Explain when to reuse this template'}
                      />
                    </div>
                  </div>
                ) : null}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  {isTemplateMode ? 'Template title *' : 'Title *'}
                </label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="input-field"
                  placeholder={isTemplateMode ? 'Enter template title' : 'Enter document title'}
                  required
                />
                {!isTemplateMode && duplicateCheckQuery.data?.has_matches ? (
                  <div className="mt-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    <p className="font-medium">Possible duplicate documents found</p>
                    <div className="mt-2 space-y-1">
                      {duplicateMatches.map((match) => (
                        <a
                          key={match.document_id}
                          href={`/documents/${match.document_id}`}
                          className="block rounded-lg px-2 py-1 transition-colors hover:bg-white/70"
                        >
                          <span className="font-medium">{match.title}</span>
                          <span className="ml-2 text-xs text-amber-800">
                            {match.document_number} · {Math.round(match.similarity * 100)}% match
                          </span>
                        </a>
                      ))}
                    </div>
                    <label className="mt-2 flex items-center gap-2 text-xs text-amber-800">
                      <input
                        type="checkbox"
                        checked={duplicateAcknowledged}
                        onChange={(e) => setDuplicateAcknowledged(e.target.checked)}
                        className="rounded border-amber-400 text-amber-600 focus:ring-amber-500"
                      />
                      I've reviewed these — create anyway
                    </label>
                  </div>
                ) : null}
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

              {!isTemplateMode ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
                    <input type="text" value="Draft" disabled className="input-field disabled:opacity-70" />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Audience Presets</label>
                    <div className="grid grid-cols-1 gap-2">
                      {audiencePresets.map((preset) => {
                        const isActive = formData.visibility === preset.visibility
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            onClick={() => handlePresetApply(preset.id)}
                            className={`text-left px-3 py-2 rounded-xl border transition-colors ${
                              isActive
                                ? 'border-sky-500 bg-sky-50 text-sky-800'
                                : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'
                            }`}
                          >
                            <span className="block text-sm font-medium">{preset.label}</span>
                            <span className="block text-xs text-slate-500">{preset.description}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Visibility</label>
                    <select
                      value={formData.visibility}
                      onChange={(e) =>
                        setFormData({ ...formData, visibility: e.target.value as typeof formData.visibility })
                      }
                      className="select-field"
                    >
                      <option value="internal">Internal</option>
                      <option value="public">Public</option>
                      <option value="company">Company</option>
                    </select>
                    <p className="mt-1 text-xs text-slate-500">{visibilityHelperText}</p>
                    <p
                      className={`mt-1 text-xs ${
                        audienceDirtyHelper.isChanged ? 'text-amber-700' : 'text-slate-500'
                      }`}
                    >
                      {audienceDirtyHelper.text}
                    </p>
                  </div>

                  {formData.visibility === 'company' ? (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Target Companies
                      </label>
                      <CompanySelector
                        selectedIds={formData.company_ids || []}
                        onChange={(ids) => setFormData({ ...formData, company_ids: ids })}
                        placeholder="Select target companies..."
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        {getAudienceVisibilityHelperText('company')}
                      </p>
                    </div>
                  ) : null}
                </>
              ) : null}

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

              {!isTemplateMode ? (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Platform *</label>
                  <input
                    type="text"
                    list="document-platform-options"
                    value={formData.platform || ''}
                    onChange={(e) => setFormData({ ...formData, platform: e.target.value, platform_id: undefined })}
                    className="input-field"
                    placeholder="Choose an existing platform or type a new one"
                    required
                  />
                  <datalist id="document-platform-options">
                    {platformSuggestions.map((platformName) => (
                      <option key={platformName} value={platformName} />
                    ))}
                  </datalist>
                  <p className="mt-1 text-xs text-slate-500">
                    Select a current platform or type a new platform name to create it with this document.
                  </p>
                </div>
              ) : null}

              {!isTemplateMode ? (
                <>
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
                    <label className="block text-sm font-medium text-slate-700 mb-1">Due Date</label>
                    <input
                      type="date"
                      value={formData.due_date || ''}
                      onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                      className="input-field"
                    />
                  </div>
                </>
              ) : null}

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

              {!isTemplateMode ? (
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
              ) : null}
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
            <button type="button" onClick={confirmClose} className="btn-ghost">
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || (hasDuplicates && !duplicateAcknowledged)}
              className="btn-primary flex items-center gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <span className="animate-spin">...</span>
                  Creating...
                </>
              ) : (
                isTemplateMode ? 'Save Template' : 'Create & Continue Editing'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
