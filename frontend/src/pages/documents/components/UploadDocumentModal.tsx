import CompanySelector from '@/components/CompanySelector'
import {
  applyAudiencePreset,
  getAudienceDirtyHelperText,
  getAudienceVisibilityHelperText,
  listAudiencePresets,
} from '@/features/documents'
import { ACCEPTED_FILE_TYPES, useUploadDocumentFlow } from '@/pages/documents/hooks/useUploadDocumentFlow'

export function UploadDocumentModal({ onClose }: { onClose: () => void }) {
  const {
    fileInputRef,
    selectedFile,
    title,
    setTitle,
    description,
    setDescription,
    category,
    setCategory,
    releaseBranch,
    setReleaseBranch,
    tags,
    setTags,
    visibility,
    setVisibility,
    companyIds,
    setCompanyIds,
    error,
    setError,
    dragActive,
    setDragActive,
    audienceDirtyState,
    uploadMutation,
    handleFileSelect,
    handleDrop,
    handleSubmit,
    confirmClose,
  } = useUploadDocumentFlow({ onClose })
  const audiencePresets = listAudiencePresets()
  const audienceDirtyHelper = getAudienceDirtyHelperText(audienceDirtyState)
  const visibilityHelperText = getAudienceVisibilityHelperText(visibility)

  const handlePresetApply = (presetId: (typeof audiencePresets)[number]['id']) => {
    const nextAudience = applyAudiencePreset(
      {
        visibility,
        company_ids: companyIds,
      },
      presetId,
    )
    setVisibility(nextAudience.visibility)
    setCompanyIds(nextAudience.company_ids)
    setError('')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-display font-bold text-slate-900 mb-4">Upload Document</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div className="p-3 bg-rose-50 text-rose-700 rounded-xl text-sm">{error}</div>}

          <div
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              dragActive ? 'border-sky-500 bg-sky-50' : 'border-slate-300 hover:border-slate-400'
            }`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragActive(true)
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_FILE_TYPES}
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            />
            {selectedFile ? (
              <div>
                <span className="text-3xl">FILE</span>
                <p className="mt-2 font-medium text-slate-900">{selectedFile.name}</p>
                <p className="text-sm text-slate-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div>
                <span className="text-3xl">UP</span>
                <p className="mt-2 text-slate-600">Drag & drop a file here, or click to browse</p>
                <p className="text-sm text-slate-400 mt-1">PDF, DOC, DOCX (max 10MB)</p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input-field"
              placeholder="Document title (uses filename if empty)"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field"
              rows={2}
              placeholder="Optional description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input-field"
                placeholder="e.g., Reports"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="input-field"
                placeholder="tag1, tag2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Audience Presets</label>
            <div className="grid grid-cols-1 gap-2">
              {audiencePresets.map((preset) => {
                const isActive = visibility === preset.visibility
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
              value={visibility}
              onChange={(e) => setVisibility(e.target.value as typeof visibility)}
              className="select-field"
            >
              <option value="internal">Internal</option>
              <option value="public">Public</option>
              <option value="company">Company</option>
            </select>
            <p
              className="mt-1 text-xs text-slate-500"
            >
              {visibilityHelperText}
            </p>
            <p
              className={`mt-1 text-xs ${
                audienceDirtyHelper.isChanged ? 'text-amber-700' : 'text-slate-500'
              }`}
            >
              {audienceDirtyHelper.text}
            </p>
          </div>

          {visibility === 'company' && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Target Companies</label>
              <CompanySelector
                selectedIds={companyIds}
                onChange={setCompanyIds}
                placeholder="Select target companies..."
              />
              <p className="text-xs text-slate-500 mt-1">
                {getAudienceVisibilityHelperText('company')}
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Release Branch</label>
            <input
              type="text"
              value={releaseBranch}
              onChange={(e) => setReleaseBranch(e.target.value)}
              className="input-field"
              placeholder="e.g., R580"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={confirmClose} className="btn-ghost">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="btn-primary disabled:opacity-50"
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
