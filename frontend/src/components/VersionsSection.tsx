import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { GitCompareArrows } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import { queryKeys } from '@/lib/queryKeys'
import { useDocumentVersionsQuery } from '@/hooks/useDocumentQueries'
import type { Version, VersionBumpType, VersionCreate } from '@/types'

interface VersionsSectionProps {
  documentId: number
  isEditor: boolean
}

const bumpMeta: Record<VersionBumpType, { label: string; style: string; hint: string }> = {
  major: {
    label: 'Major',
    style: 'bg-rose-100 text-rose-700',
    hint: 'Breaking or policy-level changes',
  },
  minor: {
    label: 'Minor',
    style: 'bg-sky-100 text-sky-700',
    hint: 'New section or meaningful update',
  },
  patch: {
    label: 'Patch',
    style: 'bg-slate-100 text-slate-700',
    hint: 'Corrections and small improvements',
  },
}

const roleLabel = (role?: string | null) =>
  (role || 'unknown').replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())

export default function VersionsSection({ documentId, isEditor }: VersionsSectionProps) {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [newVersion, setNewVersion] = useState<VersionCreate>({
    content: '',
    changes_summary: '',
    bump_type: 'patch',
  })
  const [expandedVersion, setExpandedVersion] = useState<number | null>(null)
  const [publishError, setPublishError] = useState<string | null>(null)

  const { data: versionsData, isLoading } = useDocumentVersionsQuery(documentId)

  const createMutation = useMutation({
    mutationFn: (data: VersionCreate) => api.createVersion(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
      setIsCreating(false)
      setNewVersion({ content: '', changes_summary: '', bump_type: 'patch' })
    },
  })

  const publishMutation = useMutation({
    mutationFn: (versionId: number) => api.publishVersion(documentId, versionId),
    onSuccess: () => {
      setPublishError(null)
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to publish version'
      setPublishError(message)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (versionId: number) => api.deleteVersion(documentId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(documentId) })
    },
  })

  if (isLoading) {
    return <div className="animate-pulse bg-slate-100 h-32 rounded-xl"></div>
  }

  const versions = versionsData?.items || []

  return (
    <div className="surface-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Versions ({versions.length})</h2>
        <div className="flex flex-wrap items-center gap-2">
          {versions.length > 1 && (
            <Link
              to={`/documents/${documentId}/compare`}
              className="btn-secondary inline-flex items-center gap-2 text-sm"
            >
              <GitCompareArrows className="h-4 w-4" />
              Compare versions
            </Link>
          )}
          {isEditor && !isCreating && (
            <button onClick={() => setIsCreating(true)} className="btn-primary text-sm">
              + New Version
            </button>
          )}
        </div>
      </div>

      {isCreating && (
        <div className="mb-4 p-4 bg-sky-50 rounded-xl border border-sky-200">
          <h3 className="font-medium text-sky-900 mb-3">Create New Version</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-sky-800 mb-1">Version Type</label>
              <select
                value={newVersion.bump_type || 'patch'}
                onChange={(e) =>
                  setNewVersion({ ...newVersion, bump_type: e.target.value as VersionBumpType })
                }
                className="select-field bg-white"
              >
                <option value="patch">Patch (x.y.z+1)</option>
                <option value="minor">Minor (x.y+1.0)</option>
                <option value="major">Major (x+1.0.0)</option>
              </select>
              <p className="text-xs text-sky-700 mt-1">
                {bumpMeta[(newVersion.bump_type || 'patch') as VersionBumpType].hint}
              </p>
            </div>
            <div>
              <label className="block text-sm text-sky-800 mb-1">Content</label>
              <textarea
                value={newVersion.content || ''}
                onChange={(e) => setNewVersion({ ...newVersion, content: e.target.value })}
                className="input-field"
                rows={4}
                placeholder="Version content..."
              />
            </div>
            <div>
              <label className="block text-sm text-sky-800 mb-1">Changes Summary</label>
              <input
                type="text"
                value={newVersion.changes_summary || ''}
                onChange={(e) => setNewVersion({ ...newVersion, changes_summary: e.target.value })}
                className="input-field"
                placeholder="What changed in this version?"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => createMutation.mutate(newVersion)}
                disabled={createMutation.isPending}
                className="btn-primary text-sm"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Version'}
              </button>
              <button onClick={() => setIsCreating(false)} className="btn-ghost text-sm">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {publishError && (
        <div className="mb-4 p-3 rounded-xl border border-amber-200 bg-amber-50 text-amber-800 text-sm">
          {publishError}
        </div>
      )}

      {versions.length === 0 ? (
        <p className="text-slate-500 text-sm">No versions yet</p>
      ) : (
        <div className="space-y-3">
          {versions.map((version: Version) => (
            <VersionCard
              key={version.id}
              version={version}
              isExpanded={expandedVersion === version.id}
              onToggle={() => setExpandedVersion(expandedVersion === version.id ? null : version.id)}
              onPublish={() => publishMutation.mutate(version.id)}
              onDelete={() => {
                if (confirm('Delete this version?')) {
                  deleteMutation.mutate(version.id)
                }
              }}
              isEditor={isEditor}
              isPublishing={publishMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function VersionCard({
  version,
  isExpanded,
  onToggle,
  onPublish,
  onDelete,
  isEditor,
  isPublishing,
}: {
  version: Version
  isExpanded: boolean
  onToggle: () => void
  onPublish: () => void
  onDelete: () => void
  isEditor: boolean
  isPublishing: boolean
}) {
  const bumpType = version.bump_type || 'patch'
  const bump = bumpMeta[bumpType]
  const visibleVersion = version.semantic_version || `${version.version_number}.0.0`
  const review = version.latest_review
  const reviewStatus = review?.status
  const reviewBadgeStyle =
    reviewStatus === 'approved'
      ? 'bg-emerald-100 text-emerald-700'
      : reviewStatus === 'rejected'
        ? 'bg-rose-100 text-rose-700'
        : reviewStatus === 'pending'
          ? 'bg-amber-100 text-amber-700'
          : 'bg-slate-100 text-slate-700'

  return (
    <div
      className={`border rounded-xl ${version.is_published ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200'}`}
    >
      <div
        className="p-3 flex items-start justify-between cursor-pointer hover:bg-slate-50 rounded-t-xl"
        onClick={onToggle}
      >
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-900">v{visibleVersion}</span>
            <span className="text-xs text-slate-500 font-mono">#{version.version_number}</span>
            <span className={`px-2 py-0.5 text-xs rounded-full ${bump.style}`}>{bump.label}</span>
            {version.is_published ? (
              <span className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded-full">
                Published
              </span>
            ) : (
              <span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded-full">
                Draft
              </span>
            )}
            {reviewStatus && (
              <span className={`px-2 py-0.5 text-xs rounded-full ${reviewBadgeStyle}`}>
                Review: {reviewStatus}
              </span>
            )}
          </div>
          {version.changes_summary && (
            <p className="text-sm text-slate-600 line-clamp-1 max-w-[48rem]">{version.changes_summary}</p>
          )}
          <p className="text-xs text-slate-500">
            Edited by {version.created_by_user?.full_name || `User #${version.created_by}`}{' '}
            ({roleLabel(version.created_by_user?.role)})
          </p>
        </div>
        <div className="flex items-center gap-2 pl-3">
          <span className="text-xs text-slate-400">{new Date(version.created_at).toLocaleDateString()}</span>
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-slate-100 space-y-3">
          <div className="pt-3">
            <label className="text-xs text-slate-500">Content</label>
            <div className="mt-1 p-2 bg-white rounded-lg border text-sm whitespace-pre-wrap">
              {version.content || 'No content'}
            </div>
          </div>

          {version.changes_summary && (
            <div>
              <label className="text-xs text-slate-500">Change Summary</label>
              <p className="mt-1 text-sm text-slate-700">{version.changes_summary}</p>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-2 text-xs text-slate-600">
            <p>
              <span className="text-slate-500">Editor:</span>{' '}
              {version.created_by_user?.full_name || `User #${version.created_by}`}{' '}
              ({roleLabel(version.created_by_user?.role)})
            </p>
            <p>
              <span className="text-slate-500">Created:</span>{' '}
              {formatDate(version.created_at)}
            </p>
            {review?.submitter && (
              <p>
                <span className="text-slate-500">Submitted:</span> {review.submitter.full_name}{' '}
                ({roleLabel(review.submitter.role)})
              </p>
            )}
            {review?.reviewer && (
              <p>
                <span className="text-slate-500">Reviewed:</span> {review.reviewer.full_name}{' '}
                ({roleLabel(review.reviewer.role)})
              </p>
            )}
            {version.published_at && (
              <p>
                <span className="text-slate-500">Published:</span>{' '}
                {formatDate(version.published_at)}
              </p>
            )}
            {version.published_by_user && (
              <p>
                <span className="text-slate-500">Publisher:</span> {version.published_by_user.full_name}{' '}
                ({roleLabel(version.published_by_user.role)})
              </p>
            )}
          </div>

          {isEditor && !version.is_published && (
            <div className="pt-1 flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onPublish()
                }}
                disabled={isPublishing}
                className="px-2 py-1 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
                title="Requires approved review for this version"
              >
                {isPublishing ? 'Publishing...' : 'Publish'}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete()
                }}
                className="px-2 py-1 text-xs text-rose-600 hover:bg-rose-50 rounded"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
