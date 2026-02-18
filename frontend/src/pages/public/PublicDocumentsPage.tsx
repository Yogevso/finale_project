import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Folder, ChevronLeft, ChevronRight, Grid, List, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { publicApi } from '@/lib/publicApi'

type LatestPlatformRelease = {
  title: string
  documentNumber: string
  releaseBranch?: string
  versionLabel?: string
  versionNumber?: number
  publishedAt?: string
}

type PlatformReleasePreview = {
  platformId?: number
  platform: string
  latestDoc: LatestPlatformRelease
}

const normalizePlatformName = (value: string) => value.trim().toLowerCase()
const TOP_CATEGORIES_LIMIT = 8

export default function PublicDocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [localSearch, setLocalSearch] = useState('')
  const [showAllCategories, setShowAllCategories] = useState(false)

  const page = parseInt(searchParams.get('page') || '1')
  const category = searchParams.get('category') || undefined
  const search = searchParams.get('search') || undefined

  useEffect(() => {
    setLocalSearch(search || '')
  }, [search])

  // Fetch documents
  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['public-documents', { page, page_size: 12, category, search }],
    queryFn: () => publicApi.getDocuments({ page, page_size: 12, category, search }),
  })

  // Fetch categories for sidebar
  const { data: categories } = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
  })

  const { data: platformHistory } = useQuery({
    queryKey: ['public-platform-history-preview'],
    queryFn: () => publicApi.getPlatformHistory(),
  })

  const { data: platformOverview } = useQuery({
    queryKey: ['public-platform-overview-preview'],
    queryFn: () => publicApi.getPlatformsOverview(),
  })

  const platformIdByName = useMemo(() => {
    const map = new Map<string, number>()
    for (const item of platformOverview?.items || []) {
      map.set(normalizePlatformName(item.platform), item.id)
    }
    return map
  }, [platformOverview?.items])

  const handleCategoryClick = (cat: string | null) => {
    const params = new URLSearchParams(searchParams)
    if (cat) {
      params.set('category', cat)
    } else {
      params.delete('category')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', newPage.toString())
    setSearchParams(params)
  }

  const handleLocalSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (localSearch.trim()) {
      params.set('search', localSearch)
    } else {
      params.delete('search')
    }
    params.set('page', '1')
    setSearchParams(params)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getTags = (tags?: string) =>
    tags ? tags.split(',').map((tag) => tag.trim()).filter(Boolean).slice(0, 3) : []

  const sortedCategories = useMemo(() => {
    const items = categories?.items || []
    return [...items].sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count
      return a.category.localeCompare(b.category)
    })
  }, [categories?.items])

  const totalCategoryDocuments = useMemo(
    () => sortedCategories.reduce((sum, item) => sum + item.count, 0),
    [sortedCategories],
  )

  const visibleCategories = useMemo(() => {
    if (showAllCategories) return sortedCategories

    const top = sortedCategories.slice(0, TOP_CATEGORIES_LIMIT)
    if (!category) return top

    const selected = sortedCategories.find((item) => item.category === category)
    if (!selected) return top
    if (top.some((item) => item.category === selected.category)) return top

    return [...top, selected]
  }, [showAllCategories, sortedCategories, category])

  const hiddenCategoryCount = Math.max(sortedCategories.length - visibleCategories.length, 0)

  const latestPlatformReleases = useMemo<PlatformReleasePreview[]>(() => {
    if (!platformHistory?.items) return []
    const releases: PlatformReleasePreview[] = []

    for (const platform of platformHistory.items) {
      let latestDoc: LatestPlatformRelease | null = null

      for (const category of platform.categories) {
        for (const yearGroup of category.years) {
          for (const doc of yearGroup.documents) {
            const docDate = doc.published_at || doc.updated_at
            if (!latestDoc) {
              latestDoc = {
                title: doc.title,
                documentNumber: doc.document_number,
                releaseBranch: doc.release_branch,
                versionLabel: doc.version_label,
                versionNumber: doc.version_number,
                publishedAt: docDate,
              }
            } else {
              const latestDate = latestDoc.publishedAt ? new Date(latestDoc.publishedAt).getTime() : 0
              const candidateDate = docDate ? new Date(docDate).getTime() : 0
              if (candidateDate > latestDate) {
                latestDoc = {
                  title: doc.title,
                  documentNumber: doc.document_number,
                  releaseBranch: doc.release_branch,
                  versionLabel: doc.version_label,
                  versionNumber: doc.version_number,
                  publishedAt: docDate,
                }
              }
            }
          }
        }
      }

      if (latestDoc) {
        releases.push({
          platformId: platformIdByName.get(normalizePlatformName(platform.platform)),
          platform: platform.platform,
          latestDoc,
        })
      }
    }

    return releases
      .sort((a, b) => {
        const aDate = a.latestDoc.publishedAt ? new Date(a.latestDoc.publishedAt).getTime() : 0
        const bDate = b.latestDoc.publishedAt ? new Date(b.latestDoc.publishedAt).getTime() : 0
        return bDate - aDate
      })
      .slice(0, 3)
  }, [platformHistory, platformIdByName])

  return (
    <div className="min-h-screen bg-slate-50">
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-14">
          <div className="max-w-3xl">
            <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Viewer Portal</div>
            <h1 className="text-4xl font-display font-bold mb-3">Documentation Library</h1>
            <p className="text-sky-100">
              Explore approved documentation, release notes, and technical guides curated by the docs team.
            </p>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <aside className="lg:w-72 lg:sticky lg:top-6 lg:self-start flex-shrink-0">
            {/* Search */}
            <form onSubmit={handleLocalSearch} className="mb-6">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search..."
                  value={localSearch}
                  onChange={(e) => setLocalSearch(e.target.value)}
                  className="input-field pl-10"
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
              </div>
            </form>

            {/* Categories */}
            <div className="surface-card rounded-2xl p-4">
              <div className="mb-3">
                <h3 className="font-display font-semibold text-slate-900">Categories</h3>
                <p className="text-xs text-slate-500 mt-1">Filter by documentation domain</p>
              </div>
              <ul className="space-y-1">
                <li>
                  <button
                    onClick={() => handleCategoryClick(null)}
                    className={`w-full text-left px-3 py-2 rounded-xl transition-colors flex justify-between items-center ${
                      !category
                        ? 'bg-sky-50 text-sky-700 font-medium'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <span>All Categories</span>
                    <span className="pill bg-slate-100 text-slate-600 border-slate-200">
                      {totalCategoryDocuments}
                    </span>
                  </button>
                </li>
                {visibleCategories.map((cat) => (
                  <li key={cat.category}>
                    <button
                      onClick={() => handleCategoryClick(cat.category)}
                      className={`w-full text-left px-3 py-2 rounded-xl transition-colors flex justify-between items-center ${
                        category === cat.category
                          ? 'bg-sky-50 text-sky-700 font-medium'
                          : 'text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <span className="truncate">{cat.category}</span>
                      <span className="pill bg-slate-100 text-slate-600 border-slate-200">
                        {cat.count}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {sortedCategories.length > TOP_CATEGORIES_LIMIT && (
                <button
                  type="button"
                  onClick={() => setShowAllCategories((prev) => !prev)}
                  className="mt-3 w-full text-xs font-semibold text-sky-700 hover:text-sky-800 rounded-lg border border-sky-200 bg-sky-50/60 px-3 py-2"
                >
                  {showAllCategories
                    ? 'Show top categories only'
                    : `Show ${hiddenCategoryCount} more categories`}
                </button>
              )}
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1">
            {latestPlatformReleases.length > 0 && (
              <div className="surface-card rounded-3xl p-6 mb-8">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
                  <div>
                    <div className="text-xs uppercase tracking-widest text-slate-400">Latest Releases</div>
                    <h2 className="text-2xl font-display font-semibold text-slate-900">Platform highlights</h2>
                    <p className="text-sm text-slate-500 mt-1">
                      The newest published documents across active platforms.
                    </p>
                  </div>
                  <Link to="/platforms" className="btn-secondary text-xs">
                    Full platform history
                  </Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {latestPlatformReleases.map((item) => (
                    <Link
                      key={item.platform}
                      to={item.platformId ? `/platforms/${item.platformId}` : '/platforms'}
                      className="surface-muted rounded-2xl p-4 block cursor-pointer transition-shadow hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
                    >
                      <div className="text-xs uppercase tracking-widest text-slate-400">Platform</div>
                      <div className="text-lg font-display font-semibold text-slate-900 mt-1">
                        {item.platform}
                      </div>
                      <div className="mt-3 text-sm text-slate-600">
                        {item.latestDoc.title}
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        {item.latestDoc.releaseBranch && (
                          <span className="pill bg-white text-slate-600 border-slate-200">
                            {item.latestDoc.releaseBranch}
                          </span>
                        )}
                        <span className="pill bg-white text-slate-600 border-slate-200">
                          {item.latestDoc.versionLabel ||
                            (item.latestDoc.versionNumber
                              ? `v${item.latestDoc.versionNumber}`
                              : 'Version —')}
                        </span>
                        {item.latestDoc.publishedAt && (
                          <span>{formatDate(item.latestDoc.publishedAt)}</span>
                        )}
                      </div>
                      <div className="mt-3 text-xs text-slate-400 font-mono">
                        {item.latestDoc.documentNumber}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Toolbar */}
            <div className="surface-card rounded-2xl px-4 py-3 mb-6">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="text-sm text-slate-600">
                  <span className="font-semibold text-slate-900">{docs?.total || 0}</span> documents found
                </div>
                <div className="flex gap-2 items-center">
                  <Link to="/platforms" className="btn-secondary text-xs">
                    Explore Platforms
                  </Link>
                  <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1">
                    <button
                      onClick={() => setViewMode('grid')}
                      className={`p-2 rounded-lg ${
                        viewMode === 'grid'
                          ? 'bg-sky-100 text-sky-700'
                          : 'text-slate-400 hover:bg-slate-100'
                      }`}
                      aria-label="Grid view"
                    >
                      <Grid className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => setViewMode('list')}
                      className={`p-2 rounded-lg ${
                        viewMode === 'list'
                          ? 'bg-sky-100 text-sky-700'
                          : 'text-slate-400 hover:bg-slate-100'
                      }`}
                      aria-label="List view"
                    >
                      <List className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>

              {(category || search) && (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {category && (
                    <button
                      type="button"
                      onClick={() => handleCategoryClick(null)}
                      className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700"
                    >
                      Category: {category}
                      <span aria-hidden>×</span>
                    </button>
                  )}
                  {search && (
                    <button
                      type="button"
                      onClick={() => {
                        const params = new URLSearchParams(searchParams)
                        params.delete('search')
                        params.set('page', '1')
                        setSearchParams(params)
                        setLocalSearch('')
                      }}
                      className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-600"
                    >
                      Search: {search}
                      <span aria-hidden>×</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setSearchParams({})
                      setLocalSearch('')
                    }}
                    className="text-xs font-semibold text-slate-500 hover:text-slate-700"
                  >
                    Clear all
                  </button>
                </div>
              )}
            </div>

            {/* Documents */}
            {docsLoading ? (
              <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-40 bg-slate-100 rounded-2xl animate-pulse" />
                ))}
              </div>
            ) : docs?.items && docs.items.length > 0 ? (
              <>
                {viewMode === 'grid' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {docs.items.map((doc) => (
                      <Link
                        key={doc.id}
                        to={`/doc/${doc.id}?fullscreen=1`}
                        className="surface-card-hover rounded-2xl p-6 group"
                      >
                        <div className="flex items-start gap-4">
                          <div className="bg-sky-100 rounded-xl p-3">
                            <FileText className="h-6 w-6 text-sky-600" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-display font-semibold text-slate-900 truncate group-hover:text-sky-600">
                              {doc.title}
                            </h3>
                            <p className="text-xs text-slate-400 mt-1">
                              {doc.document_number}
                            </p>
                            <p className="text-sm text-slate-500 mt-2 line-clamp-2">
                              {doc.description || 'No description'}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2 text-xs">
                              {doc.platform && <span className="pill bg-slate-100 text-slate-600 border-slate-200">{doc.platform}</span>}
                              {getTags(doc.tags).map((tag) => (
                                <span key={tag} className="pill bg-white text-slate-600 border-slate-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                          <span>{formatDate(doc.created_at)}</span>
                          {doc.category && (
                            <span className="pill bg-slate-100 text-slate-600 border-slate-200">
                              {doc.category}
                            </span>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {docs.items.map((doc) => (
                      <Link
                        key={doc.id}
                        to={`/doc/${doc.id}?fullscreen=1`}
                        className="block surface-card-hover rounded-2xl p-4 group"
                      >
                        <div className="flex items-center gap-4">
                          <FileText className="h-8 w-8 text-sky-500 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3">
                              <h3 className="font-display font-semibold text-slate-900 group-hover:text-sky-600">
                                {doc.title}
                              </h3>
                              <span className="text-xs text-slate-400">
                                {doc.document_number}
                              </span>
                            </div>
                            <p className="text-sm text-slate-500 truncate">
                              {doc.description || 'No description'}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2 text-xs">
                              {doc.platform && <span className="pill bg-slate-100 text-slate-600 border-slate-200">{doc.platform}</span>}
                              {getTags(doc.tags).map((tag) => (
                                <span key={tag} className="pill bg-white text-slate-600 border-slate-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="text-sm text-slate-400">
                              {formatDate(doc.created_at)}
                            </div>
                            {doc.category && (
                              <span className="pill bg-slate-100 text-slate-600 border-slate-200">
                                {doc.category}
                              </span>
                            )}
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}

              {/* Pagination */}
              {docs.total_pages > 1 && (
                <div className="mt-8 flex justify-center items-center gap-4">
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                    className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <span className="text-sm text-slate-600">
                    Page {page} of {docs.total_pages}
                  </span>
                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= docs.total_pages}
                    className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16">
              <Folder className="h-16 w-16 mx-auto mb-4 text-slate-300" />
              <h3 className="text-lg font-display font-medium text-slate-900 mb-2">No documents found</h3>
              <p className="text-slate-500">
                {search ? `No documents match "${search}"` : 'No approved documents available in this category'}
              </p>
              {(category || search) && (
                <button
                  onClick={() => {
                    setSearchParams({})
                    setLocalSearch('')
                  }}
                  className="mt-4 text-sky-600 hover:text-sky-700 font-medium"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
          </main>
        </div>
      </section>
    </div>
  )
}
