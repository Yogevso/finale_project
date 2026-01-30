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
    <div className="flex flex-wrap items-center gap-4 bg-white rounded-xl shadow p-4">
      <div className="flex items-center gap-2">
        <Calendar className="w-5 h-5 text-slate-400" />
        <span className="text-sm font-medium text-slate-700">Date Range:</span>
      </div>
      
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        />
        <span className="text-slate-500">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        />
      </div>

      <div className="relative">
        <button
          onClick={() => setShowPresets(!showPresets)}
          className="px-3 py-1.5 text-sm text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200"
        >
          Quick Select
        </button>
        {showPresets && (
          <div className="absolute top-full mt-1 left-0 bg-white border border-slate-200 rounded-xl shadow-lg z-10">
            {presets.map((preset) => (
              <button
                key={preset.label}
                onClick={() => applyPreset(preset.days)}
                className="block w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 first:rounded-t-xl last:rounded-b-xl"
              >
                {preset.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <span className="text-sm font-medium text-slate-700">Group by:</span>
        <select
          value={granularity}
          onChange={(e) => onGranularityChange(e.target.value as TimeGranularity)}
          className="px-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
    </div>
  )
}
