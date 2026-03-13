import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowLeftRight, GitCompareArrows } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import PageHeader from '@/components/PageHeader'
import VersionDiffView from '@/components/VersionDiffView'
import NotFoundState from '@/components/NotFoundState'
import { useDocumentDetailQuery, useDocumentVersionsQuery } from '@/hooks/useDocumentQueries'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/dateUtils'
import type { Version } from '@/types'

function sortVersions(versions: Version[]): Version[] {
  return [...versions].sort((left, right) => {
    if (right.version_number !== left.version_number) {
      return right.version_number - left.version_number
    }
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
  })
}

function getVersionLabel(version: Version | null | undefined): string {
  if (!version) {
    return 'Select a version'
  }

  const visibleVersion = version.semantic_version || `${version.version_number}.0.0`
  const stateLabel = version.is_published ? 'Published' : 'Draft'
  return `v${visibleVersion} | ${stateLabel} | ${formatDate(version.created_at)}`
}

export default function VersionComparePage() {
  const { id } = useParams<{ id: string }>()
  const documentId = Number(id)
  const [leftVersionId, setLeftVersionId] = useState<number | null>(null)
  const [rightVersionId, setRightVersionId] = useState<number | null>(null)

  const {
    data: document,
    isLoading: isDocumentLoading,
    error: documentError,
  } = useDocumentDetailQuery(id)
  const {
    data: versionsData,
    isLoading: areVersionsLoading,
  } = useDocumentVersionsQuery(id)

  const versions = useMemo(
    () => sortVersions(versionsData?.items || []),
    [versionsData?.items],
  )

  useEffect(() => {
    if (versions.length === 0) {
      return
    }

    setRightVersionId((current) =>
      current && versions.some((version) => version.id === current) ? current : versions[0].id,
    )
    setLeftVersionId((current) => {
      if (current && versions.some((version) => version.id === current)) {
        return current
      }
      return versions[1]?.id || versions[0].id
    })
  }, [versions])

  const selectedLeftVersion = versions.find((version) => version.id === leftVersionId) || null
  const selectedRightVersion = versions.find((version) => version.id === rightVersionId) || null

  const { data: leftVersionDetail, isLoading: isLeftLoading } = useQuery({
    queryKey: ['documents', 'compare', documentId, 'left', leftVersionId],
    queryFn: () => api.getVersion(documentId, leftVersionId as number),
    enabled: Number.isFinite(documentId) && leftVersionId !== null,
  })

  const { data: rightVersionDetail, isLoading: isRightLoading } = useQuery({
    queryKey: ['documents', 'compare', documentId, 'right', rightVersionId],
    queryFn: () => api.getVersion(documentId, rightVersionId as number),
    enabled: Number.isFinite(documentId) && rightVersionId !== null,
  })

  if (!Number.isFinite(documentId)) {
    return (
      <NotFoundState
        title="Document Not Found"
        description="This comparison request is missing a valid document id."
      />
    )
  }

  if (isDocumentLoading || areVersionsLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-sky-600" />
      </div>
    )
  }

  if (documentError || !document) {
    return (
      <NotFoundState
        title="Document Not Found"
        description="The document could not be loaded for version comparison."
      />
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Version Compare"
        title={`Compare versions for ${document.title}`}
        subtitle="Review changes side-by-side before approving, publishing, or restoring content."
        actions={
          <>
            <Link to={`/documents/${documentId}`} className="btn-ghost inline-flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to document
            </Link>
            <button
              type="button"
              onClick={() => {
                setLeftVersionId(rightVersionId)
                setRightVersionId(leftVersionId)
              }}
              disabled={leftVersionId === null || rightVersionId === null}
              className="btn-secondary inline-flex items-center gap-2"
            >
              <ArrowLeftRight className="h-4 w-4" />
              Swap sides
            </button>
          </>
        }
        meta={
          <div className="inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
            <GitCompareArrows className="h-3.5 w-3.5" />
            {versions.length} version{versions.length === 1 ? '' : 's'} available
          </div>
        }
      />

      {versions.length < 2 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-12 text-center text-slate-500">
          <GitCompareArrows className="mx-auto mb-3 h-10 w-10 text-slate-300" />
          <p className="text-sm">At least two versions are needed before a side-by-side compare is useful.</p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 lg:grid-cols-2">
            <label className="space-y-2 text-sm text-slate-600">
              <span className="font-medium text-slate-900">Left version</span>
              <select
                value={leftVersionId ?? ''}
                onChange={(event) => setLeftVersionId(Number(event.target.value))}
                className="select-field"
              >
                {versions.map((version) => (
                  <option key={version.id} value={version.id}>
                    {getVersionLabel(version)}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm text-slate-600">
              <span className="font-medium text-slate-900">Right version</span>
              <select
                value={rightVersionId ?? ''}
                onChange={(event) => setRightVersionId(Number(event.target.value))}
                className="select-field"
              >
                {versions.map((version) => (
                  <option key={version.id} value={version.id}>
                    {getVersionLabel(version)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {(isLeftLoading || isRightLoading) ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500">
              Loading selected versions...
            </div>
          ) : (
            <VersionDiffView
              leftHtml={leftVersionDetail?.content || selectedLeftVersion?.content || ''}
              rightHtml={rightVersionDetail?.content || selectedRightVersion?.content || ''}
              leftLabel={getVersionLabel(leftVersionDetail || selectedLeftVersion)}
              rightLabel={getVersionLabel(rightVersionDetail || selectedRightVersion)}
            />
          )}
        </>
      )}
    </div>
  )
}
