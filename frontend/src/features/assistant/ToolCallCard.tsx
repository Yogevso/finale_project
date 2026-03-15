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
  // Phase 10-14 tools
  semantic_search: 'Searching with AI…',
  summarize_document: 'Summarizing document…',
  ask_about_document: 'Analyzing document…',
  analyze_uploaded_file: 'Analyzing file…',
  compare_files: 'Comparing files…',
  compare_versions: 'Comparing versions…',
  get_document_history: 'Loading version history…',
  publish_document: 'Publishing document…',
  get_document_workflow: 'Loading workflow status…',
  list_attachments: 'Loading attachments…',
  get_attachment_info: 'Loading attachment info…',
  get_documents_by_status: 'Filtering documents…',
  get_recent_documents: 'Loading recent documents…',
  get_platform_analytics: 'Loading platform analytics…',
  get_engagement_analytics: 'Analyzing engagement…',
  get_content_analytics: 'Analyzing content…',
  search_audit_logs: 'Searching audit logs…',
  get_user_activity: 'Loading user activity…',
  get_my_notifications: 'Loading notifications…',
  mark_notifications_read: 'Marking notifications read…',
  list_document_comments: 'Loading comments…',
  add_comment: 'Adding comment…',
  resolve_comment: 'Resolving comment…',
  submit_review: 'Submitting review…',
  list_pending_reviews: 'Loading pending reviews…',
  create_invitation: 'Creating invitation…',
  list_invitations: 'Loading invitations…',
  get_active_collaborators: 'Checking collaborators…',
  get_collaboration_history: 'Loading collaboration history…',
}

/** Tool category colors for visual grouping. */
const TOOL_CATEGORY_COLORS: Record<string, string> = {
  analytics: 'border-purple-200 bg-purple-50',
  audit: 'border-amber-200 bg-amber-50',
  collaboration: 'border-teal-200 bg-teal-50',
  rag: 'border-indigo-200 bg-indigo-50',
}

function getToolCategory(name: string): string | null {
  if (name.includes('analytics')) return 'analytics'
  if (name.includes('audit') || name.includes('activity')) return 'audit'
  if (name.includes('collaborat')) return 'collaboration'
  if (['semantic_search', 'summarize_document', 'ask_about_document'].includes(name)) return 'rag'
  return null
}

interface Props {
  toolCall: ToolCall
  result?: ToolResult
}

export default function ToolCallCard({ toolCall, result }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const isRunning = !result
  const label = TOOL_LABELS[toolCall.name] ?? `Running ${toolCall.name}…`
  const category = getToolCategory(toolCall.name)
  const categoryClass = category ? TOOL_CATEGORY_COLORS[category] : 'border-slate-200 bg-slate-50'

  const handleCopy = () => {
    if (result?.result) {
      navigator.clipboard.writeText(result.result).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      })
    }
  }

  return (
    <div className={`my-2 rounded-lg border text-sm ${categoryClass}`}>
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
          <div className="relative">
            <button
              type="button"
              onClick={handleCopy}
              className="absolute right-1 top-1 rounded px-1.5 py-0.5 text-[10px] text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              title="Copy result"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <pre className="whitespace-pre-wrap break-words rounded bg-white p-2 font-mono">
              {result.result.slice(0, 2000)}
              {result.result.length > 2000 && '…'}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
