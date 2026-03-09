import { Link } from 'react-router-dom'
import BookmarkToggleButton from '@/components/BookmarkToggleButton'
import VisibilityBadge from '@/components/VisibilityBadge'
import { formatDueDate, isOverdueDueDate } from '@/lib/documentDueDates'
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
  isManager: boolean
  page: number
  visibilityOverrides: Record<number, DocumentVisibility>
  selectedDocumentIds: number[]
  onToggleDocumentSelection: (documentId: number) => void
  onToggleAllVisibleDocuments: () => void
  onArchiveOrRestore: (id: number, title: string, status: DocumentStatus) => void
  onVisibilityChange: (change: VisibilityChangeRequest) => void
  onPageChange: (nextPage: number) => void
}

export function DocumentsTable({
  data,
  isLoading,
  isManager,
  page,
  visibilityOverrides,
  selectedDocumentIds,
  onToggleDocumentSelection,
  onToggleAllVisibleDocuments,
  onArchiveOrRestore,
  onVisibilityChange,
  onPageChange,
}: DocumentsTableProps) {
  const currentPageIds = data?.items.map((document) => document.id) ?? []
  const areAllVisibleDocumentsSelected =
    currentPageIds.length > 0 && currentPageIds.every((documentId) => selectedDocumentIds.includes(documentId))

  return (
    <div className="admin-table-shell">
      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead className="admin-table-head">
            <tr>
              {isManager ? (
                <th className="w-12">
                  <input
                    type="checkbox"
                    checked={areAllVisibleDocumentsSelected}
                    onChange={() => onToggleAllVisibleDocuments()}
                    aria-label="Select all visible documents"
                  />
                </th>
              ) : null}
              <th className="w-[36%]">Document</th>
              <th className="w-[14%]">Status</th>
              <th>Visibility</th>
              <th>Category</th>
              <th>Created</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr className="admin-table-row">
                <td colSpan={isManager ? 7 : 6} className="px-5 py-10 text-center text-slate-500">
                  <div className="space-y-3">
                    <Skeleton className="mx-auto h-4 w-48" />
                    <Skeleton className="mx-auto h-4 w-40" />
                    <Skeleton className="mx-auto h-4 w-44" />
                  </div>
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr className="admin-table-row">
                <td colSpan={isManager ? 7 : 6} className="px-5 py-10 text-center text-slate-500">
                  No documents found
                </td>
              </tr>
            ) : (
              data?.items.map((doc) => (
                <tr key={doc.id} className="admin-table-row">
                  {isManager ? (
                    <td className="admin-table-cell w-12">
                      <input
                        type="checkbox"
                        checked={selectedDocumentIds.includes(doc.id)}
                        onChange={() => onToggleDocumentSelection(doc.id)}
                        aria-label={`Select ${doc.title}`}
                      />
                    </td>
                  ) : null}
                  <td className="admin-table-cell w-[36%]">
                    <div className="flex items-start justify-between gap-3">
                      <Link to={`/documents/${doc.id}/fullscreen`} className="block hover:text-sky-700">
                        <div className="font-medium text-slate-900">{doc.title}</div>
                        <div className="text-sm text-slate-500">{doc.document_number}</div>
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
                      <BookmarkToggleButton documentId={doc.id} showLabel={false} />
                    </div>
                  </td>
                  <td className="admin-table-cell w-[14%]">
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
                      return isManager ? (
                        <div className="space-y-1.5">
                          <select
                            value={effectiveVisibility}
                            onChange={(event) =>
                              onVisibilityChange({
                                id: doc.id,
                                currentVisibility: doc.visibility || 'internal',
                                nextVisibility: event.target.value as DocumentVisibility,
                                ifMatch: doc.etag || String(doc.row_version || ''),
                                title: doc.title,
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
                              to={`/documents/${doc.id}`}
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
                    {isManager ? (
                      <button
                        onClick={() => onArchiveOrRestore(doc.id, doc.title, doc.status)}
                        className={`text-xs font-semibold uppercase tracking-wide ${
                          doc.status === 'archived'
                            ? 'text-emerald-600 hover:text-emerald-700'
                            : 'text-amber-600 hover:text-amber-700'
                        }`}
                      >
                        {doc.status === 'archived' ? 'Restore' : 'Archive'}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-400">-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && data.pages > 1 ? (
        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4">
          <div className="text-sm text-slate-500">
            Page {data.page} of {data.pages} ({data.total} total)
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
              onClick={() => onPageChange(Math.min(data.pages, page + 1))}
              disabled={page === data.pages}
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
