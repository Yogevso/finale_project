import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { publicApi, type PublicPlatformOverviewItem } from '@/lib/publicApi'

type PlatformSort = 'latest' | 'docs' | 'name'

export default function PublicPlatformsPage() {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<PlatformSort>('latest')

  const { data, isLoading } = useQuery({
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
    if (!value) return '—'
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
    <div className="min-h-screen bg-slate-50">
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-14">
          <div className="max-w-3xl">
            <div className="text-xs uppercase tracking-widest text-slate-300 mb-3">Viewer Portal</div>
            <h1 className="text-4xl font-display font-bold mb-3">Platform Release History</h1>
            <p className="text-slate-200">
              Browse platform documentation by category, year, and release lineage.
            </p>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="surface-card rounded-3xl p-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <div>
              <div className="text-xs uppercase tracking-widest text-slate-400">Latest Releases</div>
              <h2 className="text-2xl font-display font-semibold text-slate-900">
                Active platform lines
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Click a platform row to open its full document table.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
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
              <Link to="/docs" className="btn-secondary text-xs">
                Back to Docs
              </Link>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-widest text-slate-400">
                  <th className="py-3 px-4">Platform</th>
                  <th className="py-3 px-4">Latest Release</th>
                  <th className="py-3 px-4">Branch</th>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Published</th>
                  <th className="py-3 px-4 text-right">Docs</th>
                </tr>
              </thead>
              <tbody>
                {filteredSummaries.map((platform) => (
                  <tr
                    key={platform.id}
                    className="border-t border-slate-200 hover:bg-slate-50 cursor-pointer"
                    onClick={() => openPlatform(platform)}
                  >
                    <td className="py-3 px-4 font-medium text-slate-900">{platform.platform}</td>
                    <td className="py-3 px-4 text-slate-700">
                      {platform.latest_release?.title || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {platform.latest_release?.release_branch || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {platform.latest_release?.version_label ||
                        (platform.latest_release?.version_number
                          ? `v${platform.latest_release.version_number}`
                          : '—')}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {formatDateOrDash(
                        platform.latest_release?.published_at ||
                          platform.latest_release?.updated_at
                      )}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-500">{platform.doc_count}</td>
                  </tr>
                ))}
                {!filteredSummaries.length && !isLoading && (
                  <tr>
                    <td colSpan={6} className="py-6 px-4 text-center text-slate-400">
                      No platform data available yet.
                    </td>
                  </tr>
                )}
                {isLoading && (
                  <tr>
                    <td colSpan={6} className="py-6 px-4 text-center text-slate-400">
                      Loading platform overview...
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
