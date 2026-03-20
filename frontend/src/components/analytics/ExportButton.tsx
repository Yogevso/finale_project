import { Download, FileSpreadsheet } from 'lucide-react'
import { useState } from 'react'
import { api } from '@/lib/api'

interface ExportButtonProps {
  exportType: 'overview' | 'engagement' | 'users' | 'content' | 'feedback'
  startDate: string
  endDate: string
}

export function ExportButton({ exportType, startDate, endDate }: ExportButtonProps) {
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await api.downloadAnalyticsExport(exportType, 'csv', {
        date_from: startDate,
        date_to: endDate,
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics-${exportType}-${startDate}-to-${endDate}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setExporting(false)
    }
  }

  return (
    <button
      type="button"
      onClick={() => void handleExport()}
      disabled={exporting}
      className="btn-secondary table-action-btn flex items-center gap-2 disabled:opacity-50"
    >
      {exporting ? <Download className="w-4 h-4" /> : <FileSpreadsheet className="w-4 h-4" />}
      {exporting ? 'Exporting CSV...' : 'Export CSV'}
    </button>
  )
}
