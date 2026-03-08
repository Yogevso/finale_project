import { FormEvent, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '@/lib/api'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')?.trim() ?? ''
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const isTokenMissing = useMemo(() => token.length === 0, [token])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isSubmitting || isTokenMissing) {
      return
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    setError('')
    setSuccessMessage('')
    try {
      await api.resetPassword(token, newPassword)
      setSuccessMessage('Password reset successful. Redirecting to login...')
      window.setTimeout(() => {
        navigate('/login', { replace: true })
      }, 800)
    } catch {
      setError('Unable to reset password. Please request a new reset link.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-md">
        <div className="surface-card rounded-2xl p-8 space-y-5">
          <div className="text-center">
            <h1 className="text-3xl font-display font-bold text-slate-900">Reset Password</h1>
            <p className="text-sm text-slate-600 mt-2">
              Enter your new password to complete the reset process.
            </p>
          </div>

          {isTokenMissing && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              Reset token is missing or invalid.
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
              {successMessage}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="new-password" className="block text-sm font-medium text-slate-700 mb-2">
                New password
              </label>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                className="input-field"
                placeholder="Enter new password"
                autoComplete="new-password"
                required
                disabled={isTokenMissing}
              />
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-700 mb-2">
                Confirm password
              </label>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="input-field"
                placeholder="Confirm new password"
                autoComplete="new-password"
                required
                disabled={isTokenMissing}
              />
            </div>

            <button
              type="submit"
              className="btn-primary w-full py-3"
              disabled={isSubmitting || isTokenMissing}
            >
              {isSubmitting ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>

          <div className="text-center">
            <Link to="/login" className="text-sm text-sky-600 hover:text-sky-700">
              Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
