import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import AvatarUpload from '@/components/AvatarUpload'
import NotificationPreferences from '@/components/NotificationPreferences'
import PageHeader from '@/components/PageHeader'
import ProfileSettingsNav from '@/components/ProfileSettingsNav'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { useToast } from '@/lib/toast'

export default function ProfileSettingsPage() {
  const { user, refreshUser } = useAuth()
  const toast = useToast()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [timezone, setTimezone] = useState(user?.timezone || 'UTC')
  const [timezoneSearch, setTimezoneSearch] = useState('')
  const [locale, setLocale] = useState(user?.locale || 'en')

  const localeOptions = [
    { value: 'en', label: 'English' },
    { value: 'he', label: 'Hebrew' },
    { value: 'fr', label: 'French' },
    { value: 'de', label: 'German' },
  ] as const

  useEffect(() => {
    setFullName(user?.full_name || '')
    setTimezone(user?.timezone || 'UTC')
    setLocale(user?.locale || 'en')
  }, [user?.full_name, user?.timezone, user?.locale])

  const timezoneOptions = useMemo(() => {
    const intlWithSupportedValues = Intl as unknown as {
      supportedValuesOf?: (key: 'timeZone') => string[]
    }
    const availableTimezones = intlWithSupportedValues.supportedValuesOf
      ? intlWithSupportedValues.supportedValuesOf('timeZone')
      : ['UTC']
    const search = timezoneSearch.trim().toLowerCase()

    const filtered = search
      ? availableTimezones.filter((zone) => zone.toLowerCase().includes(search))
      : availableTimezones

    if (timezone && !filtered.includes(timezone)) {
      return [timezone, ...filtered]
    }
    return filtered
  }, [timezone, timezoneSearch])

  const updateProfileMutation = useMutation({
    mutationFn: (payload: { full_name: string; timezone: string; locale: string }) =>
      api.updateMyProfile({
        full_name: payload.full_name,
        timezone: payload.timezone,
        locale: payload.locale,
      }),
    onSuccess: async () => {
      await refreshUser()
      toast.success('Profile updated')
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to update profile'
      toast.error('Profile update failed', message)
    },
  })

  const replayTours = () => {
    window.localStorage.removeItem('tour-completed-documents-page')
    window.localStorage.removeItem('tour-completed-document-detail')
    toast.success('Tours reset', 'Visit Documents or a document detail page to replay the tour.')
  }

  if (!user) {
    return (
      <div className="surface-card rounded-2xl p-6 text-slate-600">
        Unable to load user profile.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Profile Settings"
        subtitle="Manage your profile information and personal preferences."
      />

      <ProfileSettingsNav />

      <div className="surface-card rounded-2xl p-6 space-y-5">
        <h3 className="text-lg font-display font-semibold text-slate-900">Profile</h3>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className="input-field"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Username <span className="text-xs text-slate-400 font-normal">(read-only)</span></label>
            <input
              type="text"
              value={user.username}
              readOnly
              className="input-field bg-slate-100 text-slate-500 cursor-default"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Email <span className="text-xs text-slate-400 font-normal">(read-only)</span></label>
            <input type="email" value={user.email} readOnly className="input-field bg-slate-100 text-slate-500 cursor-default" />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Role <span className="text-xs text-slate-400 font-normal">(read-only)</span></label>
            <input
              type="text"
              value={user.role.replace('_', ' ')}
              readOnly
              className="input-field bg-slate-100 text-slate-500 capitalize cursor-default"
            />
          </div>

          <div className="space-y-1 md:col-span-2">
            <label className="text-sm font-medium text-slate-700">Search Timezone</label>
            <input
              type="search"
              value={timezoneSearch}
              onChange={(event) => setTimezoneSearch(event.target.value)}
              placeholder="Search timezones..."
              className="input-field"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Timezone</label>
            <select
              value={timezone}
              onChange={(event) => { setTimezone(event.target.value); setTimezoneSearch('') }}
              className="select-field"
            >
              {timezoneOptions.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Locale</label>
            <select
              value={locale}
              onChange={(event) => setLocale(event.target.value)}
              className="select-field"
            >
              {localeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          className="btn-primary disabled:cursor-not-allowed"
          disabled={
            updateProfileMutation.isPending ||
            fullName.trim().length === 0 ||
            timezone.trim().length === 0 ||
            locale.trim().length === 0
          }
          onClick={() =>
            updateProfileMutation.mutate({
              full_name: fullName.trim(),
              timezone: timezone.trim(),
              locale: locale.trim(),
            })
          }
        >
          {updateProfileMutation.isPending ? 'Saving...' : 'Save Profile'}
        </button>
      </div>

      <AvatarUpload
        currentAvatarUrl={user.avatar_url}
        onUploaded={() => {
          void refreshUser()
        }}
      />

      <NotificationPreferences
        initialPreferences={user.notification_preferences}
        onUpdated={() => {
          void refreshUser()
        }}
      />

      <div className="surface-card rounded-2xl p-6 space-y-3">
        <h3 className="text-lg font-display font-semibold text-slate-900">Product Tour</h3>
        <p className="text-sm text-slate-600">
          Replay onboarding tours for the documents list and document detail screens.
        </p>
        <button type="button" className="btn-secondary" onClick={replayTours}>
          Replay tour
        </button>
      </div>
    </div>
  )
}
