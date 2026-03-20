import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { TableSkeleton } from '@/components/skeletons'
import { publicApi, type PublicPlatformOverviewItem } from '@/lib/publicApi'

type PlatformSort = 'latest' | 'docs' | 'name'

export default function PublicPlatformsPage() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<PlatformSort>('latest')

  const {
    data,
    isLoading,
    isError: platformError,
    refetch: refetchPlatforms,
  } = useQuery({
    queryKey: ['platform-overview'],
    queryFn: () => publicApi.getPlatformsOverview(),
  })

  const filteredSummaries = useMemo(() => {
    const items = data?.items || []
    const term = searchTerm.trim().toLowerCase()
    const filtered = term
      ? items.filter((item) => item.platform.toLowerCase().includes(term))
      : items

    return [...filtered].sort((a, b) => {
      if (sortBy === 'docs') return b.doc_count - a.doc_count
      if (sortBy === 'name') return a.platform.localeCompare(b.platform)

      const aDate = a.latest_release?.published_at || a.latest_release?.updated_at || ''
      const bDate = b.latest_release?.published_at || b.latest_release?.updated_at || ''
      return new Date(bDate).getTime() - new Date(aDate).getTime()
    })
  }, [data?.items, searchTerm, sortBy])

  const formatDateOrDash = (value?: string) => {
    if (!value) return '-'
    return new Date(value).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const openPlatform = (platform: PublicPlatformOverviewItem) => {
    navigate(`/platforms/${platform.id}`)
  }

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="content-shell py-9">
          <div className="max-w-3xl">
            <div className="mb-3 text-xs uppercase tracking-widest text-slate-300">Viewer Portal</div>
            <h1 className="mb-2 text-3xl font-display font-bold">Platform Release History</h1>
            <p className="text-slate-200">
              Browse platform documentation by category, year, and release lineage.
            </p>
            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-3 py-1.5 text-xs text-slate-100">
              <span className="font-semibold">{data?.items.length || 0}</span>
              active platform lines
            </div>
          </div>
        </div>
      </section>

      <section className="content-shell py-8">
        <div className="public-table-shell">
          <div className="public-table-section-head">
            <div>
              <div className="text-xs uppercase tracking-widest text-slate-400">Latest Releases</div>
              <h2 className="page-title">Active platform lines</h2>
              <p className="body-copy mt-1">
                Click a platform row to open its full document table.
              </p>
            </div>
          </div>

          <div className="public-table-toolbar">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search platforms"
                className="input-field sm:w-56"
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as PlatformSort)}
                className="select-field sm:w-48"
              >
                <option value="latest">Sort by latest</option>
                <option value="docs">Sort by doc count</option>
                <option value="name">Sort by name</option>
              </select>
              <Link to="/docs" className="btn-secondary table-action-btn">
                Back to Docs
              </Link>
            </div>
          </div>

          {isLoading ? (
            <div className="p-6">
              <TableSkeleton rows={6} columns={7} />
            </div>
          ) : platformError ? (
            <div className="p-6">
              <ErrorState
                title="Unable to load platform history"
                message="The public platform overview is unavailable right now."
                onRetry={() => {
                  void refetchPlatforms()
                }}
              />
            </div>
          ) : !filteredSummaries.length ? (
            <div className="p-6">
              <EmptyState
                title="No platform releases found"
                description={
                  searchTerm
                    ? `No platform lines match "${searchTerm}".`
                    : 'Platform release history will appear here after the first public release.'
                }
                action={
                  searchTerm
                    ? {
                        label: 'Clear search',
                        onClick: () => {
                          setSearchTerm('')
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
                    <th className="px-4 py-3">Platform</th>
                    <th className="px-4 py-3">Latest Release</th>
                    <th className="px-4 py-3">Branch</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Published</th>
                    <th className="px-4 py-3 text-right">Docs</th>
                    <th className="px-4 py-3 text-right">Open</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSummaries.map((platform) => (
                    <tr
                      key={platform.id}
                      className="public-table-row group cursor-pointer"
                      onClick={() => openPlatform(platform)}
                    >
                      <td className="px-4 py-3 font-semibold text-slate-900 dark:text-slate-100">{platform.platform}</td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-200">
                        {platform.latest_release?.title || '-'}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                        {platform.latest_release?.release_branch || '-'}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                        {platform.latest_release?.version_label ||
                          (platform.latest_release?.version_number
                            ? `v${platform.latest_release.version_number}`
                            : '-')}
                      </td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                        {formatDateOrDash(
                          platform.latest_release?.published_at ||
                            platform.latest_release?.updated_at,
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-300">{platform.doc_count}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="btn-secondary table-action-btn pointer-events-none">
                          Open
                          <ArrowRight className="h-4 w-4" aria-hidden="true" />
                        </span>
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
