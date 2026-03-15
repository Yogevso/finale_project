/**
 * ToolCallCard – renders an inline tool-call execution indicator.
 *
 * Shows a spinner while the tool is running, then a success/failure
 * badge with a collapsible result preview.
 */

import { useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronUp, Loader2, XCircle, Wrench } from 'lucide-react'
import type { ToolCall, ToolResult } from '@/types/assistant'

/** Friendly display names for known tools. */
const TOOL_LABELS: Record<string, string> = {
  search_documents: 'Searching documents…',
  get_document: 'Reading document…',
  create_document: 'Creating document…',
  edit_document: 'Editing document…',
  delete_document: 'Deleting document…',
  list_users: 'Listing users…',
  get_user: 'Looking up user…',
  create_user: 'Creating user…',
  deactivate_user: 'Deactivating user…',
  change_user_role: 'Changing user role…',
  get_site_settings: 'Loading settings…',
  update_site_setting: 'Updating setting…',
  create_announcement: 'Creating announcement…',
  list_announcements: 'Loading announcements…',
  list_topics: 'Loading topics…',
  create_topic: 'Creating topic…',
  list_tenants: 'Listing tenants…',
  get_tenant: 'Loading tenant…',
  update_tenant: 'Updating tenant…',
  get_my_profile: 'Loading profile…',
  get_my_permissions: 'Checking permissions…',
  get_help: 'Loading help…',
  search_public_documents: 'Searching public docs…',
  get_document_content: 'Reading document…',
  create_support_ticket: 'Creating support ticket…',
  list_my_tickets: 'Loading tickets…',
  get_ticket_details: 'Loading ticket…',
  submit_feedback: 'Submitting feedback…',
  get_my_feedback: 'Loading feedback…',
}

interface Props {
  toolCall: ToolCall
  result?: ToolResult
}

export default function ToolCallCard({ toolCall, result }: Props) {
  const [expanded, setExpanded] = useState(false)
  const isRunning = !result
  const label = TOOL_LABELS[toolCall.name] ?? `Running ${toolCall.name}…`

  return (
    <div className="my-2 rounded-lg border border-slate-200 bg-slate-50 text-sm">
      {/* Header */}
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        onClick={() => !isRunning && setExpanded(!expanded)}
        disabled={isRunning}
      >
        {isRunning ? (
          <Loader2 className="h-4 w-4 animate-spin text-sky-500" />
        ) : result?.success ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )}

        <Wrench className="h-3.5 w-3.5 text-slate-400" />

        <span className="flex-1 font-medium text-slate-700">
          {isRunning ? label : result?.success ? `${toolCall.name} — done` : `${toolCall.name} — failed`}
        </span>

        {!isRunning && (
          expanded
            ? <ChevronUp className="h-4 w-4 text-slate-400" />
            : <ChevronDown className="h-4 w-4 text-slate-400" />
        )}
      </button>

      {/* Expanded body */}
      {expanded && result && (
        <div className="border-t border-slate-200 px-3 py-2 text-xs text-slate-600">
          {result.error && (
            <p className="mb-1 text-red-600"><strong>Error:</strong> {result.error}</p>
          )}
          <pre className="whitespace-pre-wrap break-words rounded bg-white p-2 font-mono">
            {result.result.slice(0, 2000)}
            {result.result.length > 2000 && '…'}
          </pre>
        </div>
      )}
    </div>
  )
}
