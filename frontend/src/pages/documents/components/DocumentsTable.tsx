import type { CSSProperties } from 'react'
import { FileQuestion } from 'lucide-react'
import { Link } from 'react-router-dom'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'
import VisibilityBadge from '@/components/VisibilityBadge'
import { formatDueDate, isOverdueDueDate } from '@/lib/documentDueDates'
import { getDocumentDisplayDescription, getDocumentDisplayTitle } from '@/lib/documentDisplay'
import Skeleton from '@/components/Skeleton'
import type { DocumentListResponse, DocumentStatus, DocumentVisibility } from '@/types'

type VisibilityChangeRequest = {
  id: number
  currentVisibility: DocumentVisibility
  nextVisibility: DocumentVisibility
  ifMatch: string
  title: string
}

type DocumentsTableProps = {
  data: DocumentListResponse | undefined
  isLoading: boolean
  isAdmin: boolean
  isManager: boolean
  showDeleted: boolean
  page: number
  visibilityOverrides: Record<number, DocumentVisibility>
  selectedDocumentIds: number[]
  onToggleDocumentSelection: (documentId: number) => void
  onToggleAllVisibleDocuments: () => void
  onArchiveOrRestore: (id: number, title: string, status: DocumentStatus) => void
  onDelete: (id: number, title: string) => void
  onRestoreDeleted: (id: number, title: string) => void
  onPurgeDeleted: (id: number, title: string) => void
  onVisibilityChange: (change: VisibilityChangeRequest) => void
  onPageChange: (nextPage: number) => void
}

