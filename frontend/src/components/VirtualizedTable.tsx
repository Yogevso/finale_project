import { useRef, type Key, type ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

interface VirtualizedTableColumn {
  header: ReactNode
  headerClassName?: string
}

interface VirtualizedTableProps<T> {
  items: T[]
  columns: VirtualizedTableColumn[]
  gridTemplateColumns: string
  rowKey: (item: T, index: number) => Key
  renderRow: (item: T, index: number) => ReactNode
  ariaLabel?: string
  estimateRowHeight?: number
  overscan?: number
  maxHeightClassName?: string
  tableClassName?: string
  getRowClassName?: (item: T, index: number) => string
  onRowClick?: (item: T, index: number) => void
}

export function VirtualizedTable<T>({
  items,
  columns,
  gridTemplateColumns,
  rowKey,
  renderRow,
  ariaLabel,
  estimateRowHeight = 72,
  overscan = 8,
  maxHeightClassName = 'max-h-[36rem]',
  tableClassName = 'min-w-full',
  getRowClassName,
  onRowClick,
}: VirtualizedTableProps<T>) {
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateRowHeight,
    overscan,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const fallbackRows = items.map((_, index) => ({
    index,
    start: index * estimateRowHeight,
  }))
  const renderedRows = virtualRows.length > 0 ? virtualRows : fallbackRows
  const totalHeight =
    virtualRows.length > 0 ? rowVirtualizer.getTotalSize() : items.length * estimateRowHeight

  return (
    <div className="admin-table-shell overflow-hidden">
      <div className="admin-table-scroll">
        <div
          role="table"
          aria-label={ariaLabel}
          className={['admin-table', tableClassName].filter(Boolean).join(' ')}
        >
          <div role="rowgroup" className="admin-table-head">
            <div role="row" className="grid" style={{ gridTemplateColumns }}>
              {columns.map((column, index) => (
                <div
                  key={index}
                  role="columnheader"
                  className={[
                    'px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-widest text-slate-500 border-b border-slate-200 dark:border-slate-800 dark:text-slate-400',
                    column.headerClassName ?? '',
                  ].filter(Boolean).join(' ')}
                >
                  {column.header}
                </div>
              ))}
            </div>
          </div>

          <div ref={scrollRef} className={['overflow-y-auto', maxHeightClassName].join(' ')}>
            <div
              role="rowgroup"
              className="relative"
              style={{ height: `${totalHeight}px` }}
            >
              {renderedRows.map((virtualRow) => {
                const item = items[virtualRow.index]

                return (
                  <div
                    key={rowKey(item, virtualRow.index)}
                    role="row"
                  className={[
                      'admin-table-row absolute inset-x-0',
                      virtualRow.index % 2 === 1 ? 'bg-slate-50/60 dark:bg-slate-900/40' : '',
                      onRowClick ? 'cursor-pointer' : '',
                      getRowClassName?.(item, virtualRow.index) ?? '',
                    ].filter(Boolean).join(' ')}
                    style={{ transform: `translateY(${virtualRow.start}px)` }}
                    tabIndex={onRowClick ? 0 : undefined}
                    onClick={onRowClick ? () => onRowClick(item, virtualRow.index) : undefined}
                    onKeyDown={
                      onRowClick
                        ? (event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              onRowClick(item, virtualRow.index)
                            }
                          }
                        : undefined
                    }
                  >
                    <div className="grid" style={{ gridTemplateColumns }}>
                      {renderRow(item, virtualRow.index)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
