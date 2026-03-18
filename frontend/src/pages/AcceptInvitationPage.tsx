import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import {
  CheckCircle2,
  XCircle,
  User,
  Lock,
  Mail,
  Building2,
  AlertCircle,
  Loader2,
  FileText,
} from 'lucide-react'

export default function AcceptInvitationPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { refreshUser } = useAuth()

  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')

  // Validate the invitation token
  const {
    data: invitation,
    isLoading,
    error: validationError,
  } = useQuery({
    queryKey: ['invitation-validate', token],
    queryFn: () => api.validateInvitation(token!),
    enabled: !!token,
    retry: false,
  })

  // Accept invitation mutation
  const acceptMutation = useMutation({
    mutationFn: () =>
      api.acceptInvitation({
        token: token!,
        username: formData.username,
        full_name: formData.full_name,
        password: formData.password,
      }),
    onSuccess: async (data) => {
      api.setToken(data.access_token, data.refresh_token)
      const currentUser = await refreshUser()

      // Redirect to role-appropriate home after session bootstrap.
      if (currentUser?.role === 'customer' || invitation?.role === 'customer') {
        navigate('/portal')
      } else {
        navigate('/')
      }
    },
    onError: (err: unknown) => {
      const apiError = err as { response?: { data?: { detail?: string } } }
      setError(apiError.response?.data?.detail || 'Failed to create account')
    },
  })

  // Pre-fill email as username if email looks like a valid username
  useEffect(() => {
    if (invitation?.valid && invitation.email) {
      const emailPrefix = invitation.email.split('@')[0]
      if (emailPrefix && /^[a-zA-Z0-9_-]+$/.test(emailPrefix)) {
        setFormData((prev) => ({
          ...prev,
          username: prev.username || emailPrefix,
        }))
      }
    }
  }, [invitation])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.username || !formData.full_name || !formData.password) {
      setError('All fields are required')
      return
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    acceptMutation.mutate()
  }

  // No token provided
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50 flex items-center justify-center p-4">
        <div className="surface-card rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-rose-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-8 h-8 text-rose-600" />
          </div>
          <h1 className="text-xl font-bold text-slate-900 mb-2">Invalid Link</h1>
          <p className="text-slate-600 mb-6">
            This invitation link is invalid. Please check your email for the correct link.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary"
          >
            Go to Login
          </button>
        </div>
      </div>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-sky-600 animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Validating invitation...</p>
        </div>
      </div>
    )
  }

  // Invalid or expired invitation
  if (validationError || !invitation?.valid) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-50 flex items-center justify-center p-4">
        <div className="surface-card rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-rose-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="w-8 h-8 text-rose-600" />
          </div>
          <h1 className="text-xl font-bold text-slate-900 mb-2">Invitation Invalid</h1>
          <p className="text-slate-600 mb-6">
            This invitation link is invalid or has expired. Please contact the person who
            invited you to request a new invitation.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="btn-primary"
          >
            Go to Login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-sky-100 flex items-center justify-center p-4">
      <div className="surface-card rounded-2xl shadow-lg w-full max-w-lg">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 text-center">
          <div className="w-16 h-16 bg-sky-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-sky-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Accept Invitation</h1>
          <p className="text-slate-600 mt-2">
            You've been invited to join the document management platform
          </p>
        </div>

        {/* Invitation Details */}
        <div className="px-6 pt-6">
          <div className="bg-sky-50 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-sky-600" />
              <div>
                <p className="text-xs text-sky-600 font-medium">Email</p>
                <p className="text-slate-900">{invitation.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-sky-600" />
              <div>
                <p className="text-xs text-sky-600 font-medium">Role</p>
                <p className="text-slate-900 capitalize">
                  {invitation.role?.replace('_', ' ')}
                </p>
              </div>
            </div>
            {invitation.company_name && (
              <div className="flex items-center gap-3">
                <Building2 className="w-5 h-5 text-sky-600" />
                <div>
                  <p className="text-xs text-sky-600 font-medium">Company</p>
                  <p className="text-slate-900">{invitation.company_name}</p>
                </div>
              </div>
            )}
            {invitation.inviter_name && (
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-sky-600" />
                <div>
                  <p className="text-xs text-sky-600 font-medium">Invited by</p>
                  <p className="text-slate-900">{invitation.inviter_name}</p>
                </div>
              </div>
            )}
            {invitation.message && (
              <div className="pt-2 border-t border-sky-200">
                <p className="text-sm text-slate-700 italic">"{invitation.message}"</p>
              </div>
            )}
          </div>
        </div>

        {/* Registration Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-rose-50 text-rose-700 rounded-lg">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Username <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="Choose a username"
                required
                className="input-field pl-10"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Full Name <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="Enter your full name"
                required
                className="input-field pl-10"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="Create a password"
                required
                minLength={8}
                aria-describedby="password-hint"
                className="input-field pl-10"
              />
            </div>
            <p id="password-hint" className="text-xs text-slate-500 mt-1">Must be at least 8 characters</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Confirm Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="password"
                value={formData.confirmPassword}
                onChange={(e) =>
                  setFormData({ ...formData, confirmPassword: e.target.value })
                }
                placeholder="Confirm your password"
                required
                className="input-field pl-10"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={acceptMutation.isPending}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3"
          >
            {acceptMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating Account...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Create Account
              </>
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="px-6 pb-6 text-center">
          <p className="text-sm text-slate-500">
            Already have an account?{' '}
            <button
              onClick={() => navigate('/login')}
              className="text-sky-600 hover:text-sky-700 font-medium"
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
