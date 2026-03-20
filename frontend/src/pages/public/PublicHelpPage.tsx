import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Folder, Search } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorState } from '@/components/ErrorState'
import { SEO } from '@/components/SEO'
import { ListSkeleton } from '@/components/skeletons'
import { publicApi } from '@/lib/publicApi'

export default function PublicHelpPage() {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  const {
    data: categories,
    isLoading: categoriesLoading,
    isError: categoriesError,
    refetch: refetchCategories,
  } = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (search.trim()) {
      navigate(`/search?q=${encodeURIComponent(search.trim())}`)
    }
  }

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <SEO title="Help Center" description="Find answers, search documentation, and get support." />

      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="content-shell py-12">
          <div className="mb-3 text-xs uppercase tracking-widest text-white/85">Viewer Portal</div>
          <h1 className="text-3xl font-display font-bold md:text-4xl">Help Center</h1>
          <p className="mt-3 max-w-2xl text-sky-100">
            Guidance for searching docs, requesting access, and staying aligned with release updates.
          </p>
          <form onSubmit={handleSearch} className="mt-6 flex max-w-xl gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-white/85" aria-hidden="true" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documentation..."
                className="w-full rounded-xl border border-white/25 bg-white/14 py-3 pl-10 pr-4 text-white placeholder:text-white/80 focus:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/30"
              />
            </div>
            <button type="submit" className="btn-secondary table-action-btn rounded-xl bg-white text-sky-700 hover:bg-sky-50 dark:bg-slate-950 dark:text-sky-200 dark:hover:bg-slate-900">
              Search
            </button>
          </form>
        </div>
      </section>

      <section className="content-shell py-12">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <div className="surface-card rounded-3xl p-8">
              <h2 className="section-title mb-4">Getting started</h2>
              <div className="space-y-4 leading-6">
                <div>
                  <div className="card-title">How do I find documents?</div>
                  <p className="body-copy">
                    Use the search bar above or{' '}
                    <Link
                      to="/docs"
                      className="font-medium text-sky-800 underline decoration-sky-700/70 underline-offset-4 hover:text-sky-900"
                    >
                      browse the document library
                    </Link>{' '}
                    with category and platform filters.
                  </p>
                </div>
                <div>
                  <div className="card-title">Public vs. restricted documents</div>
                  <p className="body-copy">
                    Public documents are available to everyone. Restricted documents require
                    authentication and role assignments.
                  </p>
                </div>
                <div>
                  <div className="card-title">How do I provide feedback?</div>
                  <p className="body-copy">
                    Each document has a feedback section at the bottom. Your submissions are tracked
                    and you'll receive responses.
                  </p>
                </div>
                <div>
                  <div className="card-title">Can I track my reading progress?</div>
                  <p className="body-copy">
                    Yes! As a logged-in portal user, your reading progress is tracked automatically
                    across devices.
                  </p>
                </div>
              </div>
            </div>

            {categoriesLoading ? (
              <div className="surface-card rounded-3xl p-8">
                <h2 className="section-title mb-4">Browse by category</h2>
                <ListSkeleton rows={4} />
              </div>
            ) : categoriesError ? (
              <div className="surface-card rounded-3xl p-8">
                <h2 className="section-title mb-4">Browse by category</h2>
                <ErrorState
                  className="p-6"
                  title="Unable to load categories"
                  message="Browse-by-category links are unavailable right now."
                  onRetry={() => {
                    void refetchCategories()
                  }}
                />
              </div>
            ) : categories?.items?.length ? (
              <div className="surface-card rounded-3xl p-8">
                <h2 className="section-title mb-4">Browse by category</h2>
                <div className="flex flex-wrap gap-2">
                  {categories.items.map((cat: { category: string; count: number }) => (
                    <Link
                      key={cat.category}
                      to={`/docs?category=${encodeURIComponent(cat.category)}`}
                      className="inline-flex items-center rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700 transition-colors hover:bg-sky-100 hover:text-sky-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-sky-950/50 dark:hover:text-sky-200"
                    >
                      <Folder className="mr-1.5 h-4 w-4" />
                      {cat.category}
                      <span className="ml-1.5 text-xs text-slate-600 dark:text-slate-500">({cat.count})</span>
                    </Link>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          <div className="rounded-3xl bg-gradient-to-br from-sky-900 via-sky-800 to-sky-700 p-8 text-white">
            <div className="mb-3 text-xs uppercase tracking-widest text-white/85">Need help?</div>
            <h3 className="section-title mb-4 text-white">Support channels</h3>
            <ul className="space-y-3 text-sm text-white/90">
              <li>Access requests: contact your portal admin</li>
              <li>Doc corrections: comment directly on the doc</li>
              <li>Tooling issues: open a ticket with Developer Ops</li>
            </ul>
            <Link
              to="/docs"
              className="btn-secondary table-action-btn mt-6 inline-flex bg-white/90 text-sky-900 hover:bg-white"
            >
              Return to docs
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
