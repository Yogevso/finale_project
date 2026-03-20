import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import AvatarUpload from '@/components/AvatarUpload'
import NotificationPreferences from '@/components/NotificationPreferences'
import PageHeader from '@/components/PageHeader'
import ProfileSettingsNav from '@/components/ProfileSettingsNav'
import { FormField, SubmitButton } from '@/components/form'
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
  const [fullNameError, setFullNameError] = useState('')

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

  const handleProfileSubmit = (event: React.FormEvent) => {
    event.preventDefault()

    if (!fullName.trim()) {
      setFullNameError('Full name is required')
      return
    }

    setFullNameError('')
    updateProfileMutation.mutate({
      full_name: fullName.trim(),
      timezone: timezone.trim(),
      locale: locale.trim(),
    })
  }

  if (!user) {
    return (
      <div className="surface-card rounded-2xl p-6 text-slate-600 dark:text-slate-300">
        Unable to load user profile.
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        title="Profile Settings"
        subtitle="Manage your profile information and personal preferences."
      />

      <ProfileSettingsNav />

      <form onSubmit={handleProfileSubmit} className="surface-card space-y-6 rounded-2xl p-6">
        <h3 className="section-title">Profile</h3>

        <div className="grid gap-4 md:grid-cols-2">
          <FormField label="Full Name" htmlFor="profile-full-name" required error={fullNameError}>
            <input
              id="profile-full-name"
              type="text"
              value={fullName}
              onChange={(event) => {
                setFullName(event.target.value)
                if (fullNameError) {
                  setFullNameError('')
                }
              }}
              className="input-field"
              aria-invalid={!!fullNameError}
            />
          </FormField>

          <FormField
            label="Username"
            htmlFor="profile-username"
            hint="Read-only"
          >
            <input
              id="profile-username"
              type="text"
              value={user.username}
              readOnly
              className="input-field cursor-default bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
            />
          </FormField>

          <FormField
            label="Email"
            htmlFor="profile-email"
            hint="Read-only"
          >
            <input
              id="profile-email"
              type="email"
              value={user.email}
              readOnly
              className="input-field cursor-default bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
            />
          </FormField>

          <FormField
            label="Role"
            htmlFor="profile-role"
            hint="Read-only"
          >
            <input
              id="profile-role"
              type="text"
              value={user.role.replace('_', ' ')}
              readOnly
              className="input-field capitalize cursor-default bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
            />
          </FormField>

          <FormField
            label="Search Timezone"
            htmlFor="profile-timezone-search"
            hint="Type to narrow the timezone list."
            className="md:col-span-2"
          >
            <input
              id="profile-timezone-search"
              type="search"
              value={timezoneSearch}
              onChange={(event) => setTimezoneSearch(event.target.value)}
              placeholder="Search timezones..."
              className="input-field"
            />
          </FormField>

          <FormField label="Timezone" htmlFor="profile-timezone" required>
            <select
              id="profile-timezone"
              value={timezone}
              onChange={(event) => {
                setTimezone(event.target.value)
                setTimezoneSearch('')
              }}
              className="select-field"
            >
              {timezoneOptions.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </FormField>

          <FormField label="Locale" htmlFor="profile-locale" required>
            <select
              id="profile-locale"
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
          </FormField>
        </div>

        <SubmitButton
          isLoading={updateProfileMutation.isPending}
          loadingText="Saving..."
          disabled={
            fullName.trim().length === 0 ||
            timezone.trim().length === 0 ||
            locale.trim().length === 0
          }
          className="disabled:cursor-not-allowed"
        >
          Save Profile
        </SubmitButton>
      </form>

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

      <div className="surface-card space-y-3 rounded-2xl p-6">
        <h3 className="section-title">Product Tour</h3>
        <p className="body-copy dark:text-slate-300">
          Replay onboarding tours for the documents list and document detail screens.
        </p>
        <button type="button" className="btn-secondary table-action-btn" onClick={replayTours}>
          Replay tour
        </button>
      </div>
    </div>
  )
}
