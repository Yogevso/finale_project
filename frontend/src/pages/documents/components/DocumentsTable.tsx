import type { CSSProperties } from 'react'
import { FileQuestion } from 'lucide-react'
import { Link } from 'react-router-dom'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'
import VisibilityBadge from '@/components/VisibilityBadge'
import { formatDueDate, isOverdueDueDate } from '@/lib/documentDueDates'
import { getDocumentDisplayDescription, getDocumentDisplayTitle } from '@/lib/documentDisplay'
import Skeleton from '@/components/Skeleton'
import type { DocumentListResponse, DocumentStatus, DocumentVisibility } from '@/types'
import { formatDocumentDate } from '@/lib/dateUtils'
import { documentStatusDescription, documentStatusLabel, documentStatusTone } from '@/lib/documentStatus'

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
  onArchiveOrRestore: (id: number, title: string, status: DocumentStatus, etag?: string) => void
  onDelete: (id: number, title: string, etag?: string) => void
  onRestoreDeleted: (id: number, title: string, etag?: string) => void
  onPurgeDeleted: (id: number, title: string, etag?: string) => void
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
            Documents list showing title, status, visibility, and document actions.
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
              <th>Created</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr className="admin-table-row">
                <td colSpan={canSelectRows ? 6 : 5} className="px-5 py-10 text-center text-slate-500">
                  <div className="space-y-3">
                    <Skeleton className="mx-auto h-4 w-48" />
                    <Skeleton className="mx-auto h-4 w-40" />
                    <Skeleton className="mx-auto h-4 w-44" />
                  </div>
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr className="admin-table-row">
                <td colSpan={canSelectRows ? 6 : 5} className="px-5 py-10 text-center text-slate-500">
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
                              className="max-w-[40rem] text-[0.95rem] font-semibold leading-snug text-slate-900 [overflow-wrap:break-word]"
                              title={documentTitle}
                            >
                              {documentTitle}
                            </div>
                            <div className="mt-1 text-sm text-slate-500">{doc.document_number}</div>
                            <p className="mt-1 max-w-[38rem] whitespace-pre-wrap text-sm leading-6 text-slate-500 line-clamp-2 [overflow-wrap:break-word]">
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
                                  <span>Deleted {formatDocumentDate(doc.deleted_at)}</span>
                                ) : null}
                                {doc.purge_at ? (
                                  <span>Purge {formatDocumentDate(doc.purge_at)}</span>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <Link to={`/documents/${doc.id}/fullscreen`} className="block min-w-0 hover:text-blue-700">
                            <div
                              className="max-w-[40rem] text-[0.95rem] font-semibold leading-snug text-slate-900 [overflow-wrap:break-word]"
                              title={documentTitle}
                            >
                              {documentTitle}
                            </div>
                            <div className="mt-1 text-sm text-slate-500">{doc.document_number}</div>
                            <p className="mt-1 max-w-[38rem] whitespace-pre-wrap text-sm leading-6 text-slate-500 line-clamp-2 [overflow-wrap:break-word]">
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
                        className={`pill whitespace-nowrap ${documentStatusTone(doc.status)}`}
                        title={documentStatusDescription(doc.status)}
                      >
                        {documentStatusLabel(doc.status)}
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
                              className="select-field select-field--compact"
                            >
                              <option value="internal">Internal</option>
                              <option value="public">Public</option>
                              <option value="company">Company</option>
                            </select>
                            {effectiveVisibility === 'company' ? (
                              <Link
                                to={`/documents/${doc.id}?tab=details&manage_companies=1#company-assignments`}
                                className="inline-flex text-xs font-medium text-blue-700 hover:text-blue-800"
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
                    <td className="admin-table-cell whitespace-nowrap text-slate-500">
                      {formatDocumentDate(doc.created_at)}
                    </td>
                    <td className="admin-table-cell whitespace-nowrap text-right">
                      {showDeleted ? (
                        isAdmin ? (
                          <div className="flex items-center justify-end gap-3">
                            <button
                              type="button"
                              onClick={() => onRestoreDeleted(doc.id, documentTitle, doc.etag)}
                              aria-label={`Restore ${documentTitle}`}
                              className="text-xs font-semibold uppercase tracking-wide text-emerald-700 hover:text-emerald-800 dark:text-emerald-300 dark:hover:text-emerald-200"
                            >
                              Restore
                            </button>
                            <button
                              type="button"
                              onClick={() => onPurgeDeleted(doc.id, documentTitle, doc.etag)}
                              aria-label={`Permanently delete ${documentTitle}`}
                              className="text-xs font-semibold uppercase tracking-wide text-rose-700 hover:text-rose-800 dark:text-rose-300 dark:hover:text-rose-200"
                            >
                              Purge
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400">-</span>
                        )
                      ) : isManager ? (
                        <div className="flex items-center justify-end gap-3">
                          <Link
                            to={`/documents/${doc.id}`}
                            aria-label={`Edit ${documentTitle}`}
                            className="text-xs font-semibold uppercase tracking-wide text-blue-700 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
                          >
                            Edit
                          </Link>
                          <Link
                            to={`/documents/${doc.id}/fullscreen`}
                            aria-label={`View transcript of ${documentTitle}`}
                            className="text-xs font-semibold uppercase tracking-wide text-slate-600 hover:text-slate-800 dark:text-slate-300 dark:hover:text-slate-100"
                          >
                            Transcript
                          </Link>
                          <button
                            type="button"
                            onClick={() => onArchiveOrRestore(doc.id, documentTitle, doc.status, doc.etag)}
                            aria-label={`${doc.status === 'archived' ? 'Restore' : 'Archive'} ${documentTitle}`}
                            className={`text-xs font-semibold uppercase tracking-wide ${
                              doc.status === 'archived'
                                ? 'text-emerald-700 hover:text-emerald-800 dark:text-emerald-300'
                                : 'text-amber-700 hover:text-amber-800 dark:text-amber-300'
                            }`}
                          >
                            {doc.status === 'archived' ? 'Restore' : 'Archive'}
                          </button>
                          <button
                            type="button"
                            onClick={() => onDelete(doc.id, documentTitle, doc.etag)}
                            aria-label={`Delete ${documentTitle}`}
                            className="text-xs font-semibold uppercase tracking-wide text-rose-700 hover:text-rose-800 dark:text-rose-300 dark:hover:text-rose-200"
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
            Page {data.page} of {data.total_pages} <span className="text-sm font-normal text-slate-500 dark:text-slate-400">({data.total} total)</span>
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
