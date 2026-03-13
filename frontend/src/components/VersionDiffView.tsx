import { useMemo } from 'react'
import { FileDiff, Minus, PencilLine, Plus } from 'lucide-react'
import { parseDocumentHtml } from '@/lib/documentRenderer'
import {
  buildVersionDiffRows,
  summarizeVersionDiff,
  type VersionDiffBlock,
  type VersionDiffRow,
  type VersionDiffStatus,
} from '@/lib/versionDiff'

interface VersionDiffViewProps {
  leftHtml?: string | null
  rightHtml?: string | null
  leftLabel: string
  rightLabel: string
}

const STATUS_META: Record<
  VersionDiffStatus,
  {
    label: string
    containerClassName: string
    badgeClassName: string
    icon: typeof FileDiff
  }
> = {
  unchanged: {
    label: 'Unchanged',
    containerClassName: 'border-slate-200 bg-white',
    badgeClassName: 'bg-slate-100 text-slate-600',
    icon: FileDiff,
  },
  modified: {
    label: 'Changed',
    containerClassName: 'border-amber-200 bg-amber-50/70',
    badgeClassName: 'bg-amber-100 text-amber-700',
    icon: PencilLine,
  },
  added: {
    label: 'Added',
    containerClassName: 'border-emerald-200 bg-emerald-50/80',
    badgeClassName: 'bg-emerald-100 text-emerald-700',
    icon: Plus,
  },
  removed: {
    label: 'Removed',
    containerClassName: 'border-rose-200 bg-rose-50/80',
    badgeClassName: 'bg-rose-100 text-rose-700',
    icon: Minus,
  },
}

function SummaryPill({
  label,
  value,
  className,
}: {
  label: string
  value: number
  className: string
}) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${className}`}>
      <span>{label}</span>
      <span>{value}</span>
    </span>
  )
}

function EmptySide({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-400">
      {label}
    </div>
  )
}

function DiffCard({
  block,
  status,
  emptyLabel,
}: {
  block: VersionDiffBlock | null
  status: VersionDiffStatus
  emptyLabel: string
}) {
  if (!block) {
    return <EmptySide label={emptyLabel} />
  }

  const meta = STATUS_META[status]
  const Icon = meta.icon

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${meta.containerClassName}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${meta.badgeClassName}`}>
          <Icon className="h-3.5 w-3.5" />
          {meta.label}
        </span>
        <span className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
          {block.id}
        </span>
      </div>
      <div className="prose prose-slate max-w-none text-sm">
        {parseDocumentHtml(block.html)}
      </div>
    </div>
  )
}

function DiffRowView({
  row,
  leftLabel,
  rightLabel,
}: {
  row: VersionDiffRow
  leftLabel: string
  rightLabel: string
}) {
  return (
    <article className="grid gap-4 xl:grid-cols-2">
      <DiffCard
        block={row.left}
        status={row.status === 'added' ? 'unchanged' : row.status}
        emptyLabel={`No matching content in ${leftLabel}`}
      />
      <DiffCard
        block={row.right}
        status={row.status === 'removed' ? 'unchanged' : row.status}
        emptyLabel={`No matching content in ${rightLabel}`}
      />
    </article>
  )
}

export default function VersionDiffView({
  leftHtml,
  rightHtml,
  leftLabel,
  rightLabel,
}: VersionDiffViewProps) {
  const rows = useMemo(
    () => buildVersionDiffRows(leftHtml, rightHtml),
    [leftHtml, rightHtml],
  )
  const summary = useMemo(() => summarizeVersionDiff(rows), [rows])

  if (rows.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-slate-500">
        <FileDiff className="mx-auto mb-3 h-10 w-10 text-slate-300" />
        <p className="text-sm">No version content is available to compare.</p>
      </div>
    )
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <SummaryPill
          label="Changed"
          value={summary.modified}
          className="bg-amber-100 text-amber-700"
        />
        <SummaryPill
          label="Added"
          value={summary.added}
          className="bg-emerald-100 text-emerald-700"
        />
        <SummaryPill
          label="Removed"
          value={summary.removed}
          className="bg-rose-100 text-rose-700"
        />
        <SummaryPill
          label="Unchanged"
          value={summary.unchanged}
          className="bg-slate-100 text-slate-600"
        />
      </div>

      <div className="grid gap-4 rounded-2xl border border-slate-200 bg-slate-50/70 p-4 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 xl:grid-cols-2">
        <div>{leftLabel}</div>
        <div>{rightLabel}</div>
      </div>

      <div className="space-y-4">
        {rows.map((row) => (
          <DiffRowView
            key={row.id}
            row={row}
            leftLabel={leftLabel}
            rightLabel={rightLabel}
          />
        ))}
      </div>
    </section>
  )
}
