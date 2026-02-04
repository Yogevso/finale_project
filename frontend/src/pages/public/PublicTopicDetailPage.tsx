import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { publicApi } from '@/lib/publicApi'

function TagPill({ label }: { label: string }) {
  return (
    <span className="pill bg-white/90 text-slate-700 border-white/50">
      {label}
    </span>
  )
}

export default function PublicTopicDetailPage() {
  const { slug } = useParams<{ slug: string }>()

  const { data: topic, isLoading: topicLoading } = useQuery({
    queryKey: ['public-topic', slug],
    queryFn: () => publicApi.getTopic(slug || ''),
    enabled: !!slug,
  })

  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['public-topic-docs', slug],
    queryFn: () => publicApi.getDocuments({ page: 1, page_size: 30, topic: slug }),
    enabled: !!slug,
  })

  if (topicLoading) {
    return <div className="min-h-screen bg-slate-50" />
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `url(${topic?.image_url || ''})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />
        <div className="absolute inset-0 bg-slate-900/35" />
        <div className="relative max-w-6xl mx-auto px-6 py-16 text-white">
          <div className="text-xs uppercase tracking-widest text-white/70 mb-3">Topic</div>
          <h1 className="text-4xl font-display font-bold">{topic?.name}</h1>
          <p className="text-white/80 mt-3 max-w-2xl">{topic?.description}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <TagPill label={`${topic?.document_count || 0} docs`} />
            <Link to="/docs" className="pill bg-white/90 text-slate-700 border-white/50">
              View all docs
            </Link>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-display font-semibold text-slate-900">Documents</h2>
          <Link to="/docs" className="text-sky-700 text-sm">
            Browse library →
          </Link>
        </div>

        {docsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-36 bg-white rounded-2xl border border-slate-200 animate-pulse" />
            ))}
          </div>
        ) : docs?.items && docs.items.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {docs.items.map((doc) => (
              <Link key={doc.id} to={`/doc/${doc.id}`} className="surface-card-hover rounded-2xl p-5">
                <div className="text-xs uppercase tracking-widest text-slate-400">{doc.category}</div>
                <div className="font-semibold text-slate-900 mt-2 line-clamp-2">{doc.title}</div>
                <p className="text-sm text-slate-500 mt-2 line-clamp-2">{doc.description}</p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-slate-500">No documents available for this topic yet.</div>
        )}
      </section>
    </div>
  )
}
