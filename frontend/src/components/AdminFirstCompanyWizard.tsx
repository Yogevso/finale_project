import { useCallback, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, CheckCircle2, Mail, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'
import type { UserRole } from '@/types'
import { useFocusTrap } from '@/hooks/useAccessibility'

type AdminFirstCompanyWizardProps = {
  isOpen: boolean
  userId: number
  onDismiss: () => void
}

type WizardStep = 1 | 2 | 3

function toCompanyType(industry: string): 'customer' | 'partner' | 'internal' {
  const normalized = industry.toLowerCase()
  if (normalized.includes('partner')) return 'partner'
  if (normalized.includes('internal')) return 'internal'
  return 'customer'
}

export default function AdminFirstCompanyWizard({
  isOpen,
  userId,
  onDismiss,
}: AdminFirstCompanyWizardProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()

  const [step, setStep] = useState<WizardStep>(1)
  const [createdCompanyId, setCreatedCompanyId] = useState<number | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [industry, setIndustry] = useState('')
  const [website, setWebsite] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<UserRole>('editor')

  const dismissStorageKey = useMemo(() => `admin-wizard-dismissed-${userId}`, [userId])

  const dismissWizard = useCallback(() => {
    window.localStorage.setItem(dismissStorageKey, '1')
    onDismiss()
  }, [dismissStorageKey, onDismiss])

  const { containerRef } = useFocusTrap(dismissWizard)

  const createCompanyMutation = useMutation({
    mutationFn: () =>
      api.createCompany({
        name: companyName.trim(),
        company_type: toCompanyType(industry.trim()),
      }),
    onSuccess: (company) => {
      setCreatedCompanyId(company.id)
      setStep(2)
      toast.success('Company created')
      queryClient.invalidateQueries({ queryKey: ['companies', 'onboarding-check'] })
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to create company'
      toast.error('Could not create company', message)
    },
  })

  const inviteMutation = useMutation({
    mutationFn: () =>
      api.createInvitation({
        email: inviteEmail.trim(),
        role: inviteRole,
        tenant_id: createdCompanyId || undefined,
        message: website.trim()
          ? `Invited during setup wizard (website: ${website.trim()})`
          : 'Invited during setup wizard',
      }),
    onSuccess: () => {
      setStep(3)
      toast.success('Invitation sent')
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to send invitation'
      toast.error('Could not send invitation', message)
    },
  })

  const completeWizard = () => {
    window.localStorage.setItem(dismissStorageKey, '1')
    onDismiss()
    navigate('/documents?action=create')
  }

  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center px-4">
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="First Company Wizard"
        tabIndex={-1}
        className="w-full max-w-2xl bg-white rounded-2xl shadow-xl border border-slate-200"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <p className="eyebrow text-slate-500">Admin Setup</p>
            <h2 className="text-lg font-display font-semibold text-slate-900">First Company Wizard</h2>
          </div>
          <button
            type="button"
            onClick={dismissWizard}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100"
            aria-label="Dismiss setup wizard"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 py-4 border-b border-slate-200">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span className={`pill ${step >= 1 ? 'bg-blue-100 text-blue-700 border-blue-200' : ''}`}>1. Company</span>
            <span className={`pill ${step >= 2 ? 'bg-blue-100 text-blue-700 border-blue-200' : ''}`}>2. Invite user</span>
            <span className={`pill ${step >= 3 ? 'bg-blue-100 text-blue-700 border-blue-200' : ''}`}>3. Done</span>
          </div>
        </div>

        <div className="p-6">
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-slate-900">
                <Building2 className="h-5 w-5 text-blue-600" />
                <h3 className="font-medium">Create company</h3>
              </div>
              <div className="grid gap-4">
                <div className="space-y-1">
                  <label htmlFor="wizard-company-name" className="text-sm text-slate-700">Company name</label>
                  <input
                    id="wizard-company-name"
                    type="text"
                    value={companyName}
                    onChange={(event) => setCompanyName(event.target.value)}
                    className="input-field"
                    placeholder="Acme Corp"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="wizard-company-industry" className="text-sm text-slate-700">Industry</label>
                  <input
                    id="wizard-company-industry"
                    type="text"
                    value={industry}
                    onChange={(event) => setIndustry(event.target.value)}
                    className="input-field"
                    placeholder="Software"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="wizard-company-website" className="text-sm text-slate-700">Website</label>
                  <input
                    id="wizard-company-website"
                    type="url"
                    value={website}
                    onChange={(event) => setWebsite(event.target.value)}
                    className="input-field"
                    placeholder="https://example.com"
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => createCompanyMutation.mutate()}
                  disabled={createCompanyMutation.isPending || companyName.trim().length === 0}
                >
                  {createCompanyMutation.isPending ? 'Creating...' : 'Create Company'}
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-slate-900">
                <Mail className="h-5 w-5 text-blue-600" />
                <h3 className="font-medium">Invite first user</h3>
              </div>
              <div className="grid gap-4">
                <div className="space-y-1">
                  <label htmlFor="wizard-invite-email" className="text-sm text-slate-700">Email</label>
                  <input
                    id="wizard-invite-email"
                    type="email"
                    value={inviteEmail}
                    onChange={(event) => setInviteEmail(event.target.value)}
                    className="input-field"
                    placeholder="first.user@example.com"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="wizard-invite-role" className="text-sm text-slate-700">Role</label>
                  <select
                    id="wizard-invite-role"
                    value={inviteRole}
                    onChange={(event) => setInviteRole(event.target.value as UserRole)}
                    className="select-field"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="manager">Manager</option>
                    <option value="customer">Customer</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-between">
                <button type="button" className="btn-ghost" onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => inviteMutation.mutate()}
                  disabled={inviteMutation.isPending || inviteEmail.trim().length === 0}
                >
                  {inviteMutation.isPending ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4 text-center">
              <CheckCircle2 className="h-10 w-10 mx-auto text-emerald-600" />
              <h3 className="text-lg font-medium text-slate-900">Setup complete</h3>
              <p className="text-sm text-slate-600">
                Your first company and invitation are ready. Continue by creating your first document.
              </p>
              <div className="flex items-center justify-center gap-3">
                <button type="button" className="btn-secondary" onClick={dismissWizard}>
                  Close
                </button>
                <button type="button" className="btn-primary" onClick={completeWizard}>
                  Create your first document
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
