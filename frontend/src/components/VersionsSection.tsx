import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Version, VersionCreate } from '@/types'

interface VersionsSectionProps {
  documentId: number
  isEditor: boolean
}

export default function VersionsSection({ documentId, isEditor }: VersionsSectionProps) {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [newVersion, setNewVersion] = useState<VersionCreate>({ content: '', changes_summary: '' })
  const [expandedVersion, setExpandedVersion] = useState<number | null>(null)

  const { data: versionsData, isLoading } = useQuery({
    queryKey: ['versions', documentId],
    queryFn: () => api.getVersions(documentId),
  })

  const createMutation = useMutation({
    mutationFn: (data: VersionCreate) => api.createVersion(documentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions', documentId] })
      setIsCreating(false)
      setNewVersion({ content: '', changes_summary: '' })
    },
  })

  const publishMutation = useMutation({
    mutationFn: (versionId: number) => api.publishVersion(documentId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions', documentId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (versionId: number) => api.deleteVersion(documentId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions', documentId] })
    },
  })

  if (isLoading) {
    return <div className="animate-pulse bg-slate-100 h-32 rounded-xl"></div>
  }

  const versions = versionsData?.items || []

  return (
    <div className="surface-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Versions ({versions.length})
        </h2>
        {isEditor && !isCreating && (
          <button
            onClick={() => setIsCreating(true)}
            className="btn-primary text-sm"
          >
            + New Version
          </button>
        )}
      </div>

      {/* Create New Version Form */}
      {isCreating && (
        <div className="mb-4 p-4 bg-sky-50 rounded-xl border border-sky-200">
          <h3 className="font-medium text-sky-900 mb-3">Create New Version</h3>
          <div className="space-y-3">
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
              <button
                onClick={() => setIsCreating(false)}
                className="btn-ghost text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Versions List */}
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
  return (
    <div className={`border rounded-xl ${version.is_published ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200'}`}>
      <div
        className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate-50 rounded-t-xl"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <span className="font-medium">v{version.version_number}</span>
          {version.is_published ? (
            <span className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded-full">
              Published
            </span>
          ) : (
            <span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded-full">
              Draft
            </span>
          )}
          {version.changes_summary && (
            <span className="text-sm text-slate-500 truncate max-w-xs">
              {version.changes_summary}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            {new Date(version.created_at).toLocaleDateString()}
          </span>
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
        <div className="px-3 pb-3 border-t border-slate-100">
          <div className="mt-3">
            <label className="text-xs text-slate-500">Content</label>
            <div className="mt-1 p-2 bg-white rounded-lg border text-sm whitespace-pre-wrap">
              {version.content || 'No content'}
            </div>
          </div>

          {version.published_at && (
            <p className="mt-2 text-xs text-slate-500">
              Published: {new Date(version.published_at).toLocaleString()}
            </p>
          )}

          {isEditor && !version.is_published && (
            <div className="mt-3 flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onPublish()
                }}
                disabled={isPublishing}
                className="px-2 py-1 text-xs bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
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
