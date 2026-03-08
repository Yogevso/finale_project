import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Circle, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { UserRole } from '@/types'

type OnboardingChecklistProps = {
  storageKey: string
  role: UserRole
  documentsPath: string
}

type ChecklistState = {
  completed_steps: string[]
  onboarding_completed: boolean
}

type ChecklistStep = {
  id: string
  title: string
  description: string
  href: string
}

const DEFAULT_STATE: ChecklistState = {
  completed_steps: [],
  onboarding_completed: false,
}

export default function OnboardingChecklist({
  storageKey,
  role,
  documentsPath,
}: OnboardingChecklistProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [state, setState] = useState<ChecklistState>(DEFAULT_STATE)

  const steps = useMemo<ChecklistStep[]>(() => {
    if (role === 'viewer') {
      return [
        {
          id: 'browse_documents',
          title: 'Browse documents',
          description: 'Open the documents area and review available content.',
          href: documentsPath,
        },
        {
          id: 'follow_document',
          title: 'Follow a document',
          description: 'Open a document and use notifications/bookmarks to follow updates.',
          href: documentsPath,
        },
        {
          id: 'set_notification_preferences',
          title: 'Set notification preferences',
          description: 'Choose which updates should trigger email notifications.',
          href: '/profile#notifications',
        },
      ]
    }

    if (role === 'editor') {
      return [
        {
          id: 'create_first_document',
          title: 'Create your first document',
          description: 'Start a new document draft from the documents page.',
          href: '/documents?action=create',
        },
        {
          id: 'invite_reviewer',
          title: 'Invite a reviewer',
          description: 'Open user management and invite a reviewer for your content.',
          href: '/users',
        },
        {
          id: 'publish_document',
          title: 'Publish a document',
          description: 'Submit and publish a reviewed document.',
          href: '/reviews',
        },
      ]
    }

    if (role === 'admin' || role === 'system_admin') {
      return [
        {
          id: 'invite_team',
          title: 'Invite your team',
          description: 'Send invitations so your team can start collaborating.',
          href: '/users',
        },
        {
          id: 'set_up_categories',
          title: 'Set up categories',
          description: 'Create category structure for your documentation.',
          href: '/documents',
        },
        {
          id: 'review_pending_approvals',
          title: 'Review pending approvals',
          description: 'Process pending approvals in the review queue.',
          href: '/reviews',
        },
      ]
    }

    return [
      {
        id: 'set_up_profile',
        title: 'Set up profile',
        description: 'Review your profile details and avatar settings.',
        href: '/profile',
      },
      {
        id: 'explore_documents',
        title: 'Explore documents',
        description: 'Open the document workspace and review what is available.',
        href: documentsPath,
      },
      {
        id: 'set_notification_preferences',
        title: 'Set notification preferences',
        description: 'Choose which updates should trigger email notifications.',
        href: '/profile#notifications',
      },
    ]
  }, [documentsPath, role])

  useEffect(() => {
    const rawState = window.localStorage.getItem(storageKey)
    if (!rawState) {
      setState(DEFAULT_STATE)
      setIsVisible(true)
      return
    }

    try {
      const parsedState = JSON.parse(rawState) as ChecklistState
      const normalizedState: ChecklistState = {
        completed_steps: Array.isArray(parsedState.completed_steps)
          ? parsedState.completed_steps
          : [],
        onboarding_completed: Boolean(parsedState.onboarding_completed),
      }
      setState(normalizedState)
      setIsVisible(!normalizedState.onboarding_completed)
    } catch {
      setState(DEFAULT_STATE)
      setIsVisible(true)
    }
  }, [storageKey])

  const persistState = (nextState: ChecklistState) => {
    setState(nextState)
    window.localStorage.setItem(storageKey, JSON.stringify(nextState))
  }

  const completedCount = steps.filter((step) =>
    state.completed_steps.includes(step.id),
  ).length
  const isComplete = completedCount === steps.length

  const toggleStep = (stepId: string) => {
    const stepIsCompleted = state.completed_steps.includes(stepId)
    const nextCompletedSteps = stepIsCompleted
      ? state.completed_steps.filter((id) => id !== stepId)
      : [...state.completed_steps, stepId]

    const nextState: ChecklistState = {
      completed_steps: nextCompletedSteps,
      onboarding_completed: nextCompletedSteps.length === steps.length,
    }

    persistState(nextState)
    if (nextState.onboarding_completed) {
      setIsVisible(false)
    }
  }

  const dismissChecklist = () => {
    const completedState: ChecklistState = {
      completed_steps: steps.map((step) => step.id),
      onboarding_completed: true,
    }
    persistState(completedState)
    setIsVisible(false)
  }

  if (!isVisible) {
    return null
  }

  return (
    <div className="surface-card rounded-2xl border border-sky-200 bg-sky-50/70 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow text-sky-700">Welcome</p>
          <h2 className="text-xl font-display font-semibold text-slate-900">
            Onboarding checklist
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Complete these quick steps to finish your setup.
          </p>
        </div>
        <button
          type="button"
          onClick={dismissChecklist}
          className="inline-flex h-8 w-8 items-center justify-center rounded-full text-slate-500 hover:bg-white hover:text-slate-700"
          aria-label="Dismiss onboarding checklist"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 grid gap-3">
        {steps.map((step) => {
          const stepIsCompleted = state.completed_steps.includes(step.id)
          return (
            <div
              key={step.id}
              className="rounded-xl border border-slate-200 bg-white p-4"
            >
              <div className="flex items-start gap-3">
                <button
                  type="button"
                  onClick={() => toggleStep(step.id)}
                  className="mt-0.5 text-sky-700 hover:text-sky-800"
                  aria-label={`${stepIsCompleted ? 'Unmark' : 'Mark'} ${step.title} complete`}
                >
                  {stepIsCompleted ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <Circle className="h-5 w-5" />
                  )}
                </button>
                <div className="min-w-0 flex-1">
                  <p
                    className={`text-sm font-medium ${
                      stepIsCompleted ? 'text-slate-500 line-through' : 'text-slate-900'
                    }`}
                  >
                    {step.title}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{step.description}</p>
                  <Link to={step.href} className="mt-2 inline-flex text-xs font-medium text-sky-700 hover:text-sky-800">
                    Go to step
                  </Link>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <p className="text-slate-600">
          {completedCount}/{steps.length} completed
        </p>
        {isComplete && (
          <span className="font-medium text-emerald-700">Checklist completed</span>
        )}
      </div>
    </div>
  )
}
