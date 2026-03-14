import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Folder } from 'lucide-react'
import { publicApi } from '@/lib/publicApi'
import { SEO } from '@/components/SEO'

export default function PublicHelpPage() {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  const { data: categories } = useQuery({
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
    <div className="min-h-screen bg-slate-50">
      <SEO title="Help Center" description="Find answers, search documentation, and get support." />
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Viewer Portal</div>
          <h1 className="text-3xl md:text-4xl font-display font-bold">Help Center</h1>
          <p className="text-sky-100 mt-3 max-w-2xl">
            Guidance for searching docs, requesting access, and staying aligned with release updates.
          </p>
          <form onSubmit={handleSearch} className="mt-6 flex gap-2 max-w-xl">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-sky-300" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documentation..."
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-sky-200 focus:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/30"
              />
            </div>
            <button type="submit" className="px-5 py-3 bg-white text-sky-700 rounded-xl font-medium hover:bg-sky-50">
              Search
            </button>
          </form>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-8">
          <div className="space-y-6">
            <div className="surface-card rounded-3xl p-8">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Getting started</h2>
              <div className="space-y-4 text-slate-600 text-sm leading-6">
                <div>
                  <div className="font-medium text-slate-900">How do I find documents?</div>
                  <p>Use the search bar above or <Link to="/docs" className="text-sky-600 hover:underline">browse the document library</Link> with category and platform filters.</p>
                </div>
                <div>
                  <div className="font-medium text-slate-900">Public vs. restricted documents</div>
                  <p>Public documents are available to everyone. Restricted documents require authentication and role assignments.</p>
                </div>
                <div>
                  <div className="font-medium text-slate-900">How do I provide feedback?</div>
                  <p>Each document has a feedback section at the bottom. Your submissions are tracked and you'll receive responses.</p>
                </div>
                <div>
                  <div className="font-medium text-slate-900">Can I track my reading progress?</div>
                  <p>Yes! As a logged-in portal user, your reading progress is tracked automatically across devices.</p>
                </div>
              </div>
            </div>

            {/* Browse by Category */}
            {categories && categories.length > 0 && (
              <div className="surface-card rounded-3xl p-8">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Browse by category</h2>
                <div className="flex flex-wrap gap-2">
                  {categories.map((cat: { category: string; count: number }) => (
                    <Link
                      key={cat.category}
                      to={`/docs?category=${encodeURIComponent(cat.category)}`}
                      className="inline-flex items-center px-3 py-2 bg-slate-100 hover:bg-sky-100 text-slate-700 hover:text-sky-700 rounded-lg transition-colors text-sm"
                    >
                      <Folder className="h-4 w-4 mr-1.5" />
                      {cat.category}
                      <span className="ml-1.5 text-xs text-slate-400">({cat.count})</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="rounded-3xl bg-gradient-to-br from-sky-900 via-sky-800 to-sky-700 text-white p-8">
            <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Need help?</div>
            <h3 className="text-xl font-semibold mb-4">Support channels</h3>
            <ul className="text-sm text-sky-100 space-y-3">
              <li>Access requests: contact your portal admin</li>
              <li>Doc corrections: comment directly on the doc</li>
              <li>Tooling issues: open a ticket with Developer Ops</li>
            </ul>
            <Link
              to="/docs"
              className="inline-flex items-center mt-6 px-4 py-2 rounded-full bg-white/90 text-sky-900 text-sm font-medium hover:bg-white"
            >
              Return to docs
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
