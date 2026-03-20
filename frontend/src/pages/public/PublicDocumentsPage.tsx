import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  Folder,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Grid,
  List,
  Search,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { publicApi } from '@/lib/publicApi'
import { SEO } from '@/components/SEO'
import { CardSkeleton, ListSkeleton } from '@/components/skeletons'

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

type CategoryTreeNode = {
  id: string
  label: string
  count: number
  selfCount: number
  filterCategory: string | null
  children: CategoryTreeNode[]
}

const normalizePlatformName = (value: string) => value.trim().toLowerCase()
const CATEGORY_DELIMITER_PATTERN = /\s*(?:\/|>)\s*/

const splitCategorySegments = (value: string) =>
  value
    .split(CATEGORY_DELIMITER_PATTERN)
    .map((segment) => segment.trim())
    .filter(Boolean)

const buildCategoryTree = (items: Array<{ category: string; count: number }>): CategoryTreeNode[] => {
  const roots: CategoryTreeNode[] = []
  const nodeMap = new Map<string, CategoryTreeNode>()

  for (const item of items) {
    const segments = splitCategorySegments(item.category)
    if (segments.length === 0) {
      continue
    }

    let parentPath = ''
    let currentLevel = roots

    segments.forEach((segment, index) => {
      const nodeId = parentPath ? `${parentPath} / ${segment}` : segment
      let node = nodeMap.get(nodeId)

      if (!node) {
        node = {
          id: nodeId,
          label: segment,
          count: 0,
          selfCount: 0,
          filterCategory: null,
          children: [],
        }
        nodeMap.set(nodeId, node)
        currentLevel.push(node)
      }

      node.count += item.count
      if (index === segments.length - 1) {
        node.selfCount += item.count
        node.filterCategory = item.category
      }

      parentPath = nodeId
      currentLevel = node.children
    })
  }

  const sortNodes = (nodes: CategoryTreeNode[]) => {
    nodes.sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count
      }
      return left.label.localeCompare(right.label)
    })
    nodes.forEach((node) => sortNodes(node.children))
  }

  sortNodes(roots)
  return roots
}

