import { useEffect, useState } from 'react'
import { X, Info, AlertTriangle, CheckCircle } from 'lucide-react'
import { publicApi, type PublicAnnouncement } from '@/lib/publicApi'

const DISMISSED_KEY = 'dismissed_announcements'

function getDismissed(): Set<number> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch {
    return new Set()
  }
}

function dismiss(id: number) {
  const dismissed = getDismissed()
  dismissed.add(id)
  localStorage.setItem(DISMISSED_KEY, JSON.stringify([...dismissed]))
}

const typeConfig: Record<string, { icon: typeof Info; bg: string; border: string; text: string }> = {
  info: { icon: Info, bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800' },
  warning: { icon: AlertTriangle, bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800' },
  success: { icon: CheckCircle, bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800' },
}

export default function AnnouncementBanner() {
  const [announcements, setAnnouncements] = useState<PublicAnnouncement[]>([])
  const [dismissed, setDismissedState] = useState<Set<number>>(getDismissed)

  useEffect(() => {
    publicApi.getAnnouncements().then(setAnnouncements).catch(() => {
      // Announcements are non-critical; log for debugging
      // eslint-disable-next-line no-console
      console.warn('Failed to load announcements')
    })
  }, [])

  const visible = announcements.filter((a) => !dismissed.has(a.id))
  if (visible.length === 0) return null

  function handleDismiss(id: number) {
    dismiss(id)
    setDismissedState(new Set(getDismissed()))
  }

  return (
    <div className="space-y-0">
      {visible.map((a) => {
        const config = typeConfig[a.type] || typeConfig.info
        const Icon = config.icon
        return (
          <div
            key={a.id}
            className={`${config.bg} ${config.border} border-b px-4 py-2.5 flex items-center gap-3`}
          >
            <Icon className={`h-4 w-4 flex-shrink-0 ${config.text}`} />
            <p className={`text-sm flex-1 ${config.text}`}>{a.message}</p>
            <button
              onClick={() => handleDismiss(a.id)}
              className={`p-1 rounded hover:bg-black/5 ${config.text}`}
              aria-label="Dismiss announcement"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
