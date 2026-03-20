import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import OptimizedImage from '@/components/OptimizedImage'
import { CardSkeleton } from '@/components/skeletons'
import { publicApi } from '@/lib/publicApi'

export default function PublicTopicsPage() {
  const {
    data: topics,
    isLoading,
    isError: topicsError,
    refetch: refetchTopics,
  } = useQuery({
    queryKey: ['public-topics'],
    queryFn: () => publicApi.getTopics(),
  })

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <section className="content-shell py-10">
        <div className="surface-card rounded-3xl p-10 shadow-sm">
          <div className="mb-3 text-xs uppercase tracking-widest text-slate-400">Viewer Portal</div>
          <h1 className="text-3xl font-display font-bold text-slate-900 dark:text-slate-100">Topics</h1>
          <p className="body-copy mt-2">
            Browse technical areas, programs, and product documentation.
          </p>
        </div>
      </section>

      <section className="content-shell pb-16">
        {isLoading ? (
          <CardSkeleton count={6} className="md:grid-cols-3 xl:grid-cols-3" />
        ) : topicsError ? (
          <ErrorState
            title="Unable to load topics"
            message="Public topics could not be loaded right now."
            onRetry={() => {
              void refetchTopics()
            }}
          />
        ) : topics?.items && topics.items.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {topics.items.map((topic) => (
              <Link
                key={topic.slug}
                to={`/topics/${topic.slug}`}
                className="group relative overflow-hidden rounded-2xl p-6 surface-card-hover"
              >
                {topic.image_url && (
                  <OptimizedImage
                    src={topic.image_url}
                    alt=""
                    blurPlaceholder
                    className="h-full w-full object-cover opacity-85"
                    containerClassName="absolute inset-0"
                    height={400}
                    responsiveWidths={[480, 768, 1200]}
                    sizes="(min-width: 768px) 33vw, 100vw"
                    width={640}
                    aria-hidden="true"
                  />
                )}
                <div className="absolute inset-0 bg-slate-900/35" aria-hidden="true" />
                <div className="relative z-10">
                  <div className="mb-2 text-xs uppercase tracking-widest text-white/70">Topic</div>
                  <h3 className="card-title text-white">{topic.name}</h3>
                  <p className="body-copy mt-2 line-clamp-2 text-white/80">{topic.description}</p>
                  <span className="mt-3 inline-flex items-center gap-1 text-sm text-white/90">
                    {topic.document_count} docs <ArrowRight className="h-4 w-4" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No topics available"
            description="Topics will appear here after documentation areas are published."
          />
        )}
      </section>
    </div>
  )
}
