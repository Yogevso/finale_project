import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { publicApi } from '@/lib/publicApi'

type DocumentSort = 'latest' | 'name' | 'category' | 'version' | 'status'

export default function PublicPlatformDetailPage() {
  const { platformId } = useParams<{ platformId: string }>()
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<DocumentSort>('latest')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const parsedPlatformId = useMemo(() => Number(platformId), [platformId])
  const isValidPlatformId = Number.isInteger(parsedPlatformId) && parsedPlatformId > 0

  const { data, isLoading, error } = useQuery({
    queryKey: ['platform-documents', parsedPlatformId, searchTerm, sortBy, sortOrder],
    queryFn: () =>
      publicApi.getPlatformDocuments(parsedPlatformId, {
        search: searchTerm || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    enabled: isValidPlatformId,
  })

  const formatDateOrDash = (value?: string) => {
    if (!value) return '—'
    return new Date(value).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatStatus = (status: string) =>
    status
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (ch) => ch.toUpperCase())

  if (!isValidPlatformId) {
    return (
      <div className="min-h-screen bg-slate-50">
        <section className="max-w-5xl mx-auto px-6 py-12">
          <div className="surface-card rounded-3xl p-8 text-center">
            <h1 className="text-2xl font-display font-semibold text-slate-900 mb-3">
              Invalid Platform
            </h1>
            <p className="text-slate-500 mb-6">The platform id in the URL is not valid.</p>
            <Link to="/platforms" className="btn-primary">
              Back to Platforms
            </Link>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-14">
          <div className="max-w-3xl">
            <div className="text-xs uppercase tracking-widest text-slate-300 mb-3">Platform</div>
            <h1 className="text-4xl font-display font-bold mb-3">
              {data?.platform || 'Platform Documents'}
            </h1>
            <p className="text-slate-200">
              Full document table for this platform release line.
            </p>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="surface-card rounded-3xl p-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <div>
              <h2 className="text-2xl font-display font-semibold text-slate-900">Documents</h2>
              <p className="text-sm text-slate-500 mt-1">{data?.total || 0} documents</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
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
                className="btn-secondary text-xs"
              >
                Order: {sortOrder.toUpperCase()}
              </button>
              <Link to="/platforms" className="btn-secondary text-xs">
                Back to Platforms
              </Link>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-widest text-slate-400">
                  <th className="py-3 px-4">Document Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Published</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((doc) => (
                  <tr key={doc.id} className="border-t border-slate-200">
                    <td className="py-3 px-4 font-medium text-slate-900">
                      <Link to={`/doc/${doc.id}?fullscreen=1`} className="hover:text-sky-700">
                        {doc.title}
                      </Link>
                      <span className="ml-2 text-xs text-slate-400 font-mono">
                        {doc.document_number}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-600">{doc.category || 'General'}</td>
                    <td className="py-3 px-4 text-slate-600">
                      {doc.version_label || (doc.version_number ? `v${doc.version_number}` : '—')}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {formatDateOrDash(doc.published_at || doc.updated_at)}
                    </td>
                    <td className="py-3 px-4 text-slate-600">{formatStatus(doc.status)}</td>
                  </tr>
                ))}
                {!isLoading && !data?.items.length && !error && (
                  <tr>
                    <td colSpan={5} className="py-6 px-4 text-center text-slate-400">
                      No documents found for this platform.
                    </td>
                  </tr>
                )}
                {isLoading && (
                  <tr>
                    <td colSpan={5} className="py-6 px-4 text-center text-slate-400">
                      Loading platform documents...
                    </td>
                  </tr>
                )}
                {error && (
                  <tr>
                    <td colSpan={5} className="py-6 px-4 text-center text-rose-500">
                      Failed to load platform documents.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  )
}
