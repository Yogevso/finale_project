import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { TableSkeleton } from '@/components/skeletons'
import { publicApi } from '@/lib/publicApi'
import { audienceSensitiveQueryOptions } from '@/lib/queryFreshness'
import { formatDocumentDate } from '@/lib/dateUtils'

type DocumentSort = 'latest' | 'name' | 'category' | 'version' | 'status'

export default function PublicPlatformDetailPage() {
  const { platformId } = useParams<{ platformId: string }>()
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<DocumentSort>('latest')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const parsedPlatformId = useMemo(() => Number(platformId), [platformId])
  const isValidPlatformId = Number.isInteger(parsedPlatformId) && parsedPlatformId > 0

  const {
    data,
    isLoading,
    isError: platformError,
    refetch: refetchPlatformDocuments,
  } = useQuery({
    queryKey: ['platform-documents', parsedPlatformId, searchTerm, sortBy, sortOrder],
    queryFn: () =>
      publicApi.getPlatformDocuments(parsedPlatformId, {
        search: searchTerm || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    enabled: isValidPlatformId,
    ...audienceSensitiveQueryOptions,
  })

  const formatDateOrDash = (value?: string) => formatDocumentDate(value)

  const formatStatus = (status: string) =>
    status
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (ch) => ch.toUpperCase())

  const hasCustomFilters = searchTerm.trim().length > 0 || sortBy !== 'latest' || sortOrder !== 'desc'

  if (!isValidPlatformId) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
        <section className="content-shell py-12">
          <div className="surface-card rounded-3xl p-8 text-center">
            <h1 className="page-title mb-3">Invalid Platform</h1>
            <p className="body-copy mb-6">The platform id in the URL is not valid.</p>
            <Link to="/platforms" className="btn-primary">
              Back to Platforms
            </Link>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <section className="bg-gradient-to-l from-blue-700 via-blue-600 to-blue-500 text-white">
        <div className="content-shell py-9">
          <div className="max-w-3xl">
            <div className="mb-2 text-xs uppercase tracking-widest text-slate-300">
              <Link to="/platforms" className="hover:text-white/90">
                Platforms
              </Link>
              <span className="mx-2 text-white/40">/</span>
              Platform
            </div>
            <h1 className="mb-2 text-3xl font-display font-bold">
              {data?.platform || 'Platform Documents'}
            </h1>
            <p className="text-slate-200">Full document table for this platform release line.</p>
            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-3 py-1.5 text-xs text-slate-100">
              <span className="font-semibold">{data?.total || 0}</span>
              documents
            </div>
          </div>
        </div>
      </section>

      <section className="content-shell py-8">
        <div className="public-table-shell">
          <div className="public-table-section-head">
            <div>
              <h2 className="page-title">Documents</h2>
              <p className="body-copy mt-1">{data?.total || 0} documents</p>
            </div>
          </div>

          <div className="public-table-toolbar">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search in this platform"
                className="input-field sm:w-56"
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as DocumentSort)}
                className="select-field sm:w-48"
              >
                <option value="latest">Sort by latest</option>
                <option value="name">Sort by name</option>
                <option value="category">Sort by category</option>
                <option value="version">Sort by version</option>
                <option value="status">Sort by status</option>
              </select>
              <button
                type="button"
                onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
                className="btn-secondary table-action-btn"
              >
                Order: {sortOrder.toUpperCase()}
              </button>
              <Link to="/platforms" className="btn-secondary table-action-btn">
                Back to Platforms
              </Link>
            </div>
          </div>

          {isLoading ? (
            <div className="p-6">
              <TableSkeleton rows={6} columns={6} />
            </div>
          ) : platformError ? (
            <div className="p-6">
              <ErrorState
                title="Unable to load platform documents"
                message="This platform release line could not be loaded right now."
                onRetry={() => {
                  void refetchPlatformDocuments()
                }}
              />
            </div>
          ) : !data?.items.length ? (
            <div className="p-6">
              <EmptyState
                title="No documents found for this platform"
                description={
                  hasCustomFilters
                    ? 'Try resetting your filters to see the full platform release line.'
                    : 'Documents will appear here as releases are published for this platform.'
                }
                action={
                  hasCustomFilters
                    ? {
                        label: 'Reset filters',
                        onClick: () => {
                          setSearchTerm('')
                          setSortBy('latest')
                          setSortOrder('desc')
                        },
                      }
                    : undefined
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="public-table-head">
                  <tr className="public-table-head-row">
                    <th className="px-4 py-3">Document Name</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Published</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Open</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((doc) => (
                    <tr
                      key={doc.id}
                      className="public-table-row group"
                    >
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">
                        <Link to={`/doc/${doc.id}?fullscreen=1`} className="hover:text-blue-700">
                          {doc.title}
                        </Link>
                        <span className="ml-2 text-xs font-mono text-slate-400 dark:text-slate-500">
                          {doc.document_number}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{doc.category || 'General'}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                        {doc.version_label || (doc.version_number ? `v${doc.version_number}` : '-')}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                        {formatDateOrDash(doc.published_at || doc.updated_at)}
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                        <span className="inline-flex rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {formatStatus(doc.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/doc/${doc.id}?fullscreen=1`}
                          className="btn-secondary table-action-btn"
                        >
                          Open
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
