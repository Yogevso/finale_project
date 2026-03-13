export interface DocumentTemplate {
  id: string
  name: string
  description: string
  category: string
  tags: string[]
  content: string
}

export const documentTemplates: DocumentTemplate[] = [
  {
    id: 'release-notes',
    name: 'Release Notes',
    description: 'Summarize changes, rollout notes, and known issues for a product release.',
    category: 'Release Notes',
    tags: ['release', 'customer-facing'],
    content: `<h1>Release Notes</h1><p>Summarize what changed in this release and who it affects.</p><h2>Highlights</h2><ul><li>Feature or improvement</li><li>Operational note</li></ul><h2>Known Issues</h2><ul><li>Document any known limitations.</li></ul><h2>Rollout Guidance</h2><p>Include rollout timing, enablement steps, and support contacts.</p>`,
  },
  {
    id: 'technical-spec',
    name: 'Technical Spec',
    description: 'Capture scope, architecture, dependencies, and rollout risks for implementation work.',
    category: 'Technical Spec',
    tags: ['engineering', 'spec'],
    content: `<h1>Technical Specification</h1><h2>Problem Statement</h2><p>Describe the problem, constraints, and success criteria.</p><h2>Proposed Solution</h2><p>Outline the architecture, interfaces, and data flow.</p><h2>Dependencies</h2><ul><li>Service or system dependency</li></ul><h2>Risks and Mitigations</h2><ul><li>Risk with mitigation</li></ul><h2>Rollout Plan</h2><p>List rollout phases, monitoring, and rollback criteria.</p>`,
  },
  {
    id: 'api-guide',
    name: 'API Guide',
    description: 'Explain an API surface with auth, requests, responses, and troubleshooting steps.',
    category: 'API Guide',
    tags: ['api', 'developer'],
    content: `<h1>API Guide</h1><h2>Overview</h2><p>Explain what the API does and when to use it.</p><h2>Authentication</h2><p>Document auth requirements and headers.</p><h2>Endpoints</h2><h3>Request</h3><p>Describe parameters, payloads, and examples.</p><h3>Response</h3><p>Describe response fields and common errors.</p><h2>Troubleshooting</h2><ul><li>Common integration issue</li></ul>`,
  },
  {
    id: 'runbook',
    name: 'Operational Runbook',
    description: 'Track operational procedures, incident response steps, and ownership.',
    category: 'Runbook',
    tags: ['operations', 'support'],
    content: `<h1>Operational Runbook</h1><h2>Purpose</h2><p>Define the scenario this runbook covers.</p><h2>Owners</h2><p>List primary and backup owners.</p><h2>Procedure</h2><ol><li>Step one</li><li>Step two</li></ol><h2>Escalation</h2><p>Document escalation contacts and thresholds.</p><h2>Verification</h2><p>Explain how to confirm the system is healthy again.</p>`,
  },
]

export function getDocumentTemplate(templateId: string) {
  return documentTemplates.find((template) => template.id === templateId) ?? null
}
