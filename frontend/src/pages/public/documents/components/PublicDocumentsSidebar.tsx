import { ChevronDown, ChevronRight, Search } from 'lucide-react'

import type { CategoryTreeNode } from '../lib/catalog'

interface PublicDocumentsSidebarProps {
  activeCategory?: string
  categoryTree: CategoryTreeNode[]
  expandedCategoryIds: string[]
  localSearch: string
  onCategoryClick: (category: string | null) => void
  onLocalSearchChange: (value: string) => void
  onSearchSubmit: (event: React.FormEvent) => void
  onToggleCategoryNode: (categoryId: string) => void
  totalCategoryDocuments: number
}

export function PublicDocumentsSidebar({
  activeCategory,
  categoryTree,
  expandedCategoryIds,
  localSearch,
  onCategoryClick,
  onLocalSearchChange,
  onSearchSubmit,
  onToggleCategoryNode,
  totalCategoryDocuments,
}: PublicDocumentsSidebarProps) {
  const renderCategoryNodes = (nodes: CategoryTreeNode[], level = 0): React.ReactNode =>
    nodes.map((node) => {
      const hasChildren = node.children.length > 0
      const isExpanded = expandedCategoryIds.includes(node.id)
      const isSelected = node.filterCategory === activeCategory

      return (
        <li key={node.id}>
          <div
            className={`flex items-center gap-2 rounded-xl transition-colors ${
              isSelected
                ? 'bg-sky-50 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
                : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
            style={{ paddingLeft: `${0.75 + level * 0.8}rem` }}
          >
            {hasChildren ? (
              <button
                type="button"
                onClick={() => onToggleCategoryNode(node.id)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-white hover:text-slate-900 dark:text-slate-500 dark:hover:bg-slate-900 dark:hover:text-slate-200"
                aria-label={isExpanded ? `Collapse ${node.label}` : `Expand ${node.label}`}
              >
                {isExpanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </button>
            ) : (
              <span
                className="inline-flex h-8 w-8 items-center justify-center text-slate-500 dark:text-slate-700"
                aria-hidden="true"
              >
                *
              </span>
            )}
            <button
              type="button"
              onClick={() =>
                node.filterCategory ? onCategoryClick(node.filterCategory) : onToggleCategoryNode(node.id)
              }
              className="flex min-w-0 flex-1 items-center justify-between gap-3 py-2 pr-3 text-left"
            >
              <span className={`truncate ${isSelected ? 'font-medium' : ''}`}>{node.label}</span>
              <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {node.count}
              </span>
            </button>
          </div>
          {hasChildren && isExpanded ? (
            <ul className="mt-1 space-y-1">{renderCategoryNodes(node.children, level + 1)}</ul>
          ) : null}
        </li>
      )
    })

  return (
    <aside className="flex-shrink-0 lg:sticky lg:top-6 lg:w-72 lg:self-start">
      <form onSubmit={onSearchSubmit} className="mb-6">
        <div className="relative">
          <input
            type="text"
            placeholder="Search..."
            value={localSearch}
            onChange={(event) => onLocalSearchChange(event.target.value)}
            className="input-field pl-10"
            aria-label="Search public documents"
          />
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600 dark:text-slate-500"
            aria-hidden="true"
          />
        </div>
      </form>

      <div className="surface-card rounded-2xl p-4">
        <div className="mb-3">
          <h3 className="card-title">Categories</h3>
          <p className="helper-copy mt-1">Browse nested documentation areas</p>
        </div>
        <ul className="space-y-1">
          <li>
            <button
              type="button"
              onClick={() => onCategoryClick(null)}
              className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-left transition-colors ${
                !activeCategory
                  ? 'bg-sky-50 font-medium text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'
                  : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              <span>All Categories</span>
              <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                {totalCategoryDocuments}
              </span>
            </button>
          </li>
          {renderCategoryNodes(categoryTree)}
        </ul>
      </div>
    </aside>
  )
}
