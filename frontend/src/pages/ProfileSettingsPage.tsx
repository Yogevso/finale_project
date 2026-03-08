import { useEffect, useState } from 'react'
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

  useEffect(() => {
    setFullName(user?.full_name || '')
  }, [user?.full_name])

  const updateProfileMutation = useMutation({
    mutationFn: (nextFullName: string) =>
      api.updateMyProfile({
        full_name: nextFullName,
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
            <label className="text-sm font-medium text-slate-700">Username</label>
            <input
              type="text"
              value={user.username}
              readOnly
              className="input-field bg-slate-100 text-slate-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Email</label>
            <input type="email" value={user.email} readOnly className="input-field bg-slate-100 text-slate-500" />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-slate-700">Role</label>
            <input
              type="text"
              value={user.role.replace('_', ' ')}
              readOnly
              className="input-field bg-slate-100 text-slate-500 capitalize"
            />
          </div>
        </div>

        <button
          type="button"
          className="btn-primary"
          disabled={updateProfileMutation.isPending || fullName.trim().length === 0}
          onClick={() => updateProfileMutation.mutate(fullName.trim())}
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
    </div>
  )
}
