import { SEO } from '@/components/SEO'
import {
  PublicDocumentsResults,
  PublicDocumentsSidebar,
  PublicDocumentsToolbar,
  PublicPlatformHighlights,
} from '@/pages/public/documents/components'
import { usePublicDocumentsPageController } from '@/pages/public/documents/hooks'

export default function PublicDocumentsPage() {
  const controller = usePublicDocumentsPageController()

  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <SEO
        title="Documentation Library"
        description="Explore approved documentation, release notes, and technical guides."
      />

      <section className="bg-gradient-to-l from-sky-700 via-sky-600 to-sky-500 text-white">
        <div className="content-shell py-14">
          <div className="max-w-3xl">
            <div className="mb-3 text-xs uppercase tracking-widest text-white/85">
              Viewer Portal
            </div>
            <h1 className="mb-3 text-4xl font-display font-bold">Documentation Library</h1>
            <p className="text-sky-100">
              Explore approved documentation, release notes, and technical guides curated by the
              docs team.
            </p>
          </div>
        </div>
      </section>

      <section className="content-shell py-10">
        <div className="flex flex-col gap-8 lg:flex-row">
          <PublicDocumentsSidebar
            activeCategory={controller.category}
            categoryTree={controller.categoryTree}
            expandedCategoryIds={controller.expandedCategoryIds}
            localSearch={controller.localSearch}
            onCategoryClick={controller.handleCategoryClick}
            onLocalSearchChange={controller.setLocalSearch}
            onSearchSubmit={controller.handleLocalSearchSubmit}
            onToggleCategoryNode={controller.toggleCategoryNode}
            totalCategoryDocuments={controller.totalCategoryDocuments}
          />

          <main className="flex-1">
            <PublicPlatformHighlights items={controller.latestPlatformReleases} />

            <PublicDocumentsToolbar
              activeCategory={controller.category}
              resultCount={controller.docsQuery.data?.total || 0}
              search={controller.search}
              viewMode={controller.viewMode}
              onClearAllFilters={controller.clearAllFilters}
              onClearCategory={() => controller.handleCategoryClick(null)}
              onClearSearch={controller.clearSearch}
              onViewModeChange={controller.setViewMode}
            />

            <PublicDocumentsResults
              docs={controller.docsQuery.data}
              isError={controller.docsQuery.isError}
              isLoading={controller.docsQuery.isLoading}
              onClearFilters={controller.clearAllFilters}
              onPageChange={controller.handlePageChange}
              onRetry={() => void controller.docsQuery.refetch()}
              page={controller.page}
              search={controller.search}
              selectedCategory={controller.category}
              viewMode={controller.viewMode}
            />
          </main>
        </div>
      </section>
    </div>
  )
}
