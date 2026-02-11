import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { publicApi } from '@/lib/publicApi'

type LatestPlatformDocument = {
  id: number
  title: string
  versionLabel?: string
  versionNumber?: number
  releaseBranch?: string
  publishedAt?: string
}

type PlatformSummary = {
  platform: string
  latestDoc: LatestPlatformDocument | null
  docCount: number
}

export default function PublicPlatformsPage() {
  const [activePlatform, setActivePlatform] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'latest' | 'docs' | 'name'>('latest')

  const { data: platformHistory, isLoading } = useQuery({
    queryKey: ['public-platform-history'],
    queryFn: () => publicApi.getPlatformHistory(),
  })

  const platformSummaries = useMemo<PlatformSummary[]>(() => {
    if (!platformHistory?.items) return []
    const summaries: PlatformSummary[] = []

    for (const platform of platformHistory.items) {
      let latestDoc: LatestPlatformDocument | null = null
      let docCount = 0

      for (const category of platform.categories) {
        for (const yearGroup of category.years) {
          for (const doc of yearGroup.documents) {
            docCount += 1
            const docDate = doc.published_at || doc.updated_at
            if (!latestDoc) {
              latestDoc = {
                id: doc.id,
                title: doc.title,
                versionLabel: doc.version_label,
                versionNumber: doc.version_number,
                releaseBranch: doc.release_branch,
                publishedAt: docDate,
              }
            } else {
              const latestDate = latestDoc.publishedAt ? new Date(latestDoc.publishedAt).getTime() : 0
              const candidateDate = docDate ? new Date(docDate).getTime() : 0
              if (candidateDate > latestDate) {
                latestDoc = {
                  id: doc.id,
                  title: doc.title,
                  versionLabel: doc.version_label,
                  versionNumber: doc.version_number,
                  releaseBranch: doc.release_branch,
                  publishedAt: docDate,
                }
              }
            }
          }
        }
      }

      summaries.push({
        platform: platform.platform,
        latestDoc,
        docCount,
      })
    }

    return summaries
  }, [platformHistory])

  const filteredSummaries = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    const summaries = term
      ? platformSummaries.filter((summary) => summary.platform.toLowerCase().includes(term))
      : platformSummaries

    return [...summaries].sort((a, b) => {
      if (sortBy === 'docs') return b.docCount - a.docCount
      if (sortBy === 'name') return a.platform.localeCompare(b.platform)
      const aDate = a.latestDoc?.publishedAt ? new Date(a.latestDoc.publishedAt).getTime() : 0
      const bDate = b.latestDoc?.publishedAt ? new Date(b.latestDoc.publishedAt).getTime() : 0
      return bDate - aDate
    })
  }, [platformSummaries, searchTerm, sortBy])

  const filteredPlatforms = useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    if (!platformHistory?.items) return []
    const base = term
      ? platformHistory.items.filter((platform) =>
          platform.platform.toLowerCase().includes(term)
        )
      : platformHistory.items
    return [...base].sort((a, b) => a.platform.localeCompare(b.platform))
  }, [platformHistory, searchTerm])

  useEffect(() => {
    if (filteredPlatforms.length === 0) return
    if (!activePlatform || !filteredPlatforms.find((item) => item.platform === activePlatform)) {
      setActivePlatform(filteredPlatforms[0].platform)
    }
  }, [activePlatform, filteredPlatforms])

  const formatDateOrDash = (dateStr?: string) => {
    if (!dateStr) return '—'
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
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

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
        <div className="surface-card rounded-3xl p-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <div>
              <div className="text-xs uppercase tracking-widest text-slate-400">Latest Releases</div>
              <h2 className="text-2xl font-display font-semibold text-slate-900">
                Active platform lines
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Quick view of the newest published documents per platform.
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
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
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
                {filteredSummaries.map((summary) => (
                  <tr key={summary.platform} className="border-t border-slate-200">
                    <td className="py-3 px-4 font-medium text-slate-900">
                      {summary.latestDoc ? (
                        <Link
                          to={`/doc/${summary.latestDoc.id}?fullscreen=1`}
                          className="hover:text-sky-700"
                        >
                          {summary.platform}
                        </Link>
                      ) : (
                        summary.platform
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      {summary.latestDoc ? (
                        <Link
                          to={`/doc/${summary.latestDoc.id}?fullscreen=1`}
                          className="hover:text-sky-700"
                        >
                          {summary.latestDoc.title}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {summary.latestDoc?.releaseBranch || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {summary.latestDoc?.versionLabel ||
                        (summary.latestDoc?.versionNumber
                          ? `v${summary.latestDoc.versionNumber}`
                          : '—')}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {formatDateOrDash(summary.latestDoc?.publishedAt)}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-500">
                      {summary.docCount}
                    </td>
                  </tr>
                ))}
                {!filteredSummaries.length && !isLoading && (
                  <tr>
                    <td colSpan={6} className="py-6 px-4 text-center text-slate-400">
                      No platform data available yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="surface-card rounded-3xl p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <aside className="lg:w-56 flex-shrink-0">
              <div className="surface-muted rounded-2xl p-3">
                <div className="text-xs uppercase tracking-widest text-slate-500 mb-3">
                  Platforms
                </div>
                <div className="space-y-1">
                  {filteredPlatforms.map((platform) => (
                    <button
                      key={platform.platform}
                      onClick={() => setActivePlatform(platform.platform)}
                      className={`w-full text-left px-3 py-2 rounded-xl transition-colors ${
                        activePlatform === platform.platform
                          ? 'bg-sky-800 text-white font-semibold'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      {platform.platform}
                    </button>
                  ))}
                  {!filteredPlatforms.length && !isLoading && (
                    <div className="text-sm text-slate-400 px-3 py-2">
                      No platforms yet
                    </div>
                  )}
                </div>
              </div>
            </aside>

            <div className="flex-1 space-y-5">
              {isLoading ? (
                <div className="space-y-4">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-24 bg-slate-100 rounded-2xl animate-pulse" />
                  ))}
                </div>
              ) : (
                platformHistory?.items
                  ?.find((p) => p.platform === activePlatform)
                  ?.categories?.map((cat) => (
                    <details key={cat.category} open className="surface-muted rounded-2xl p-4">
                      <summary className="cursor-pointer list-none flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-sm uppercase tracking-widest text-slate-500">Category</span>
                          <span className="text-lg font-display font-semibold text-slate-900">
                            {cat.category}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400">
                          {cat.years.reduce((sum, year) => sum + year.documents.length, 0)} docs
                        </span>
                      </summary>

                      <div className="mt-4 space-y-4">
                        {cat.years.map((yearGroup) => (
                          <div key={`${cat.category}-${yearGroup.year || 'unknown'}`} className="bg-white border border-slate-200 rounded-2xl">
                            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
                              <div className="flex items-center gap-3">
                                <span className="pill bg-slate-100 text-slate-700 border-slate-200">
                                  {yearGroup.year || 'Unknown'}
                                </span>
                                <span className="text-xs text-slate-400">
                                  {yearGroup.documents.length} documents
                                </span>
                              </div>
                            </div>
                            <div className="divide-y divide-slate-100">
                              {yearGroup.documents.map((doc) => (
                                <div key={doc.id} className="px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                                  <Link
                                  to={`/doc/${doc.id}?fullscreen=1`}
                                    className="font-display font-semibold text-slate-900 hover:text-sky-600"
                                  >
                                    {doc.title}
                                    <span className="ml-2 text-xs text-slate-400 font-mono">
                                      {doc.document_number}
                                    </span>
                                  </Link>
                                  <div className="flex items-center gap-3 text-xs text-slate-500">
                                    <span className="pill bg-slate-50 text-slate-600 border-slate-200">
                                      {doc.version_label ||
                                        (doc.version_number ? `v${doc.version_number}` : 'Version —')}
                                    </span>
                                    {doc.release_branch && (
                                      <span className="pill bg-slate-100 text-slate-600 border-slate-200">
                                        {doc.release_branch}
                                      </span>
                                    )}
                                    <span>{formatDateOrDash(doc.published_at || doc.updated_at)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  ))
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
