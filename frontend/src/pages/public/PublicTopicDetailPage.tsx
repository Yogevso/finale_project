import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import OptimizedImage from '@/components/OptimizedImage'
import { CardSkeleton } from '@/components/skeletons'
import { publicApi } from '@/lib/publicApi'
import { audienceSensitiveQueryOptions } from '@/lib/queryFreshness'

function TagPill({ label }: { label: string }) {
  return <span className="pill border-white/50 bg-white/90 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">{label}</span>
}

export default function PublicTopicDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()

  const {
    data: topic,
    isLoading: topicLoading,
    isError: topicError,
    refetch: refetchTopic,
  } = useQuery({
    queryKey: ['public-topic', slug],
    queryFn: () => publicApi.getTopic(slug || ''),
    enabled: !!slug,
    ...audienceSensitiveQueryOptions,
  })

  const {
    data: docs,
    isLoading: docsLoading,
    isError: docsError,
    refetch: refetchDocs,
  } = useQuery({
    queryKey: ['public-topic-docs', slug],
    queryFn: () => publicApi.getDocuments({ page: 1, page_size: 30, topic: slug }),
    enabled: !!slug,
    ...audienceSensitiveQueryOptions,
  })

  if (topicLoading) {
    return (
      <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
        <section className="content-shell py-16">
          <div className="space-y-4">
            <div className="h-4 w-24 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
            <div className="h-10 w-80 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
            <div className="h-4 w-2/3 animate-pulse rounded-full bg-slate-200 dark:bg-slate-800" />
          </div>
        </section>
        <section className="content-shell py-10">
          <CardSkeleton count={6} className="md:grid-cols-2 xl:grid-cols-3" />
        </section>
      </div>
    )
  }

  if (topicError) {
    return (
      <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
        <section className="content-shell py-16">
          <ErrorState
            title="Unable to load topic"
            message="This topic page could not be loaded right now."
            onRetry={() => {
              void refetchTopic()
            }}
          />
        </section>
      </div>
    )
  }

  if (!topic) {
    return (
      <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
        <section className="content-shell py-16">
          <EmptyState
            title="Topic not found"
            description="This topic is not available in the public library."
            action={{
              label: 'Back to topics',
              onClick: () => {
                navigate('/topics')
              },
            }}
          />
        </section>
      </div>
    )
  }

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <section className="relative overflow-hidden bg-slate-900">
        {topic.image_url ? (
          <OptimizedImage
            src={topic.image_url}
            alt=""
            blurPlaceholder
            className="h-full w-full object-cover"
            containerClassName="absolute inset-0"
            height={900}
            responsiveWidths={[640, 1024, 1600, 2200]}
            sizes="100vw"
            width={1600}
            aria-hidden="true"
          />
        ) : null}
        <div className="absolute inset-0 bg-slate-900/35" />
        <div className="content-shell relative py-16 text-white">
          <div className="mb-3 text-xs uppercase tracking-widest text-white/70">Topic</div>
          <h1 className="text-4xl font-display font-bold">{topic.name}</h1>
          <p className="mt-3 max-w-2xl text-white/80">{topic.description}</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <TagPill label={`${topic.document_count || 0} docs`} />
            <Link to="/docs" className="pill border-white/50 bg-white/90 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
              View all docs
            </Link>
          </div>
        </div>
      </section>

      <section className="content-shell py-10">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="page-title">Documents</h2>
          <Link to="/docs" className="btn-secondary table-action-btn">
            Browse library
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {docsLoading ? (
          <CardSkeleton count={6} className="md:grid-cols-2 xl:grid-cols-3" />
        ) : docsError ? (
          <ErrorState
            title="Unable to load topic documents"
            message="The documents for this topic are unavailable right now."
            onRetry={() => {
              void refetchDocs()
            }}
          />
        ) : docs?.items && docs.items.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {docs.items.map((doc) => (
              <Link
                key={doc.id}
                to={`/doc/${doc.id}?fullscreen=1`}
                className="rounded-2xl p-5 surface-card-hover"
              >
                <div className="text-xs uppercase tracking-widest text-slate-400">{doc.category}</div>
                <div className="card-title mt-2 line-clamp-2">{doc.title}</div>
                <p className="body-copy mt-2 line-clamp-2">{doc.description}</p>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No documents for this topic"
            description="Topic-specific documentation will appear here once documents are published."
            action={{
              label: 'Browse library',
              onClick: () => {
                navigate('/docs')
              },
            }}
          />
        )}
      </section>
    </div>
  )
}
