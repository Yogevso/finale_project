import { FilePlus2, FileText, Loader2, UploadCloud, X } from 'lucide-react'
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
  const { containerRef } = useFocusTrap<HTMLDivElement>(confirmClose)
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
    <div className="modal-overlay flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 z-0 bg-transparent"
        onClick={isUploading ? undefined : confirmClose}
        disabled={isUploading}
        aria-label="Close upload document dialog"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Upload Document"
        tabIndex={-1}
        className="modal-content motion-enter-scale relative z-10 max-h-[90vh] w-full max-w-lg overflow-y-auto p-6 dark:bg-slate-900"
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="section-title text-xl">Upload Document</h2>
            <p className="body-copy mt-1">
              Upload a source file, set initial metadata, and choose who gets access.
            </p>
          </div>
          <button
            type="button"
            onClick={confirmClose}
            disabled={isUploading}
            className="btn-icon h-9 w-9 text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Close upload dialog"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error ? (
            <div role="alert" className="alert-danger body-copy">
              {error}
            </div>
          ) : null}

          <input
            ref={fileInputRef}
            id="upload-primary-file"
            type="file"
            accept={ACCEPTED_FILE_TYPES}
            className="hidden"
            data-testid="primary-upload-input"
            aria-label="Primary upload file"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
          />
          <button
            type="button"
            className={`surface-muted w-full border-2 border-dashed p-6 text-center transition-colors ${
              dragActive
                ? 'border-sky-500 bg-sky-50 dark:border-sky-400 dark:bg-sky-950/40'
                : 'border-slate-300 hover:border-slate-400 dark:border-slate-700 dark:hover:border-slate-600'
            }`}
            aria-label="Choose a document to upload"
            onDragOver={(e) => {
              e.preventDefault()
              setDragActive(true)
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                  <FileText className="h-7 w-7" aria-hidden="true" />
                </div>
                <div>
                  <p className="helper-copy font-medium uppercase tracking-[0.2em] text-sky-700 dark:text-sky-300">
                    Primary file
                  </p>
                  <p className="card-title mt-1">{selectedFile.name}</p>
                </div>
                <p className="helper-copy">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
                  <UploadCloud className="h-7 w-7" aria-hidden="true" />
                </div>
                <div>
                  <p className="card-title">Upload DOCX or PPTX</p>
                  <p className="body-copy mt-1">
                    Drag and drop a file here, or click to browse.
                  </p>
                </div>
                <p className="helper-copy">DOCX, PPTX (max 10MB)</p>
              </div>
            )}
          </button>

          {canManageAdvancedUploadOptions ? (
            <div className="surface-muted space-y-4 p-4">
              <div>
                <p className="section-title text-base">Manager upload options</p>
                <p className="helper-copy mt-1">
                  Set the initial status or attach supporting DOCX/PPTX files during upload.
                </p>
              </div>

              <div>
                <label
                  htmlFor="upload-status"
                  className="helper-copy mb-1 block font-medium uppercase tracking-wide"
                >
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
                  <label
                    htmlFor="upload-content-file"
                    className="helper-copy mb-1 block font-medium uppercase tracking-wide"
                  >
                    Additional Content File
                  </label>
                  <input
                    id="upload-content-file"
                    type="file"
                    accept={ACCEPTED_FILE_TYPES}
                    aria-label="Additional content file"
                    className="input-field file:mr-3 file:rounded-lg file:border-0 file:bg-sky-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700"
                    onChange={(e) => handleSupplementalFileSelect('content', e.target.files?.[0] ?? null)}
                  />
                  <p className="helper-copy mt-1">
                    {contentFile ? contentFile.name : 'Optional secondary attachment for the same document.'}
                  </p>
                </div>

                <div>
                  <label
                    htmlFor="upload-release-notes-file"
                    className="helper-copy mb-1 block font-medium uppercase tracking-wide"
                  >
                    Release Notes File
                  </label>
                  <input
                    id="upload-release-notes-file"
                    type="file"
                    accept={ACCEPTED_FILE_TYPES}
                    aria-label="Release notes file"
                    className="input-field file:mr-3 file:rounded-lg file:border-0 file:bg-sky-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-sky-700"
                    onChange={(e) =>
                      handleSupplementalFileSelect('releaseNotes', e.target.files?.[0] ?? null)
                    }
                  />
                  <p className="helper-copy mt-1">
                    {releaseNotesFile
                      ? releaseNotesFile.name
                      : 'Optional release-notes document uploaded alongside the primary file.'}
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          <div>
            <label htmlFor="upload-title" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
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
            <label htmlFor="upload-platform" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
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
            <p className="helper-copy mt-1">
              Select an existing platform or type a new platform name to create it during upload.
            </p>
          </div>

          <div>
            <label
              htmlFor="upload-description"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Description
            </label>
            <textarea
              id="upload-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field"
              rows={2}
              placeholder="Optional description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="upload-category"
                className="helper-copy mb-1 block font-medium uppercase tracking-wide"
              >
                Category
              </label>
              <input
                id="upload-category"
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input-field"
                placeholder="e.g., Reports"
              />
            </div>
            <div>
              <label htmlFor="upload-tags" className="helper-copy mb-1 block font-medium uppercase tracking-wide">
                Tags
              </label>
              <input
                id="upload-tags"
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="input-field"
                placeholder="tag1, tag2"
              />
            </div>
          </div>

          <div>
            <p className="helper-copy mb-1 block font-medium uppercase tracking-wide">Audience Presets</p>
            <div className="grid grid-cols-1 gap-2">
              {audiencePresets.map((preset) => {
                const isActive = visibility === preset.visibility
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handlePresetApply(preset.id)}
                    className={`rounded-2xl border px-3 py-3 text-left transition-colors ${
                      isActive
                        ? 'border-sky-500 bg-sky-50 text-sky-800 dark:border-sky-400 dark:bg-sky-950/40 dark:text-sky-100'
                        : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 dark:hover:border-slate-600'
                    }`}
                  >
                    <span className="card-title text-sm">{preset.label}</span>
                    <span className="helper-copy mt-1 block">{preset.description}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <label
              htmlFor="upload-visibility"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Visibility
            </label>
            <select
              id="upload-visibility"
              value={visibility}
              onChange={(e) => setVisibility(e.target.value as typeof visibility)}
              className="select-field"
            >
              <option value="internal">Internal</option>
              <option value="public">Public</option>
              <option value="company">Company</option>
            </select>
            <p className="helper-copy mt-1">{visibilityHelperText}</p>
            <p
              className={`helper-copy mt-1 ${
                audienceDirtyHelper.isChanged ? 'text-amber-700' : 'text-slate-500'
              }`}
            >
              {audienceDirtyHelper.text}
            </p>
          </div>

          {visibility === 'company' ? (
            <div>
              <p className="helper-copy mb-1 block font-medium uppercase tracking-wide">Target Companies</p>
              <CompanySelector
                selectedIds={companyIds}
                onChange={setCompanyIds}
                placeholder="Select target companies..."
              />
              <p className="helper-copy mt-1">{getAudienceVisibilityHelperText('company')}</p>
            </div>
          ) : null}

          <div>
            <label
              htmlFor="upload-release-branch"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Release Branch
            </label>
            <input
              id="upload-release-branch"
              type="text"
              value={releaseBranch}
              onChange={(e) => setReleaseBranch(e.target.value)}
              className="input-field"
              placeholder="e.g., R580"
            />
          </div>

          <div>
            <label
              htmlFor="upload-due-date"
              className="helper-copy mb-1 block font-medium uppercase tracking-wide"
            >
              Due Date
            </label>
            <input
              id="upload-due-date"
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
              className="btn-ghost table-action-btn disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="btn-primary table-action-btn inline-flex items-center gap-2 disabled:opacity-50"
            >
              {isUploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
          {isUploading ? (
            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-3">
              <div className="flex items-center justify-between text-sm font-medium text-sky-900">
                <span className="inline-flex items-center gap-2">
                  <FilePlus2 className="sync-status-pulse h-4 w-4" aria-hidden="true" />
                  Uploading {selectedFile?.name ?? 'file'}
                </span>
                <span>{progressValue}%</span>
              </div>
              <div
                className="progress-track mt-2 h-2 bg-sky-100 dark:bg-sky-950/50"
                role="progressbar"
                aria-label="Upload progress"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progressValue}
              >
                <div
                  className="progress-fill"
                  style={{ width: `${progressValue}%` }}
                />
              </div>
              <p className="helper-copy mt-2 text-right text-sky-800 dark:text-sky-200">
                Uploading... Please wait to close this window.
              </p>
            </div>
          ) : null}
        </form>
      </div>
    </div>
  )
}
