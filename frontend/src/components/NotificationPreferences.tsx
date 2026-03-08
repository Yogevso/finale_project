import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'

type NotificationPreferencesProps = {
  initialPreferences?: Record<string, boolean>
  onUpdated?: (nextPreferences: Record<string, boolean>) => void
}

const PREFERENCE_OPTIONS = [
  {
    key: 'review_assigned',
    label: 'Review Assigned',
    description: 'Email me when a document is assigned for my review.',
  },
  {
    key: 'document_updated',
    label: 'Document Updated',
    description: 'Email me when tracked documents are updated or published.',
  },
  {
    key: 'mention',
    label: 'Mentions',
    description: 'Email me when someone mentions me in a comment.',
  },
] as const

const DEFAULT_PREFERENCES: Record<string, boolean> = {
  review_assigned: true,
  document_updated: true,
  mention: true,
}

export default function NotificationPreferences({
  initialPreferences,
  onUpdated,
}: NotificationPreferencesProps) {
  const toast = useToast()
  const [preferences, setPreferences] = useState<Record<string, boolean>>({
    ...DEFAULT_PREFERENCES,
    ...(initialPreferences || {}),
  })

  useEffect(() => {
    setPreferences({
      ...DEFAULT_PREFERENCES,
      ...(initialPreferences || {}),
    })
  }, [initialPreferences])

  const saveMutation = useMutation({
    mutationFn: (nextPreferences: Record<string, boolean>) =>
      api.updateMyNotificationPreferences(nextPreferences),
    onSuccess: (savedPreferences) => {
      toast.success('Notification preferences saved')
      onUpdated?.(savedPreferences)
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to save notification preferences'
      toast.error('Failed to save preferences', message)
    },
  })

  const handleToggle = (key: string) => {
    setPreferences((current) => ({
      ...current,
      [key]: !current[key],
    }))
  }

  return (
    <div className="surface-card rounded-2xl p-6 space-y-5">
      <div>
        <h3 className="text-lg font-display font-semibold text-slate-900">Notification Preferences</h3>
        <p className="text-sm text-slate-500 mt-1">Choose which email notifications you want to receive.</p>
      </div>

      <div className="space-y-4">
        {PREFERENCE_OPTIONS.map((option) => (
          <label
            key={option.key}
            className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4"
          >
            <input
              type="checkbox"
              className="mt-1 rounded border-slate-300"
              checked={Boolean(preferences[option.key])}
              onChange={() => handleToggle(option.key)}
            />
            <span className="space-y-1">
              <span className="block text-sm font-medium text-slate-900">{option.label}</span>
              <span className="block text-xs text-slate-500">{option.description}</span>
            </span>
          </label>
        ))}
      </div>

      <button
        type="button"
        className="btn-primary"
        onClick={() => saveMutation.mutate(preferences)}
        disabled={saveMutation.isPending}
      >
        {saveMutation.isPending ? 'Saving...' : 'Save Preferences'}
      </button>
    </div>
  )
}
