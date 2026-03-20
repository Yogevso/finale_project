import { useState } from 'react'
import { Calendar } from 'lucide-react'
import type { TimeGranularity } from '@/types'

interface DateRangePickerProps {
  startDate: string
  endDate: string
  granularity: TimeGranularity
  onStartDateChange: (date: string) => void
  onEndDateChange: (date: string) => void
  onGranularityChange: (granularity: TimeGranularity) => void
}

export function DateRangePicker({
  startDate,
  endDate,
  granularity,
  onStartDateChange,
  onEndDateChange,
  onGranularityChange,
}: DateRangePickerProps) {
  const [showPresets, setShowPresets] = useState(false)

  const presets = [
    { label: 'Last 7 days', days: 7 },
    { label: 'Last 30 days', days: 30 },
    { label: 'Last 90 days', days: 90 },
    { label: 'This year', days: 365 },
  ]

  const applyPreset = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - days)
    
    onStartDateChange(start.toISOString().split('T')[0])
    onEndDateChange(end.toISOString().split('T')[0])
    setShowPresets(false)
  }

  return (
    <div className="surface-card flex flex-wrap items-center gap-4 rounded-2xl p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-2">
        <Calendar className="h-5 w-5 text-slate-400 dark:text-slate-500" />
        <span className="helper-copy font-medium uppercase tracking-wide text-slate-700 dark:text-slate-200">Date range</span>
      </div>
      
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="input-field py-1.5"
        />
        <span className="text-slate-500 dark:text-slate-400">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="input-field py-1.5"
        />
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={() => setShowPresets(!showPresets)}
          className="btn-ghost table-action-btn"
        >
          Quick Select
        </button>
        {showPresets && (
          <div className="dropdown-menu absolute left-0 top-full z-10 mt-1 min-w-[11rem]">
            {presets.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => applyPreset(preset.days)}
                className="dropdown-item block w-full first:rounded-t-xl last:rounded-b-xl"
              >
                {preset.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <span className="helper-copy font-medium uppercase tracking-wide text-slate-700 dark:text-slate-200">Group by</span>
        <select
          value={granularity}
          onChange={(e) => onGranularityChange(e.target.value as TimeGranularity)}
          className="select-field py-1.5"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
    </div>
  )
}
