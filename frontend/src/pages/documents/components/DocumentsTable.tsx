import VisibilityBadge from '@/components/VisibilityBadge'
import type { DocumentListResponse, DocumentVisibility } from '@/types'

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
  onDelete: (id: number, title: string) => void
  onVisibilityChange: (change: VisibilityChangeRequest) => void
  onPageChange: (nextPage: number) => void
}

export function DocumentsTable({
  data,
  isLoading,
  isManager,
  page,
  visibilityOverrides,
  onDelete,
  onVisibilityChange,
  onPageChange,
}: DocumentsTableProps) {
  return (
    <div className="admin-table-shell">
      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead className="admin-table-head">
            <tr>
              <th className="w-[40%]">Document</th>
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
                <td colSpan={6} className="px-5 py-10 text-center text-slate-500">
                  Loading...
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr className="admin-table-row">
                <td colSpan={6} className="px-5 py-10 text-center text-slate-500">
                  No documents found
                </td>
              </tr>
            ) : (
              data?.items.map((doc) => (
                <tr key={doc.id} className="admin-table-row">
                  <td className="admin-table-cell w-[40%]">
                    <a href={`/documents/${doc.id}/fullscreen`} className="block hover:text-sky-700">
                      <div className="font-medium text-slate-900">{doc.title}</div>
                      <div className="text-sm text-slate-500">{doc.document_number}</div>
                    </a>
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
                    {isManager ? (
                      <select
                        value={visibilityOverrides[doc.id] || doc.visibility || 'internal'}
                        onChange={(e) =>
                          onVisibilityChange({
                            id: doc.id,
                            currentVisibility: doc.visibility || 'internal',
                            nextVisibility: e.target.value as DocumentVisibility,
                            ifMatch: doc.etag || String(doc.row_version || ''),
                            title: doc.title,
                          })
                        }
                        className="select-field w-40 min-w-[9.5rem]"
                      >
                        <option value="internal">Internal</option>
                        <option value="public">Public</option>
                        <option value="company">Company</option>
                      </select>
                    ) : (
                      <VisibilityBadge visibility={doc.visibility || 'internal'} size="sm" />
                    )}
                  </td>
                  <td className="admin-table-cell text-slate-500">{doc.category || '-'}</td>
                  <td className="admin-table-cell text-slate-500 whitespace-nowrap">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="admin-table-cell text-right whitespace-nowrap">
                    {isManager ? (
                      <button
                        onClick={() => onDelete(doc.id, doc.title)}
                        className="text-rose-600 hover:text-rose-700 font-semibold text-xs uppercase tracking-wide"
                      >
                        Delete
                      </button>
                    ) : (
                      <span className="text-slate-400 text-xs">-</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && data.pages > 1 && (
        <div className="px-5 py-4 border-t border-slate-200 flex items-center justify-between">
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
      )}
    </div>
  )
}
