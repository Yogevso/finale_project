import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Sparkles, Tag, X } from 'lucide-react'
import { api } from '@/lib/api'
import { queryKeys } from '@/lib/queryKeys'
import { EmptyState } from '@/components/EmptyState'

type TagEditorProps = {
  tags: string[]
  canEdit: boolean
  isSaving?: boolean
  onSave: (tags: string[]) => void
  maxTags?: number
}

function normalizeTagValue(value: string) {
  return value.trim().replace(/\s+/g, ' ')
}

function mergeTags(existingTags: string[], nextTag: string) {
  const normalizedNextTag = normalizeTagValue(nextTag)
  if (!normalizedNextTag) {
    return existingTags
  }
  const existingLookup = new Set(existingTags.map((tag) => tag.toLowerCase()))
  if (existingLookup.has(normalizedNextTag.toLowerCase())) {
    return existingTags
  }
  return [...existingTags, normalizedNextTag]
}

export default function TagEditor({
  tags,
  canEdit,
  isSaving = false,
  onSave,
  maxTags = 20,
}: TagEditorProps) {
  const [draftTag, setDraftTag] = useState('')
  const tagSuggestionsQuery = useQuery({
    queryKey: queryKeys.documents.tags(draftTag, 12),
    queryFn: () => api.getDocumentTags(draftTag, 12),
    enabled: canEdit,
  })

  const addTag = (nextTag: string) => {
    if (tags.length >= maxTags) return
    const nextTags = mergeTags(tags, nextTag)
    if (nextTags !== tags) {
      onSave(nextTags)
    }
    setDraftTag('')
  }

  const removeTag = (tagToRemove: string) => {
    onSave(tags.filter((tag) => tag.toLowerCase() !== tagToRemove.toLowerCase()))
  }

  const availableSuggestions = (tagSuggestionsQuery.data ?? []).filter(
    (suggestion) => !tags.some((tag) => tag.toLowerCase() === suggestion.toLowerCase()),
  )

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {tags.length > 0 ? (
          tags.map((tagValue) => (
            <span
              key={tagValue}
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700"
            >
              <Tag className="h-3.5 w-3.5" />
              {tagValue}
              {canEdit ? (
                <button
                  type="button"
                  onClick={() => removeTag(tagValue)}
                  disabled={isSaving}
                  className="text-slate-400 hover:text-slate-700"
                  title={`Remove ${tagValue}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              ) : null}
            </span>
          ))
        ) : (
          <EmptyState
            size="compact"
            title="No tags added yet"
            description={canEdit ? 'Add tags to improve discoverability and filtering.' : undefined}
            icon={<Tag className="h-5 w-5" aria-hidden="true" />}
          />
        )}
      </div>

      {canEdit ? (
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={draftTag}
              onChange={(event) => setDraftTag(event.target.value)}
              onKeyDown={(event) => {
                if (event.key !== 'Enter' && event.key !== ',') {
                  return
                }
                event.preventDefault()
                addTag(draftTag)
              }}
              placeholder={tags.length >= maxTags ? `Maximum ${maxTags} tags reached` : 'Add a tag and press Enter'}
              className="input-field flex-1"
              disabled={isSaving || tags.length >= maxTags}
            />
            <button
              type="button"
              onClick={() => addTag(draftTag)}
              disabled={isSaving || normalizeTagValue(draftTag).length === 0 || tags.length >= maxTags}
              className="btn-primary whitespace-nowrap disabled:opacity-60"
            >
              Add tag
            </button>
          </div>
          <p className="text-xs text-slate-400">{tags.length}/{maxTags} tags used</p>

          {availableSuggestions.length > 0 ? (
            <div className="relative z-10 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                <Sparkles className="h-3.5 w-3.5" />
                Suggestions
              </span>
              {availableSuggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => addTag(suggestion)}
                  disabled={isSaving}
                  className="rounded-full border border-blue-200 bg-white px-3 py-1 text-sm text-blue-700 transition-colors hover:bg-blue-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