export default function PublicDocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [localSearch, setLocalSearch] = useState('')
  const [expandedCategoryIds, setExpandedCategoryIds] = useState<string[]>([])

  const page = parseInt(searchParams.get('page') || '1')
  const category = searchParams.get('category') || undefined
  const search = searchParams.get('search') || undefined

  useEffect(() => {
    setLocalSearch(search || '')
  }, [search])

  // Fetch documents
  const {
    data: docs,
    isLoading: docsLoading,
    isError: docsError,
    refetch: refetchDocs,
  } = useQuery({
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
  const categoryTree = useMemo(() => buildCategoryTree(sortedCategories), [sortedCategories])

  useEffect(() => {
    if (!category) {
      return
    }

    const nextExpanded = splitCategorySegments(category).reduce<string[]>((paths, segment) => {
      const previous = paths[paths.length - 1]
      paths.push(previous ? `${previous} / ${segment}` : segment)
      return paths
    }, [])

    setExpandedCategoryIds((previous) => Array.from(new Set([...previous, ...nextExpanded])))
  }, [category])

  const toggleCategoryNode = (categoryId: string) => {
    setExpandedCategoryIds((previous) =>
      previous.includes(categoryId)
        ? previous.filter((value) => value !== categoryId)
        : [...previous, categoryId],
    )
  }

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

  const renderCategoryNodes = (nodes: CategoryTreeNode[], level: number = 0) =>
    nodes.map((node) => {
      const hasChildren = node.children.length > 0
      const isExpanded = expandedCategoryIds.includes(node.id)
      const isSelected = node.filterCategory === category

      return (
        <li key={node.id}>
          <div
            className={`flex items-center gap-2 rounded-xl transition-colors ${
              isSelected
                ? 'bg-sky-50 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
                : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
            style={{ paddingLeft: `${0.75 + level * 0.8}rem` }}
          >
            {hasChildren ? (
              <button
                type="button"
                onClick={() => toggleCategoryNode(node.id)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-white hover:text-slate-900 dark:text-slate-500 dark:hover:bg-slate-900 dark:hover:text-slate-200"
                aria-label={isExpanded ? `Collapse ${node.label}` : `Expand ${node.label}`}
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
            ) : (
              <span className="inline-flex h-8 w-8 items-center justify-center text-slate-500 dark:text-slate-700" aria-hidden="true">*</span>
            )}
            <button
              type="button"
              onClick={() =>
                node.filterCategory ? handleCategoryClick(node.filterCategory) : toggleCategoryNode(node.id)
              }
              className="flex min-w-0 flex-1 items-center justify-between gap-3 py-2 pr-3 text-left"
            >
              <span className={`truncate ${isSelected ? 'font-medium' : ''}`}>{node.label}</span>
              <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{node.count}</span>
            </button>
          </div>
          {hasChildren && isExpanded ? (
            <ul className="mt-1 space-y-1">{renderCategoryNodes(node.children, level + 1)}</ul>
          ) : null}
        </li>
      )
    })

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <SEO
        title="Documentation Library"
        description="Explore approved documentation, release notes, and technical guides."
      />
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="content-shell py-14">
          <div className="max-w-3xl">
            <div className="mb-3 text-xs uppercase tracking-widest text-white/85">Viewer Portal</div>
            <h1 className="text-4xl font-display font-bold mb-3">Documentation Library</h1>
            <p className="text-sky-100">
              Explore approved documentation, release notes, and technical guides curated by the docs team.
            </p>
          </div>
        </div>
      </section>

      <section className="content-shell py-10">
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
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600 dark:text-slate-500" aria-hidden="true" />
              </div>
            </form>

            {/* Categories */}
            <div className="surface-card rounded-2xl p-4">
              <div className="mb-3">
                <h3 className="card-title">Categories</h3>
                <p className="helper-copy mt-1">Browse nested documentation areas</p>
              </div>
              <ul className="space-y-1">
                <li>
                  <button
                    type="button"
                    onClick={() => handleCategoryClick(null)}
                    className={`w-full text-left px-3 py-2 rounded-xl transition-colors flex justify-between items-center ${
                      !category
                        ? 'bg-sky-50 text-sky-800 font-medium dark:bg-sky-950/40 dark:text-sky-200'
                        : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
                    }`}
                  >
                    <span>All Categories</span>
                    <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                      {totalCategoryDocuments}
                    </span>
                  </button>
                </li>
                {renderCategoryNodes(categoryTree)}
              </ul>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1">
            {latestPlatformReleases.length > 0 && (
              <div className="surface-card rounded-3xl p-6 mb-8">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
                    <div>
                      <div className="text-xs uppercase tracking-widest text-slate-600">Latest Releases</div>
                    <h2 className="page-title">Platform highlights</h2>
                    <p className="body-copy mt-1">
                      The newest published documents across active platforms.
                    </p>
                  </div>
                  <Link to="/platforms" className="btn-secondary table-action-btn">
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
                      <div className="text-xs uppercase tracking-widest text-slate-600">Platform</div>
                      <div className="section-title mt-1">
                        {item.platform}
                      </div>
                      <div className="body-copy mt-3">
                        {item.latestDoc.title}
                      </div>
                      <div className="helper-copy mt-3 flex flex-wrap items-center gap-2">
                        {item.latestDoc.releaseBranch && (
                          <span className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                            {item.latestDoc.releaseBranch}
                          </span>
                        )}
                        <span className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                          {item.latestDoc.versionLabel ||
                            (item.latestDoc.versionNumber
                              ? `v${item.latestDoc.versionNumber}`
                              : 'Version -')}
                        </span>
                        {item.latestDoc.publishedAt && (
                          <span>{formatDate(item.latestDoc.publishedAt)}</span>
                        )}
                      </div>
                      <div className="mt-3 font-mono text-xs text-slate-600">
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
              <div className="body-copy">
                <span className="font-semibold text-slate-900 dark:text-slate-100">{docs?.total || 0}</span> documents found
              </div>
              <div className="flex gap-2 items-center">
                  <Link to="/platforms" className="btn-secondary table-action-btn">
                    Explore Platforms
                  </Link>
                  <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900">
                    <button
                      type="button"
                      onClick={() => setViewMode('grid')}
                      className={`p-2 rounded-lg ${
                        viewMode === 'grid'
                          ? 'bg-sky-100 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
                          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-500 dark:hover:bg-slate-800'
                      }`}
                      aria-label="Grid view"
                    >
                      <Grid className="h-5 w-5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setViewMode('list')}
                      className={`p-2 rounded-lg ${
                        viewMode === 'list'
                          ? 'bg-sky-100 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
                          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-500 dark:hover:bg-slate-800'
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
                      className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200"
                    >
                      Category: {category}
                      <span aria-hidden>x</span>
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
                      className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                    >
                      Search: {search}
                      <span aria-hidden>x</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setSearchParams({})
                      setLocalSearch('')
                    }}
                    className="text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
                  >
                    Clear all
                  </button>
                </div>
              )}
            </div>

            {/* Documents */}
            {docsLoading ? (
              viewMode === 'grid' ? (
                <CardSkeleton count={6} className="md:grid-cols-2 xl:grid-cols-3" />
              ) : (
                <ListSkeleton rows={6} />
              )
            ) : docsError ? (
              <ErrorState
                title="Unable to load documents"
                message="The documentation library could not be loaded right now."
                onRetry={() => {
                  void refetchDocs()
                }}
              />
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
                          <div className="rounded-xl bg-sky-100 p-3 dark:bg-sky-950/40">
                            <FileText className="h-6 w-6 text-sky-700" aria-hidden="true" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="card-title truncate group-hover:text-sky-700">
                              {doc.title}
                            </h3>
                            <p className="helper-copy mt-1">
                              {doc.document_number}
                            </p>
                            <p className="body-copy mt-2 line-clamp-2">
                              {doc.description || 'No description'}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-2 text-xs">
                              {doc.platform && <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{doc.platform}</span>}
                              {getTags(doc.tags).map((tag) => (
                                <span key={tag} className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <div className="mt-4 flex items-center justify-between text-xs text-slate-600 dark:text-slate-500">
                          <span>{formatDate(doc.created_at)}</span>
                          {doc.category && (
                            <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
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
                          <FileText className="h-8 w-8 flex-shrink-0 text-sky-700" aria-hidden="true" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3">
                              <h3 className="card-title group-hover:text-sky-700">
                                {doc.title}
                              </h3>
                              <span className="helper-copy">
                                {doc.document_number}
                              </span>
                            </div>
                            <p className="body-copy truncate">
                              {doc.description || 'No description'}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2 text-xs">
                              {doc.platform && <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{doc.platform}</span>}
                              {getTags(doc.tags).map((tag) => (
                                <span key={tag} className="pill border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="body-copy">
                              {formatDate(doc.created_at)}
                            </div>
                            {doc.category && (
                              <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
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
                    type="button"
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                    className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <span className="body-copy">
                    Page {page} of {docs.total_pages}
                  </span>
                  <button
                    type="button"
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= docs.total_pages}
                    className="btn-ghost disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              )}
            </>
          ) : (
            <EmptyState
              icon={<Folder className="h-8 w-8" aria-hidden="true" />}
              title="No documents found"
              description={
                search
                  ? `No documents match "${search}".`
                  : 'No approved documents are available for the current category.'
              }
              action={
                category || search
                  ? {
                      label: 'Clear filters',
                      onClick: () => {
                        setSearchParams({})
                        setLocalSearch('')
                      },
                    }
                  : undefined
              }
            />
          )}
          </main>
        </div>
      </section>
    </div>
  )
}
