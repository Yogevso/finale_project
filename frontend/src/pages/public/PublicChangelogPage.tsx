import { useQuery } from '@tanstack/react-query'
import { Calendar, Tag } from 'lucide-react'
import { SEO } from '@/components/SEO'
import { api } from '@/lib/api'

const CATEGORY_COLORS: Record<string, string> = {
  feature: 'bg-emerald-100 text-emerald-700',
  bugfix: 'bg-red-100 text-red-700',
  improvement: 'bg-sky-100 text-sky-700',
}

export default function PublicChangelogPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['changelog', 'public'],
    queryFn: async () => {
      const response = await api.client.get('/changelog', {
        params: { published_only: true, per_page: 50 },
      })
      return response.data
    },
  })

  return (
    <div className="min-h-screen bg-slate-50">
      <SEO title="Changelog" description="See the latest updates, features, and fixes to the documentation platform." />

      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="max-w-4xl mx-auto px-6 py-12">
          <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Platform Updates</div>
          <h1 className="text-3xl md:text-4xl font-display font-bold">Changelog</h1>
          <p className="text-sky-100 mt-3">
            Stay up to date with the latest features, improvements, and fixes.
          </p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-12">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600" />
          </div>
        ) : !data?.items?.length ? (
          <div className="text-center py-12 text-slate-500">
            <p>No changelog entries yet.</p>
          </div>
        ) : (
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-200" />
            <div className="space-y-8">
              {data.items.map((entry: {
                id: number
                title: string
                content: string
                version_tag: string | null
                category: string | null
                created_at: string
              }) => (
                <div key={entry.id} className="relative pl-10">
                  <div className="absolute left-2.5 top-2 w-3 h-3 rounded-full bg-sky-500 border-2 border-white" />
                  <div className="surface-card rounded-2xl p-6">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="flex items-center gap-1 text-xs text-slate-400">
                        <Calendar className="h-3.5 w-3.5" />
                        {new Date(entry.created_at).toLocaleDateString('en-US', {
                          year: 'numeric', month: 'long', day: 'numeric',
                        })}
                      </span>
                      {entry.version_tag && (
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs font-mono">
                          {entry.version_tag}
                        </span>
                      )}
                      {entry.category && (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[entry.category] || 'bg-slate-100 text-slate-600'}`}>
                          <Tag className="h-3 w-3 inline mr-0.5" />
                          {entry.category}
                        </span>
                      )}
                    </div>
                    <h2 className="text-lg font-display font-semibold text-slate-900">{entry.title}</h2>
                    <div className="mt-2 text-sm text-slate-600 prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: entry.content }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
