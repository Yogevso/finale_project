import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { publicApi } from '@/lib/publicApi'

export default function PublicTopicsPage() {
  const { data: topics, isLoading } = useQuery({
    queryKey: ['public-topics'],
    queryFn: () => publicApi.getTopics(),
  })

  return (
    <div className="min-h-screen bg-slate-50">
      <section className="max-w-6xl mx-auto px-6 py-10">
        <div className="rounded-3xl bg-white border border-slate-200 shadow-sm p-10">
          <div className="text-xs uppercase tracking-widest text-slate-400 mb-3">Viewer Portal</div>
          <h1 className="text-3xl font-display font-bold text-slate-900">Topics</h1>
          <p className="text-slate-500 mt-2">
            Browse technical areas, programs, and product documentation.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 bg-white rounded-2xl animate-pulse border border-slate-200" />
            ))}
          </div>
        ) : topics?.items && topics.items.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {topics.items.map((topic) => (
              <Link
                key={topic.slug}
                to={`/topics/${topic.slug}`}
                className="surface-card-hover rounded-2xl p-6 group overflow-hidden relative"
              >
                {topic.image_url && (
                  <div
                    className="absolute inset-0 opacity-85"
                    style={{
                      backgroundImage: `url(${topic.image_url})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    }}
                  />
                )}
                <div className="relative z-10">
                  <div className="text-xs uppercase tracking-widest text-white/70 mb-2">Topic</div>
                  <h3 className="font-semibold text-white text-lg">{topic.name}</h3>
                  <p className="text-sm text-white/80 mt-2 line-clamp-2">{topic.description}</p>
                  <span className="mt-3 inline-flex items-center gap-1 text-white/90 text-sm">
                    {topic.document_count} docs <ArrowRight className="h-4 w-4" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center text-slate-500">No topics available yet.</div>
        )}
      </section>
    </div>
  )
}
