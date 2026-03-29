import { CheckCircle2, ChevronDown, ChevronUp, Circle, RotateCcw, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { OnboardingStep } from '@/features/onboarding/config'

type OnboardingChecklistProps = {
  title: string
  description: string
  steps: OnboardingStep[]
  completedSteps: string[]
  completionDate?: string | null
  isPending?: boolean
  isCollapsed?: boolean
  onToggleCollapsed: () => void
  onToggleStep: (stepId: string) => void
  onReset: () => void
  onOpenGuide: () => void
}

export default function OnboardingChecklist({
  title,
  description,
  steps,
  completedSteps,
  completionDate,
  isPending = false,
  isCollapsed = false,
  onToggleCollapsed,
  onToggleStep,
  onReset,
  onOpenGuide,
}: OnboardingChecklistProps) {
  if (steps.length === 0) {
    return null
  }

  const completedCount = steps.filter((step) => completedSteps.includes(step.id)).length
  const isComplete = completedCount === steps.length
  const progressPercent = Math.round((completedCount / steps.length) * 100)
  const completionLabel = completionDate
    ? new Date(completionDate).toLocaleDateString()
    : null

  if (isCollapsed && !isComplete) {
    return (
      <div className="surface-card rounded-2xl border border-sky-200 bg-sky-50/75 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-sky-800">
              <Sparkles className="h-4 w-4" />
              Welcome onboarding
            </div>
            <p className="mt-1 text-sm text-slate-700">
              {completedCount}/{steps.length} steps completed. Keep this visible until you know where
              the main workflows live.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary table-action-btn" onClick={onOpenGuide}>
              Reopen guide
            </button>
            <button type="button" className="btn-primary table-action-btn" onClick={onToggleCollapsed}>
              Expand checklist
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="surface-card rounded-2xl border border-sky-200 bg-[linear-gradient(180deg,_rgba(240,249,255,0.95)_0%,_rgba(255,255,255,0.98)_100%)] p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white/90 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-800">
            <Sparkles className="h-3.5 w-3.5" />
            Welcome onboarding
          </div>
          <h2 className="mt-3 text-xl font-display font-semibold text-slate-900">{title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary table-action-btn" onClick={onOpenGuide}>
            Reopen guide
          </button>
          <button type="button" className="btn-ghost" onClick={onReset} disabled={isPending}>
            <RotateCcw className="h-4 w-4" />
            Reset
          </button>
          {!isComplete ? (
            <button type="button" className="btn-ghost" onClick={onToggleCollapsed}>
              <ChevronUp className="h-4 w-4" />
              Minimize
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 bg-white/90 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-semibold text-slate-900">
              {isComplete ? 'Checklist completed' : `${completedCount} of ${steps.length} steps complete`}
            </div>
            <p className="mt-1 text-sm text-slate-600">
              {isComplete
                ? completionLabel
                  ? `Completed on ${completionLabel}. You can still reopen the guide or reset the checklist at any time.`
                  : 'You have finished the checklist. You can still reopen the guide or reset the checklist at any time.'
                : 'Mark steps as you go. This does not block your work, but it keeps the important product surfaces easy to find.'}
            </p>
          </div>
          <div className="min-w-[140px]">
            <div className="h-2.5 w-full rounded-full bg-slate-200">
              <div
                className={`h-2.5 rounded-full transition-all ${
                  isComplete ? 'bg-emerald-500' : 'bg-sky-600'
                }`}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="mt-2 text-right text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              {progressPercent}% complete
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3">
        {steps.map((step) => {
          const stepIsCompleted = completedSteps.includes(step.id)

          return (
            <div
              key={step.id}
              className={`rounded-2xl border p-4 transition ${
                stepIsCompleted
                  ? 'border-emerald-200 bg-emerald-50/70'
                  : 'border-slate-200 bg-white/95'
              }`}
            >
              <div className="flex items-start gap-3">
                <button
                  type="button"
                  onClick={() => onToggleStep(step.id)}
                  disabled={isPending}
                  className={`mt-0.5 inline-flex h-8 w-8 items-center justify-center rounded-full border transition ${
                    stepIsCompleted
                      ? 'border-emerald-200 bg-emerald-100 text-emerald-700'
                      : 'border-slate-200 bg-white text-sky-700 hover:border-sky-200 hover:bg-sky-50'
                  } disabled:cursor-not-allowed disabled:opacity-60`}
                  aria-label={`${stepIsCompleted ? 'Unmark' : 'Mark'} ${step.title} complete`}
                >
                  {stepIsCompleted ? (
                    <CheckCircle2 className="h-5 w-5" />
                  ) : (
                    <Circle className="h-5 w-5" />
                  )}
                </button>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p
                        className={`text-sm font-semibold ${
                          stepIsCompleted ? 'text-emerald-800' : 'text-slate-900'
                        }`}
                      >
                        {step.title}
                      </p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{step.description}</p>
                    </div>
                    <Link
                      to={step.href}
                      className="btn-secondary table-action-btn shrink-0 justify-center"
                    >
                      {step.hrefLabel}
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {!isComplete ? (
        <div className="mt-5 flex justify-end">
          <button type="button" className="btn-ghost" onClick={onToggleCollapsed}>
            <ChevronDown className="h-4 w-4" />
            Keep checklist compact
          </button>
        </div>
      ) : null}
    </div>
  )
}