export function DocumentsTable({
  data,
  isLoading,
  isAdmin,
  isManager,
  showDeleted,
  page,
  visibilityOverrides,
  selectedDocumentIds,
  onToggleDocumentSelection,
  onToggleAllVisibleDocuments,
  onArchiveOrRestore,
  onDelete,
  onRestoreDeleted,
  onPurgeDeleted,
  onVisibilityChange,
  onPageChange,
}: DocumentsTableProps) {
  const canSelectRows = isManager && !showDeleted
  const currentPageIds = data?.items.map((document) => document.id) ?? []
  const areAllVisibleDocumentsSelected =
    currentPageIds.length > 0 && currentPageIds.every((documentId) => selectedDocumentIds.includes(documentId))

  return (
    <div className="admin-table-shell">
      <div className="admin-table-scroll">
        <table className="admin-table" aria-label="Documents list">
          <caption className="sr-only">
            Documents list showing title, status, visibility, category, and document actions.
          </caption>
          <thead className="admin-table-head">
            <tr>
              {canSelectRows ? (
                <th className="w-12">
                  <input
                    type="checkbox"
                    checked={areAllVisibleDocumentsSelected}
                    onChange={() => onToggleAllVisibleDocuments()}
                    aria-label="Select all visible documents"
                  />
                </th>
              ) : null}
              <th className="w-[40%]">Document</th>
              <th className="w-[12%]">Status</th>
              <th>Visibility</th>
              <th>Category</th>
              <th>Created</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr className="admin-table-row">
                <td colSpan={canSelectRows ? 7 : 6} className="px-5 py-10 text-center text-slate-500">
                  <div className="space-y-3">
                    <Skeleton className="mx-auto h-4 w-48" />
                    <Skeleton className="mx-auto h-4 w-40" />
                    <Skeleton className="mx-auto h-4 w-44" />
                  </div>
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr className="admin-table-row">
                <td colSpan={canSelectRows ? 7 : 6} className="px-5 py-10 text-center text-slate-500">
                  <div className="flex flex-col items-center gap-2">
                    <FileQuestion className="w-8 h-8 text-slate-300" />
                    <span>No documents found</span>
                  </div>
                </td>
              </tr>
            ) : (
              data?.items.map((doc, index) => {
                const documentTitle = getDocumentDisplayTitle(doc.title)
                const documentDescription = getDocumentDisplayDescription(doc.description)

                return (
                  <tr
                    key={doc.id}
                    className="admin-table-row motion-enter-fade"
                    style={{ '--enter-delay': `${Math.min(index, 6) * 25}ms` } as CSSProperties}
                  >
                    {canSelectRows ? (
                      <td className="admin-table-cell w-12">
                        <input
                          type="checkbox"
                          checked={selectedDocumentIds.includes(doc.id)}
                          onChange={() => onToggleDocumentSelection(doc.id)}
                          aria-label={`Select ${documentTitle}`}
                        />
                      </td>
                    ) : null}
                    <th scope="row" className="admin-table-cell w-[40%]">
                      <div className="flex items-start justify-between gap-3">
                        {showDeleted ? (
                          <div className="block min-w-0">
                            <div
                              className="max-w-[40rem] text-[0.95rem] font-semibold leading-snug text-slate-900 [overflow-wrap:anywhere]"
                              title={documentTitle}
                            >
                              {documentTitle}
                            </div>
                            <div className="mt-1 text-sm text-slate-500">{doc.document_number}</div>
                            <p className="mt-1 max-w-[38rem] whitespace-pre-wrap text-sm leading-6 text-slate-500 line-clamp-2 [overflow-wrap:anywhere]">
                              {documentDescription}
                            </p>
                            {doc.due_date ? (
                              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                <span>Due {formatDueDate(doc.due_date)}</span>
                                {isOverdueDueDate(doc.due_date) ? (
                                  <span className="rounded-full bg-amber-50 px-2 py-0.5 font-semibold text-amber-700">
                                    Overdue
                                  </span>
                                ) : null}
                              </div>
                            ) : null}
                            {showDeleted && (doc.deleted_at || doc.purge_at) ? (
                              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-rose-600">
                                {doc.deleted_at ? (
                                  <span>Deleted {new Date(doc.deleted_at).toLocaleDateString()}</span>
                                ) : null}
                                {doc.purge_at ? (
                                  <span>Purge {new Date(doc.purge_at).toLocaleDateString()}</span>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <Link to={`/documents/${doc.id}/fullscreen`} className="block min-w-0 hover:text-sky-700">
                            <div
                              className="max-w-[40rem] text-[0.95rem] font-semibold leading-snug text-slate-900 [overflow-wrap:anywhere]"
                              title={documentTitle}
                            >
                              {documentTitle}
                            </div>
                            <div className="mt-1 text-sm text-slate-500">{doc.document_number}</div>
                            <p className="mt-1 max-w-[38rem] whitespace-pre-wrap text-sm leading-6 text-slate-500 line-clamp-2 [overflow-wrap:anywhere]">
                              {documentDescription}
                            </p>
                            {doc.due_date ? (
                              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                <span>Due {formatDueDate(doc.due_date)}</span>
                                {isOverdueDueDate(doc.due_date) ? (
                                  <span className="rounded-full bg-amber-50 px-2 py-0.5 font-semibold text-amber-700">
                                    Overdue
                                  </span>
                                ) : null}
                              </div>
                            ) : null}
                          </Link>
                        )}
                        {!showDeleted ? (
                          <BookmarkToggleButton
                            documentId={doc.id}
                            documentTitle={documentTitle}
                            showLabel={false}
                          />
                        ) : null}
                      </div>
                    </th>
                    <td className="admin-table-cell w-[12%]">
                      <span
                        className={`pill whitespace-nowrap ${
                          doc.status === 'active'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : doc.status === 'approved'
                              ? 'bg-sky-50 text-sky-700 border-sky-200'
                              : doc.status === 'draft'
                                ? 'bg-amber-50 text-amber-700 border-amber-200'
                                : doc.status === 'pending_review'
                                  ? 'bg-purple-50 text-purple-700 border-purple-200'
                                  : 'bg-slate-100 text-slate-600 border-slate-200'
                        }`}
                      >
                        {doc.status === 'active'
                          ? 'Published'
                          : doc.status === 'approved'
                            ? 'Approved'
                            : doc.status}
                      </span>
                    </td>
                    <td className="admin-table-cell">
                      {(() => {
                        const effectiveVisibility = visibilityOverrides[doc.id] || doc.visibility || 'internal'
                        return isManager && !showDeleted ? (
                          <div className="space-y-1.5">
                            <select
                              value={effectiveVisibility}
                              aria-label={`Visibility for ${documentTitle}`}
                              onChange={(event) =>
                                onVisibilityChange({
                                  id: doc.id,
                                  currentVisibility: doc.visibility || 'internal',
                                  nextVisibility: event.target.value as DocumentVisibility,
                                  ifMatch: doc.etag || String(doc.row_version || ''),
                                  title: documentTitle,
                                })
                              }
                              className="select-field min-w-[9.5rem] w-40"
                            >
                              <option value="internal">Internal</option>
                              <option value="public">Public</option>
                              <option value="company">Company</option>
                            </select>
                            {effectiveVisibility === 'company' ? (
                              <Link
                                to={`/documents/${doc.id}?tab=details&manage_companies=1#company-assignments`}
                                className="inline-flex text-xs font-medium text-sky-700 hover:text-sky-800"
                              >
                                Manage companies
                              </Link>
                            ) : null}
                          </div>
                        ) : (
                          <VisibilityBadge visibility={doc.visibility || 'internal'} size="sm" />
                        )
                      })()}
                    </td>
                    <td className="admin-table-cell text-slate-500">{doc.category || '-'}</td>
                    <td className="admin-table-cell whitespace-nowrap text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="admin-table-cell whitespace-nowrap text-right">
                      {showDeleted ? (
                        isAdmin ? (
                          <div className="flex items-center justify-end gap-3">
                            <button
                              type="button"
                              onClick={() => onRestoreDeleted(doc.id, documentTitle)}
                              aria-label={`Restore ${documentTitle}`}
                              className="text-xs font-semibold uppercase tracking-wide text-emerald-600 hover:text-emerald-700"
                            >
                              Restore
                            </button>
                            <button
                              type="button"
                              onClick={() => onPurgeDeleted(doc.id, documentTitle)}
                              aria-label={`Permanently delete ${documentTitle}`}
                              className="text-xs font-semibold uppercase tracking-wide text-rose-600 hover:text-rose-700"
                            >
                              Purge
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">-</span>
                        )
                      ) : isManager ? (
                        <div className="flex items-center justify-end gap-3">
                          <button
                            type="button"
                            onClick={() => onArchiveOrRestore(doc.id, documentTitle, doc.status)}
                            aria-label={`${doc.status === 'archived' ? 'Restore' : 'Archive'} ${documentTitle}`}
                            className={`text-xs font-semibold uppercase tracking-wide ${
                              doc.status === 'archived'
                                ? 'text-emerald-600 hover:text-emerald-700'
                                : 'text-amber-600 hover:text-amber-700'
                            }`}
                          >
                            {doc.status === 'archived' ? 'Restore' : 'Archive'}
                          </button>
                          <button
                            type="button"
                            onClick={() => onDelete(doc.id, documentTitle)}
                            aria-label={`Delete ${documentTitle}`}
                            className="text-xs font-semibold uppercase tracking-wide text-rose-600 hover:text-rose-700"
                          >
                            Delete
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">-</span>
                      )}
                    </td>
                  </tr>
                )
              }))
            }
          </tbody>
        </table>
      </div>

      {data && data.total_pages > 1 ? (
        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
          <div className="text-base text-slate-600 font-medium">
            Page {data.page} of {data.total_pages} <span className="text-sm font-normal text-slate-400">({data.total} total)</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(Math.max(1, page - 1))}
              disabled={page === 1}
              className="btn-ghost disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(Math.min(data.total_pages, page + 1))}
              disabled={page === data.total_pages}
              className="btn-ghost disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
