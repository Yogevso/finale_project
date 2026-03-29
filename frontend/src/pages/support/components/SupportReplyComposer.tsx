import { MessageSquareText, Paperclip, Search, Send, X } from 'lucide-react'

import { SubmitButton, TextArea } from '@/components/form'
import { COMMUNICATION_INPUT_LIMITS } from '@/lib/uiInputRules'
import { CardSkeleton } from '@/components/skeletons'
import type { CannedResponseListResponse } from '@/types/chat'

import { formatSupportFileSize } from '../constants'

interface SupportReplyComposerProps {
  attachmentInputAccept: string
  cannedResponses?: CannedResponseListResponse['items']
  cannedSearch: string
  canSend: boolean
  isCannedLoading: boolean
  isInternal: boolean
  isSending: boolean
  message: string
  messageError: string
  onCannedSearchChange: (value: string) => void
  onInsertCanned: (content: string) => void
  onRemoveSelectedFile: () => void
  onSend: () => void
  onSetInternal: (value: boolean) => void
  onSetMessage: (value: string) => void
  onSetMessageError: (value: string) => void
  onShowCannedChange: (value: boolean) => void
  onSelectedFileChange: (file: File | null) => void
  selectedFile: File | null
  showCanned: boolean
  fileInputRef: React.MutableRefObject<HTMLInputElement | null>
}

export function SupportReplyComposer({
  attachmentInputAccept,
  cannedResponses,
  cannedSearch,
  canSend,
  isCannedLoading,
  isInternal,
  isSending,
  message,
  messageError,
  onCannedSearchChange,
  onInsertCanned,
  onRemoveSelectedFile,
  onSend,
  onSetInternal,
  onSetMessage,
  onSetMessageError,
  onShowCannedChange,
  onSelectedFileChange,
  selectedFile,
  showCanned,
  fileInputRef,
}: SupportReplyComposerProps) {
  return (
    <div className="space-y-2 border-t border-gray-200 p-3 dark:border-slate-800">
      <div className="flex items-center gap-3 text-xs">
        <label className="flex cursor-pointer items-center gap-1.5">
          <input
            type="checkbox"
            checked={isInternal}
            onChange={(event) => onSetInternal(event.target.checked)}
            className="rounded border-gray-300 dark:border-slate-700"
          />
          <span className="font-medium text-amber-700 dark:text-amber-200">Internal note</span>
        </label>
        <div className="relative ml-auto">
          <button
            type="button"
            onClick={() => onShowCannedChange(!showCanned)}
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-2 py-1 text-xs text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            title="Insert canned response"
          >
            <MessageSquareText className="h-3.5 w-3.5" />
            Templates
          </button>
          {showCanned ? (
            <div className="dropdown-menu absolute bottom-8 right-0 z-50 w-80 dark:bg-slate-900">
              <div className="border-b border-gray-100 p-2 dark:border-slate-800">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400 dark:text-slate-500" />
                  <input
                    type="text"
                    placeholder="Search templates..."
                    value={cannedSearch}
                    onChange={(event) => onCannedSearchChange(event.target.value)}
                    className="input-field py-1.5 pl-8 pr-3 text-xs"
                  />
                </div>
              </div>
              <div className="max-h-48 overflow-y-auto p-1">
                {(cannedResponses ?? []).length === 0 ? (
                  isCannedLoading ? (
                    <div className="px-2 py-2">
                      <CardSkeleton count={2} />
                    </div>
                  ) : (
                    <p className="px-3 py-4 text-center text-xs text-gray-400 dark:text-slate-500">
                      No templates found
                    </p>
                  )
                ) : (
                  (cannedResponses ?? []).map((cannedResponse) => (
                    <button
                      key={cannedResponse.id}
                      type="button"
                      onClick={() => onInsertCanned(cannedResponse.content)}
                      className="w-full rounded-lg px-3 py-2 text-left transition-colors hover:bg-sky-50 dark:hover:bg-sky-950/30"
                    >
                      <p className="text-xs font-medium text-gray-900 dark:text-slate-100">
                        {cannedResponse.title}
                      </p>
                      {cannedResponse.category ? (
                        <span className="text-[10px] text-gray-400 dark:text-slate-500">
                          {cannedResponse.category}
                        </span>
                      ) : null}
                      <p className="mt-0.5 line-clamp-2 text-[11px] text-gray-500 dark:text-slate-400">
                        {cannedResponse.content}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {selectedFile ? (
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800/60">
          <Paperclip className="h-4 w-4 shrink-0 text-slate-500 dark:text-slate-300" />
          <span className="min-w-0 flex-1 truncate">{selectedFile.name}</span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {formatSupportFileSize(selectedFile.size)}
          </span>
          <button
            type="button"
            onClick={onRemoveSelectedFile}
            className="btn-icon h-7 w-7"
            aria-label="Remove attachment"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 md:flex-row md:items-end">
        <div className="flex-1">
          <TextArea
            label="Reply"
            value={message}
            onChange={(event) => {
              onSetMessage(event.target.value)
              if (messageError) {
                onSetMessageError('')
              }
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSend()
              }
            }}
            placeholder={
              isInternal ? 'Internal note (not visible to customer)...' : 'Reply to customer...'
            }
            rows={2}
            maxLength={COMMUNICATION_INPUT_LIMITS.supportReply}
            error={messageError}
            required={!selectedFile}
          />
        </div>
        <label className="btn-secondary flex h-10 cursor-pointer items-center justify-center gap-2 px-3 md:h-11">
          <input
            ref={fileInputRef}
            type="file"
            accept={attachmentInputAccept}
            aria-label="Attach a file"
            className="sr-only"
            onChange={(event) => onSelectedFileChange(event.target.files?.[0] ?? null)}
          />
          <Paperclip className="h-4 w-4" />
          Attach file
        </label>
        <SubmitButton
          type="button"
          onClick={onSend}
          disabled={isSending || !canSend}
          isLoading={isSending}
          loadingText="Sending..."
          className="min-w-[9rem]"
        >
          <Send className="h-4 w-4" />
          Send reply
        </SubmitButton>
      </div>
    </div>
  )
}
