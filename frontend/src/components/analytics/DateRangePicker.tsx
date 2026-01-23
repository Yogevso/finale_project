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
    <div className="flex flex-wrap items-center gap-4 bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2">
        <Calendar className="w-5 h-5 text-gray-400" />
        <span className="text-sm font-medium text-gray-700">Date Range:</span>
      </div>
      
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <span className="text-gray-500">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <div className="relative">
        <button
          onClick={() => setShowPresets(!showPresets)}
          className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200"
        >
          Quick Select
        </button>
        {showPresets && (
          <div className="absolute top-full mt-1 left-0 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
            {presets.map((preset) => (
              <button
                key={preset.label}
                onClick={() => applyPreset(preset.days)}
                className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
              >
                {preset.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <span className="text-sm font-medium text-gray-700">Group by:</span>
        <select
          value={granularity}
          onChange={(e) => onGranularityChange(e.target.value as TimeGranularity)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>
    </div>
  )
}
