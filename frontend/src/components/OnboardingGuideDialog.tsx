import { ArrowRight, BookOpen, CheckCircle2, Sparkles, X } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useFocusTrap } from '@/hooks/useAccessibility'
import type { RoleOnboardingConfig } from '@/features/onboarding/config'

type OnboardingGuideDialogProps = {
  open: boolean
  config: RoleOnboardingConfig | null
  onClose: () => void
}

export default function OnboardingGuideDialog({
  open,
  config,
  onClose,
}: OnboardingGuideDialogProps) {
  const { containerRef, handleKeyDown } = useFocusTrap(onClose)

  if (!open || !config) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 px-4 py-8"
      onClick={onClose}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Welcome guide"
        className="w-full max-w-4xl overflow-hidden rounded-[28px] border border-sky-100 bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <div className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.2),_transparent_45%),linear-gradient(135deg,_#082f49_0%,_#0f766e_100%)] px-6 py-6 text-white md:px-8">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20"
            aria-label="Close welcome guide"
          >
            <X className="h-4 w-4" />
          </button>
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white/85">
              <Sparkles className="h-3.5 w-3.5" />
              First-time guide
            </div>
            <h2 className="text-2xl font-display font-semibold md:text-3xl">{config.title}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-sky-50 md:text-base">
              {config.description}
            </p>
          </div>
        </div>

        <div className="grid gap-6 px-6 py-6 md:grid-cols-[1.35fr_0.65fr] md:px-8">
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                What to expect
              </h3>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                {config.guideCards.map((card) => (
                  <div
                    key={card.title}
                    className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
                  >
                    <div className="flex items-center gap-2 text-slate-900">
                      <BookOpen className="h-4 w-4 text-sky-600" />
                      <h4 className="text-sm font-semibold">{card.title}</h4>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="inline-flex rounded-full bg-emerald-100 p-2 text-emerald-700">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <h3 className="mt-4 text-lg font-display font-semibold text-slate-900">
              Next step
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Close this guide to continue with your role-based onboarding checklist, or jump
              straight into the main workspace now.
            </p>
            <div className="mt-5 space-y-3">
              <button type="button" className="btn-primary w-full justify-center" onClick={onClose}>
                Start checklist
              </button>
              <Link
                to={config.primaryActionHref}
                onClick={onClose}
                className="btn-secondary table-action-btn w-full justify-center"
              >
                {config.primaryActionLabel}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <p className="mt-4 text-xs leading-5 text-slate-500">
              You can reopen this guide later from the dashboard or profile settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
