import { SEO } from '@/components/SEO'
import '@/styles/comic-portal.css'
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
    <div className="comic-portal min-h-screen animate-fade-in">
      <SEO
        title="Documentation Library"
        description="Explore approved documentation, release notes, and technical guides."
      />

      <section className="comic-hero">
        <div className="content-shell relative py-16">
          <div className="max-w-3xl">
            <div className="comic-eyebrow mb-5 text-[0.7rem]">Viewer Portal</div>
            <h1 className="comic-title mb-6 font-display text-5xl md:text-6xl">
              Documentation
              <br />
              Library
            </h1>
            <p className="comic-caption max-w-xl text-sm md:text-base">
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
