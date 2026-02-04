import { Link } from 'react-router-dom'

export default function PublicHelpPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <section className="bg-gradient-to-r from-sky-950 via-sky-900 to-sky-700 text-white">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Viewer Portal</div>
          <h1 className="text-3xl md:text-4xl font-display font-bold">Help Center</h1>
          <p className="text-sky-100 mt-3 max-w-2xl">
            Guidance for searching docs, requesting access, and staying aligned with release updates.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-8">
          <div className="surface-card rounded-3xl p-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Getting started</h2>
            <div className="space-y-4 text-slate-600 text-sm leading-6">
              <div>
                <div className="font-medium text-slate-900">Public documents</div>
                <p>Available to all users without authentication.</p>
              </div>
              <div>
                <div className="font-medium text-slate-900">Restricted documents</div>
                <p>Require additional approvals or role assignments.</p>
              </div>
              <div>
                <div className="font-medium text-slate-900">Comments & feedback</div>
                <p>Add comments on docs to flag updates or request clarifications.</p>
              </div>
            </div>
          </div>

          <div className="rounded-3xl bg-gradient-to-br from-sky-900 via-sky-800 to-sky-700 text-white p-8">
            <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Need help?</div>
            <h3 className="text-xl font-semibold mb-4">Support channels</h3>
            <ul className="text-sm text-sky-100 space-y-3">
              <li>Access requests: contact your portal admin</li>
              <li>Doc corrections: comment directly on the doc</li>
              <li>Tooling issues: open a ticket with Developer Ops</li>
            </ul>
            <Link
              to="/docs"
              className="inline-flex items-center mt-6 px-4 py-2 rounded-full bg-white/90 text-sky-900 text-sm font-medium hover:bg-white"
            >
              Return to docs
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
