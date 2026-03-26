import { FormEvent, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '@/lib/api'
import { resetPasswordSchema } from '@/lib/validation/schemas'
import { PasswordInput, SubmitButton } from '@/components/form'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')?.trim() ?? ''
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [confirmPasswordError, setConfirmPasswordError] = useState('')
  const [formError, setFormError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const isTokenMissing = useMemo(() => token.length === 0, [token])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isSubmitting || isTokenMissing) {
      return
    }

    let hasValidationError = false
    setPasswordError('')
    setConfirmPasswordError('')
    setFormError('')

    const result = resetPasswordSchema.safeParse({ newPassword, confirmPassword })
    if (!result.success) {
      for (const issue of result.error.issues) {
        if (issue.path[0] === 'newPassword') {
          setPasswordError(issue.message)
          hasValidationError = true
          break
        }
        if (issue.path[0] === 'confirmPassword') {
          setConfirmPasswordError(issue.message)
          hasValidationError = true
          break
        }
      }
      if (!hasValidationError) {
        setFormError(result.error.issues[0]?.message ?? 'Invalid input')
        hasValidationError = true
      }
    }

    if (hasValidationError) {
      return
    }

    setIsSubmitting(true)
    setSuccessMessage('')
    try {
      await api.resetPassword(token, newPassword)
      setSuccessMessage('Password reset successful. Redirecting to login...')
      window.setTimeout(() => {
        navigate('/login', { replace: true })
      }, 800)
    } catch {
      setFormError('Unable to reset password. Please request a new reset link.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 px-4 dark:from-slate-950 dark:via-slate-950 dark:to-slate-900">
      <div className="w-full max-w-md">
        <div className="surface-card animate-fade-in rounded-2xl p-8 space-y-6 dark:bg-slate-900">
          <div className="text-center">
            <h1 className="page-title dark:text-slate-100">Reset Password</h1>
            <p className="body-copy mt-2 dark:text-slate-400">
              Enter your new password to complete the reset process.
            </p>
          </div>

          {isTokenMissing && (
            <div className="alert-danger">
              Reset token is missing or invalid.
            </div>
          )}
          {formError && (
            <div className="alert-danger" role="alert">
              {formError}
            </div>
          )}
          {successMessage && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 body-copy text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/40 dark:text-emerald-200">
              {successMessage}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <PasswordInput
              id="new-password"
              label="New password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              error={passwordError}
              hint="Use at least 8 characters with a mix of letters and numbers."
              placeholder="Enter new password"
              autoComplete="new-password"
              required
              disabled={isTokenMissing}
            />

            <PasswordInput
              id="confirm-password"
              label="Confirm password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              error={confirmPasswordError}
              placeholder="Confirm new password"
              autoComplete="new-password"
              required
              disabled={isTokenMissing}
              showStrengthMeter={false}
            />

            <SubmitButton
              isLoading={isSubmitting}
              loadingText="Resetting password..."
              className="w-full py-3"
              disabled={isTokenMissing}
            >
              Reset Password
            </SubmitButton>
          </form>

          <div className="flex justify-center">
            <Link to="/login" className="btn-ghost table-action-btn">
              Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
