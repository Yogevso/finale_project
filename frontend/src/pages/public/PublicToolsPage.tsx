import { Link } from 'react-router-dom'
import { Wrench, ArrowRight } from 'lucide-react'

const tools = [
  { title: 'SDK Explorer', description: 'Browse SDKs, modules, and versions.', tag: 'SDK' },
  { title: 'API Console', description: 'Test endpoints and inspect responses.', tag: 'API' },
  { title: 'Release Planner', description: 'Track releases and upgrade impacts.', tag: 'Release' },
  { title: 'Compliance Toolkit', description: 'Map controls and evidence.', tag: 'Compliance' },
  { title: 'Access Request', description: 'Request access to restricted docs.', tag: 'Access' },
  { title: 'Feedback Hub', description: 'Submit feedback and corrections.', tag: 'Support' },
]

export default function PublicToolsPage() {
  return (
    <div className="min-h-screen animate-fade-in bg-slate-50 dark:bg-slate-950">
      <section className="bg-gradient-to-l from-blue-700 via-blue-600 to-blue-500 text-white">
        <div className="content-shell py-12">
          <div className="text-xs uppercase tracking-widest text-blue-200 mb-3">Viewer Portal</div>
          <h1 className="text-3xl md:text-4xl font-display font-bold">Tools</h1>
          <p className="text-blue-100 mt-3 max-w-2xl">
            SDKs, APIs, and supporting resources for approved documentation.
          </p>
        </div>
      </section>

      <section className="content-shell py-12">
        <div className="mb-8 max-w-2xl">
          <h2 className="page-title">Tool catalog</h2>
          <p className="body-copy mt-2">
            Explore the supporting utilities and integration surfaces linked from the public documentation experience.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tools.map((tool) => (
            <div key={tool.title} className="surface-card rounded-2xl p-6">
              <Wrench className="h-8 w-8 text-blue-500 mb-3" />
              <h3 className="card-title">{tool.title}</h3>
              <p className="body-copy mt-2">{tool.description}</p>
              <div className="mt-4 flex items-center justify-between">
                <span className="pill border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{tool.tag}</span>
                <Link to="/docs" className="btn-secondary table-action-btn">
                  View docs <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
