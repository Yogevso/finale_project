import { LogIn, ShieldAlert } from 'lucide-react'

type SessionExpiredModalProps = {
  isOpen: boolean
  onSignInAgain: () => void
}

export default function SessionExpiredModal({ isOpen, onSignInAgain }: SessionExpiredModalProps) {
  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="session-expired-title"
        aria-describedby="session-expired-description"
        className="w-full max-w-md overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
      >
        <div className="h-1 w-full bg-gradient-to-r from-blue-500 via-cyan-500 to-emerald-500" />
        <div className="p-6">
          <div className="flex items-start gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
              <ShieldAlert className="h-5 w-5" />
            </span>
            <div>
              <h2 id="session-expired-title" className="text-lg font-semibold text-slate-900">
                Session expired
              </h2>
              <p id="session-expired-description" className="mt-1 text-sm text-slate-600">
                Your login session ended for security reasons. Sign in again to continue editing and
                reviewing.
              </p>
            </div>
          </div>
          <div className="mt-5 flex justify-end">
            <button type="button" onClick={onSignInAgain} className="btn-primary inline-flex items-center gap-2">
              <LogIn className="h-4 w-4" />
              Sign in again
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
