import { Download, FileSpreadsheet, FileText } from 'lucide-react'
import { useState } from 'react'
import { api } from '@/lib/api'

interface ExportButtonProps {
  exportType: 'overview' | 'engagement' | 'users' | 'content' | 'feedback'
  startDate: string
  endDate: string
}

export function ExportButton({ exportType, startDate, endDate }: ExportButtonProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format: 'csv' | 'pdf') => {
    setExporting(true)
    try {
      const blob = await api.downloadAnalyticsExport(exportType, format, { date_from: startDate, date_to: endDate })
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics-${exportType}-${startDate}-to-${endDate}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setExporting(false)
      setShowDropdown(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={exporting}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
      >
        <Download className="w-4 h-4" />
        {exporting ? 'Exporting...' : 'Export'}
      </button>
      
      {showDropdown && (
        <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-t-lg"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Export as CSV
          </button>
          <button
            onClick={() => handleExport('pdf')}
            className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-b-lg"
          >
            <FileText className="w-4 h-4" />
            Export as PDF
          </button>
        </div>
      )}
    </div>
  )
}
