/**
 * CannedResponsesPage — manage reusable reply templates for support (X1-104)
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import {
  Plus,
  Pencil,
  Trash2,
  X,
  Search,
  MessageSquareText,
} from 'lucide-react'
import PageHeader from '@/components/PageHeader'
import type { CannedResponse } from '@/types/chat'

export default function CannedResponsesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [editItem, setEditItem] = useState<CannedResponse | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['cannedResponses', search, categoryFilter],
    queryFn: () =>
      api.getCannedResponses({
        search: search || undefined,
        category: categoryFilter || undefined,
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteCannedResponse(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cannedResponses'] }),
  })

  const items = data?.items ?? []

  // Collect unique categories for filter
  const categories = [...new Set(items.map((i) => i.category).filter(Boolean))] as string[]

  return (
    <div className="space-y-4">
      <PageHeader title="Canned Responses" subtitle="Manage reusable reply templates for support tickets" />

      <div className="mx-4 space-y-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search templates..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          {categories.length > 0 && (
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => { setEditItem(null); setShowCreate(true) }}
            className="ml-auto flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" /> New Template
          </button>
        </div>

        {/* Cards grid */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600" />
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 py-12 text-center">
            <MessageSquareText className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 text-sm font-medium text-gray-500">No canned responses yet</p>
            <p className="mt-1 text-xs text-gray-400">Create your first template to speed up support replies</p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="group rounded-xl border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-gray-900 line-clamp-1">{item.title}</h3>
                  <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      onClick={() => { setEditItem(item); setShowCreate(true) }}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      title="Edit"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('Delete this template?')) deleteMutation.mutate(item.id)
                      }}
                      className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                {item.category && (
                  <span className="mt-1 inline-block rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">
                    {item.category}
                  </span>
                )}
                <p className="mt-2 text-xs text-gray-600 line-clamp-3 whitespace-pre-wrap">{item.content}</p>
                <p className="mt-2 text-[10px] text-gray-400">
                  {item.creator_name && <span>by {item.creator_name} · </span>}
                  {formatDistanceToNow(new Date(item.updated_at), { addSuffix: true })}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create / Edit modal */}
      {showCreate && (
        <CannedResponseModal
          item={editItem}
          onClose={() => { setShowCreate(false); setEditItem(null) }}
        />
      )}
    </div>
  )
}

/* ---- Create / Edit Modal ---- */

function CannedResponseModal({
  item,
  onClose,
}: {
  item: CannedResponse | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(item?.title ?? '')
  const [content, setContent] = useState(item?.content ?? '')
  const [category, setCategory] = useState(item?.category ?? '')

  const createMutation = useMutation({
    mutationFn: () =>
      api.createCannedResponse({
        title,
        content,
        category: category || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cannedResponses'] })
      onClose()
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updateCannedResponse(item!.id, {
        title,
        content,
        category: category || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cannedResponses'] })
      onClose()
    },
  })

  const handleSave = () => {
    if (!title.trim() || !content.trim()) return
    if (item) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const pending = createMutation.isPending || updateMutation.isPending

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h3 className="text-sm font-semibold text-gray-900">
            {item ? 'Edit Template' : 'New Template'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-4 p-6">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Welcome greeting"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Category (optional)</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. Greetings, Billing, Technical"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">
              Content
              <span className="ml-1 font-normal text-gray-400">
                (supports {'{{customer_name}}'}, {'{{ticket_id}}'}, {'{{agent_name}}'})
              </span>
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Hello {{customer_name}}, thank you for reaching out..."
              rows={5}
              className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={pending || !title.trim() || !content.trim()}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {pending ? 'Saving...' : item ? 'Update' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}
