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
  MessageSquareText,
} from 'lucide-react'
import PageHeader from '@/components/PageHeader'
import { CardSkeleton } from '@/components/skeletons'
import { EmptyState } from '@/components/EmptyState'
import { ErrorState } from '@/components/ErrorState'
import { FormField, SearchInput, SubmitButton, TextArea } from '@/components/form'
import type { CannedResponse } from '@/types/chat'

export default function CannedResponsesPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [editItem, setEditItem] = useState<CannedResponse | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
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
    <div className="page-stack">
      <PageHeader
        title="Canned Responses"
        subtitle="Manage reusable reply templates for support tickets"
        actions={
          <button
            type="button"
            onClick={() => {
              setEditItem(null)
              setShowCreate(true)
            }}
            className="btn-primary table-action-btn inline-flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            New Template
          </button>
        }
      />

      <div className="space-y-4">
        {/* Toolbar */}
        <div className="surface-card flex flex-wrap items-center gap-3 rounded-2xl p-4">
          <SearchInput
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates..."
            wrapperClassName="min-w-[200px] max-w-xs flex-1"
          />
          {categories.length > 0 && (
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="select-field max-w-[220px] dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          )}
        </div>

        {/* Cards grid */}
        {isLoading ? (
          <CardSkeleton count={6} />
        ) : isError ? (
          <ErrorState
            title="Templates could not be loaded"
            message="The canned response library is unavailable right now."
            onRetry={() => void refetch()}
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<MessageSquareText className="h-8 w-8" aria-hidden="true" />}
            title="No canned responses yet"
            description="Create your first reusable template to speed up support replies."
            action={{
              label: 'Create first template',
              onClick: () => { setEditItem(null); setShowCreate(true) },
            }}
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="surface-card group rounded-2xl p-4 transition-shadow hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="card-title line-clamp-1">{item.title}</h3>
                  <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      type="button"
                      onClick={() => { setEditItem(item); setShowCreate(true) }}
                      className="btn-icon h-8 w-8 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                      title="Edit"
                      aria-label={`Edit ${item.title}`}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm('Delete this template?')) deleteMutation.mutate(item.id)
                      }}
                      className="btn-icon h-8 w-8 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40"
                      title="Delete"
                      aria-label={`Delete ${item.title}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                {item.category && (
                  <span className="pill mt-1 inline-block text-[10px]">
                    {item.category}
                  </span>
                )}
                <p className="body-copy mt-2 line-clamp-3 whitespace-pre-wrap">{item.content}</p>
                <p className="helper-copy mt-2">
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
  const [titleError, setTitleError] = useState('')
  const [contentError, setContentError] = useState('')

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
    let hasError = false
    setTitleError('')
    setContentError('')

    if (!title.trim()) {
      setTitleError('Title is required.')
      hasError = true
    } else if (title.trim().length > 80) {
      setTitleError('Title must be 80 characters or fewer.')
      hasError = true
    }

    if (!content.trim()) {
      setContentError('Content is required.')
      hasError = true
    }

    if (hasError) {
      return
    }

    if (item) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  const pending = createMutation.isPending || updateMutation.isPending

  return (
    <div className="modal-overlay flex items-center justify-center px-4">
      <div className="modal-content w-full max-w-lg dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-800">
          <h3 className="section-title text-base">
            {item ? 'Edit Template' : 'New Template'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="btn-icon h-9 w-9 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            aria-label="Close template editor"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-4 p-6">
          <FormField label="Title" htmlFor="template-title" error={titleError} required>
            <input
              id="template-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Welcome greeting"
              className="input-field dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
              maxLength={80}
            />
          </FormField>
          <FormField label="Category" htmlFor="template-category" hint="Optional grouping, for example Billing or Greetings.">
            <input
              id="template-category"
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. Greetings, Billing, Technical"
              className="input-field dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
            />
          </FormField>
          <TextArea
            label="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Hello {{customer_name}}, thank you for reaching out..."
            rows={5}
            error={contentError}
            hint="Supports {{customer_name}}, {{ticket_id}}, and {{agent_name}}."
            required
          />
        </div>
        <div className="flex justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-slate-800">
          <SubmitButton
            onClick={onClose}
            type="button"
            variant="secondary"
          >
            Cancel
          </SubmitButton>
          <SubmitButton
            onClick={handleSave}
            type="button"
            disabled={pending || !title.trim() || !content.trim()}
            isLoading={pending}
            loadingText="Saving..."
          >
            {item ? 'Update' : 'Create'}
          </SubmitButton>
        </div>
      </div>
    </div>
  )
}
