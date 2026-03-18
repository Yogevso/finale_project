import { FilePlus2, FileText, Loader2, UploadCloud } from 'lucide-react'
import CompanySelector from '@/components/CompanySelector'
import {
  applyAudiencePreset,
  getAudienceDirtyHelperText,
  getAudienceVisibilityHelperText,
  listAudiencePresets,
} from '@/features/documents'
import {
  ACCEPTED_FILE_TYPES,
  MANAGER_UPLOAD_STATUS_OPTIONS,
  useUploadDocumentFlow,
} from '@/pages/documents/hooks/useUploadDocumentFlow'
import { useFocusTrap } from '@/hooks/useAccessibility'

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
    platform,
    setPlatform,
    platformSuggestions,
    releaseBranch,
    setReleaseBranch,
    tags,
    setTags,
    dueDate,
    setDueDate,
    uploadStatus,
    setUploadStatus,
    visibility,
    setVisibility,
    companyIds,
    setCompanyIds,
    canManageAdvancedUploadOptions,
    contentFile,
    releaseNotesFile,
    error,
    setError,
    dragActive,
    setDragActive,
    uploadProgressPercent,
    audienceDirtyState,
    uploadMutation,
    handleFileSelect,
    handleSupplementalFileSelect,
    handleDrop,
    handleSubmit,
    confirmClose,
  } = useUploadDocumentFlow({ onClose })
  const { containerRef, handleKeyDown } = useFocusTrap(onClose)
  const audiencePresets = listAudiencePresets()
  const audienceDirtyHelper = getAudienceDirtyHelperText(audienceDirtyState)
  const visibilityHelperText = getAudienceVisibilityHelperText(visibility)
  const isUploading = uploadMutation.isPending
  const progressValue = uploadProgressPercent ?? 0

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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div ref={containerRef} role="dialog" aria-modal="true" aria-label="Upload Document" className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} onKeyDown={handleKeyDown}>
        <h2 className="text-xl font-display font-bold text-slate-900 mb-4">Upload Document</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <div role="alert" className="p-3 bg-rose-50 text-rose-700 rounded-xl text-sm">{error}</div>}

          <div
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-colors ${
              dragActive ? 'border-sky-500 bg-sky-50' : 'border-slate-300 hover:border-slate-400'
            }`}
            role="button"
            tabIndex={0}
            aria-label="Choose a document to upload"
            onDragOver={(e) => {
              e.preventDefault()
              setDragActive(true)
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                fileInputRef.current?.click()
              }
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_FILE_TYPES}
              className="hidden"
              data-testid="primary-upload-input"
              aria-label="Primary upload file"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            />
            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                  <FileText className="h-7 w-7" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">
                    Primary file
                  </p>
                  <p className="mt-1 font-medium text-slate-900">{selectedFile.name}</p>
                </div>
                <p className="text-sm text-slate-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                  <UploadCloud className="h-7 w-7" aria-hidden="true" />
                </div>
                <div>
                  <p className="font-semibold text-slate-900">Upload DOCX or PPTX</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Drag and drop a file here, or click to browse.
                  </p>
                </div>
                <p className="text-sm text-slate-400">DOCX, PPTX (max 10MB)</p>
              </div>
            )}
          </div>

          {canManageAdvancedUploadOptions ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 space-y-4">
              <div>
                <p className="text-sm font-semibold text-slate-900">Manager upload options</p>
                <p className="mt-1 text-xs text-slate-500">
                  Set the initial status or attach supporting DOCX/PPTX files during upload.
                </p>
              </div>

              <div>
                <label htmlFor="upload-status" className="block text-sm font-medium text-slate-700 mb-1">
                  Initial Status
                </label>
                <select
                  id="upload-status"
                  value={uploadStatus}
                  onChange={(e) => setUploadStatus(e.target.value as typeof uploadStatus)}
                  className="select-field"
                >
                  {MANAGER_UPLOAD_STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Additional Content File
                  </label>
                  <input
                    type="file"
                    accept={ACCEPTED_FILE_TYPES}
                    aria-label="Additional content file"
                    className="input-field file:mr-3 file:rounded-lg file:border-0 file:bg-sky-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700"
                    onChange={(e) => handleSupplementalFileSelect('content', e.target.files?.[0] ?? null)}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    {contentFile ? contentFile.name : 'Optional secondary attachment for the same document.'}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Release Notes File
                  </label>
                  <input
                    type="file"
                    accept={ACCEPTED_FILE_TYPES}
                    aria-label="Release notes file"
                    className="input-field file:mr-3 file:rounded-lg file:border-0 file:bg-sky-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700"
                    onChange={(e) =>
                      handleSupplementalFileSelect('releaseNotes', e.target.files?.[0] ?? null)
                    }
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    {releaseNotesFile
                      ? releaseNotesFile.name
                      : 'Optional release-notes document uploaded alongside the primary file.'}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          <div>
            <label htmlFor="upload-title" className="block text-sm font-medium text-slate-700 mb-1">
              Title
            </label>
            <input
              id="upload-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="input-field"
              placeholder="Document title (uses filename if empty)"
            />
          </div>

          <div>
            <label htmlFor="upload-platform" className="block text-sm font-medium text-slate-700 mb-1">
              Platform *
            </label>
            <input
              id="upload-platform"
              type="text"
              list="upload-platform-options"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="input-field"
              placeholder="Choose an existing platform or type a new one"
              required
            />
            <datalist id="upload-platform-options">
              {platformSuggestions.map((platformName) => (
                <option key={platformName} value={platformName} />
              ))}
            </datalist>
            <p className="mt-1 text-xs text-slate-500">
              Select an existing platform or type a new platform name to create it during upload.
            </p>
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

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Due Date</label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="input-field"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={confirmClose}
              disabled={isUploading}
              className="btn-ghost disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="btn-primary disabled:opacity-50 inline-flex items-center gap-2"
            >
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
          {isUploading && (
            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-3">
              <div className="flex items-center justify-between text-sm font-medium text-sky-900">
                <span className="inline-flex items-center gap-2">
                  <FilePlus2 className="h-4 w-4" aria-hidden="true" />
                  Uploading {selectedFile?.name ?? 'file'}
                </span>
                <span>{progressValue}%</span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-sky-100"
                role="progressbar"
                aria-label="Upload progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progressValue}
              >
                <div
                  className="h-full rounded-full bg-sky-600 transition-[width] duration-200 ease-out"
                  style={{ width: `${progressValue}%` }}
                />
              </div>
              <p className="mt-2 text-right text-xs text-sky-800">
                Uploading... Please wait to close this window.
              </p>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
