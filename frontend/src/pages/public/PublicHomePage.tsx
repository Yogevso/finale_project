import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileText, Search, ArrowRight, BookOpen, Wrench } from 'lucide-react'
import { useState } from 'react'
import { publicApi } from '@/lib/publicApi'
import { SEO } from '@/components/SEO'

export default function PublicHomePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  // Fetch recent public documents
  const { data: recentDocs, isLoading: docsLoading } = useQuery({
    queryKey: ['public-documents', { page: 1, page_size: 6 }],
    queryFn: () => publicApi.getDocuments({ page: 1, page_size: 6 }),
  })

  // Fetch categories
  const { data: categories } = useQuery({
    queryKey: ['public-categories'],
    queryFn: () => publicApi.getCategories(),
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  return (
    <div className="bg-slate-50">
      <SEO
        title="Home"
        description="Browse technical documentation, release notes, and guides on our documentation platform."
      />
      {/* Hero Section */}
      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="max-w-4xl">
            <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Viewer Portal</div>
            <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
              Documentation Platform
            </h1>
            <p className="text-lg text-sky-100 mb-6">
              Find approved documentation fast. Browse tools and release notes with role-aware access.
            </p>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="max-w-3xl">
              <div className="flex flex-col md:flex-row gap-3">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="Search docs and tools"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full px-6 py-3.5 pl-12 rounded-full text-slate-900 focus:outline-none focus:ring-4 focus:ring-sky-300/40"
                  />
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                </div>
                <button
                  type="submit"
                  className="px-6 py-3.5 rounded-full bg-white text-sky-900 font-medium hover:bg-sky-50"
                >
                  Search
                </button>
              </div>
            </form>

            <div className="flex flex-wrap gap-3 mt-6">
              <Link to="/docs" className="px-4 py-2 rounded-full bg-white/10 text-white border border-white/20 hover:bg-white/20">
                Browse documents
              </Link>
              <Link to="/tools" className="px-4 py-2 rounded-full bg-white/10 text-white border border-white/20 hover:bg-white/20">
                Explore tools
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Essentials + Quick Paths */}
      <section className="py-14">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_0.8fr] gap-8">
            <div className="surface-card rounded-3xl p-8">
              <div className="text-xs uppercase tracking-widest text-slate-400 mb-2">Browse by</div>
              <h2 className="text-2xl font-display font-semibold text-slate-900 mb-6">Start with the essentials</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Link to="/docs" className="surface-card-hover rounded-2xl p-4">
                  <BookOpen className="h-6 w-6 text-sky-600 mb-3" />
                  <div className="font-medium text-slate-900">Documentation Library</div>
                  <p className="text-sm text-slate-500">Approved docs, release notes, and guides.</p>
                </Link>
                <Link to="/tools" className="surface-card-hover rounded-2xl p-4">
                  <Wrench className="h-6 w-6 text-sky-600 mb-3" />
                  <div className="font-medium text-slate-900">Tools</div>
                  <p className="text-sm text-slate-500">SDKs, APIs, and supporting resources.</p>
                </Link>
              </div>
            </div>

            <div className="surface-card rounded-3xl p-8">
              <div className="text-xs uppercase tracking-widest text-slate-400 mb-2">Quick paths</div>
              <h3 className="text-xl font-display font-semibold text-slate-900 mb-4">Most visited</h3>
              <div className="space-y-3">
                {(categories?.items || []).slice(0, 4).map((cat) => (
                  <Link
                    key={cat.category}
                    to={`/docs?category=${encodeURIComponent(cat.category)}`}
                    className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 hover:bg-slate-50"
                  >
                    <span className="text-slate-700">{cat.category}</span>
                    <span className="pill bg-slate-100 text-slate-600 border-slate-200">Docs</span>
                  </Link>
                ))}
              </div>
              <div className="mt-6 text-xs text-slate-500">
                Need internal access? Switch to the management portal for drafts, reviews, and publishing.
              </div>
              <Link to="/login" className="inline-flex items-center gap-2 mt-4 btn-secondary">
                Go to Management Portal <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Most Popular */}
      <section className="py-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-xs uppercase tracking-widest text-slate-400">Most popular</div>
              <h2 className="text-2xl font-display font-semibold text-slate-900">Most viewed documentation</h2>
              <p className="text-slate-500 text-sm mt-1">
                Start with the highest-impact guides and release notes.
              </p>
            </div>
            <Link to="/docs" className="btn-secondary">View all</Link>
          </div>

          {docsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-44 bg-white rounded-2xl border border-slate-200 animate-pulse" />
              ))}
            </div>
          ) : recentDocs?.items && recentDocs.items.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {recentDocs.items.slice(0, 3).map((doc) => (
                <Link key={doc.id} to={`/doc/${doc.id}?fullscreen=1`} className="surface-card-hover rounded-2xl p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-sky-100 flex items-center justify-center">
                        <FileText className="h-5 w-5 text-sky-600" />
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-widest text-slate-400">Public access</div>
                        <div className="font-medium text-slate-900">{doc.title}</div>
                      </div>
                    </div>
                    <span className="pill bg-slate-100 text-slate-600 border-slate-200">v1.0</span>
                  </div>
                  <p className="text-sm text-slate-500 mt-3 line-clamp-2">
                    {doc.description || 'No description available'}
                  </p>
                  <div className="mt-4 inline-flex items-center gap-2 text-sm text-sky-700">
                    Open document <ArrowRight className="h-4 w-4" />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500">
              <BookOpen className="h-12 w-12 mx-auto mb-4 text-slate-300" />
              <p>No public documents available yet.</p>
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-12">
        <div className="max-w-6xl mx-auto px-6">
          <div className="rounded-3xl bg-white border border-slate-200 p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <h2 className="text-xl font-display font-semibold text-slate-900">Need access to more documents?</h2>
              <p className="text-slate-500 mt-2">
                Login to access internal documentation, company-specific resources, and more.
              </p>
            </div>
            <Link to="/login" className="btn-primary inline-flex items-center gap-2">
              Sign in for full access <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
