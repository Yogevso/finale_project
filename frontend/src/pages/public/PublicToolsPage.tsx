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
    <div className="min-h-screen bg-slate-50">
      <section className="bg-gradient-to-r from-sky-950 via-sky-900 to-sky-700 text-white">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-xs uppercase tracking-widest text-sky-200 mb-3">Viewer Portal</div>
          <h1 className="text-3xl md:text-4xl font-display font-bold">Tools</h1>
          <p className="text-sky-100 mt-3 max-w-2xl">
            SDKs, APIs, and supporting resources for approved documentation.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tools.map((tool) => (
            <div key={tool.title} className="surface-card rounded-2xl p-6">
              <Wrench className="h-8 w-8 text-sky-500 mb-3" />
              <h3 className="font-semibold text-slate-900">{tool.title}</h3>
              <p className="text-sm text-slate-500 mt-2">{tool.description}</p>
              <div className="mt-4 flex items-center justify-between">
                <span className="pill bg-slate-100 text-slate-600 border-slate-200">{tool.tag}</span>
                <Link to="/docs" className="text-sky-700 text-sm inline-flex items-center gap-1">
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
