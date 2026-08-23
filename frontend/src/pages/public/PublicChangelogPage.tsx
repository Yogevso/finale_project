import { useQuery } from '@tanstack/react-query'
import DOMPurify from 'dompurify'
import { Calendar, Tag } from 'lucide-react'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { SEO } from '@/components/SEO'
import { ListSkeleton } from '@/components/skeletons'
import { formatDocumentDate } from '@/lib/dateUtils'

const CATEGORY_COLORS: Record<string, string> = {
  feature: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-200',
  bugfix: 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-200',
  improvement: 'bg-blue-100 text-blue-700 dark:bg-blue-950/50 dark:text-blue-200',
}

export default function PublicChangelogPage() {
  const {
    data,
    isLoading,
    isError: changelogError,
    refetch: refetchChangelog,
  } = useQuery({
    queryKey: ['changelog', 'public'],
    queryFn: async () => {
      const response = await fetch('/api/v1/changelog?published_only=true&per_page=50')
      if (!response.ok) throw new Error('Failed to fetch changelog')
      return response.json()
    },
  })

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <SEO
        title="Changelog"
        description="See the latest updates, features, and fixes to the documentation platform."
      />

      <section className="bg-gradient-to-l from-blue-700 via-blue-600 to-blue-500 text-white">
        <div className="content-shell max-w-4xl py-12">
          <div className="mb-3 text-xs uppercase tracking-widest text-blue-200">Platform Updates</div>
          <h1 className="text-3xl font-display font-bold md:text-4xl">Changelog</h1>
          <p className="mt-3 text-blue-100">
            Stay up to date with the latest features, improvements, and fixes.
          </p>
        </div>
      </section>

      <section className="content-shell max-w-4xl py-12">
        {isLoading ? (
          <ListSkeleton rows={5} />
        ) : changelogError ? (
          <ErrorState
            title="Unable to load the changelog"
            message="Public release notes could not be loaded right now."
            onRetry={() => {
              void refetchChangelog()
            }}
          />
        ) : !data?.items?.length ? (
          <EmptyState
            title="No changelog entries yet"
            description="Published release notes will appear here when updates are announced."
          />
        ) : (
          <div className="relative">
            <div className="absolute bottom-0 left-4 top-0 w-px bg-slate-200 dark:bg-slate-800" />
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
                  <div className="absolute left-2.5 top-2 h-3 w-3 rounded-full border-2 border-white bg-blue-500 dark:border-slate-900" />
                  <div className="surface-card rounded-2xl p-6">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="helper-copy flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        {formatDocumentDate(entry.created_at)}
                      </span>
                      {entry.version_tag ? (
                        <span className="pill border-slate-200 bg-slate-100 font-mono text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {entry.version_tag}
                        </span>
                      ) : null}
                      {entry.category ? (
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            CATEGORY_COLORS[entry.category] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200'
                          }`}
                        >
                          <Tag className="mr-0.5 inline h-3 w-3" />
                          {entry.category}
                        </span>
                      ) : null}
                    </div>
                    <h2 className="section-title">{entry.title}</h2>
                    <div
                      className="prose prose-sm body-copy mt-2 max-w-none dark:prose-invert"
                      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(entry.content) }}
                    />
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
