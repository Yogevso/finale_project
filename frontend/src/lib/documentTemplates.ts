export interface DocumentTemplate {
  id: string
  name: string
  description: string
  category: string
  tags: string[]
  content: string
  source?: 'built-in' | 'custom'
  createdAt?: string
}

const CUSTOM_TEMPLATE_STORAGE_KEY = 'finale:custom-document-templates'
const HIDDEN_BUILT_IN_TEMPLATE_STORAGE_KEY = 'finale:hidden-built-in-document-templates'

export const builtInDocumentTemplates: DocumentTemplate[] = [
  {
    id: 'release-notes',
    name: 'Release Notes',
    description: 'Summarize changes, rollout notes, and known issues for a product release.',
    category: 'Release Notes',
    tags: ['release', 'customer-facing'],
    content: `<h1>Release Notes</h1><p>Summarize what changed in this release and who it affects.</p><h2>Highlights</h2><ul><li>Feature or improvement</li><li>Operational note</li></ul><h2>Known Issues</h2><ul><li>Document any known limitations.</li></ul><h2>Rollout Guidance</h2><p>Include rollout timing, enablement steps, and support contacts.</p>`,
    source: 'built-in',
  },
  {
    id: 'technical-spec',
    name: 'Technical Spec',
    description: 'Capture scope, architecture, dependencies, and rollout risks for implementation work.',
    category: 'Technical Spec',
    tags: ['engineering', 'spec'],
    content: `<h1>Technical Specification</h1><h2>Problem Statement</h2><p>Describe the problem, constraints, and success criteria.</p><h2>Proposed Solution</h2><p>Outline the architecture, interfaces, and data flow.</p><h2>Dependencies</h2><ul><li>Service or system dependency</li></ul><h2>Risks and Mitigations</h2><ul><li>Risk with mitigation</li></ul><h2>Rollout Plan</h2><p>List rollout phases, monitoring, and rollback criteria.</p>`,
    source: 'built-in',
  },
  {
    id: 'api-guide',
    name: 'API Guide',
    description: 'Explain an API surface with auth, requests, responses, and troubleshooting steps.',
    category: 'API Guide',
    tags: ['api', 'developer'],
    content: `<h1>API Guide</h1><h2>Overview</h2><p>Explain what the API does and when to use it.</p><h2>Authentication</h2><p>Document auth requirements and headers.</p><h2>Endpoints</h2><h3>Request</h3><p>Describe parameters, payloads, and examples.</p><h3>Response</h3><p>Describe response fields and common errors.</p><h2>Troubleshooting</h2><ul><li>Common integration issue</li></ul>`,
    source: 'built-in',
  },
  {
    id: 'runbook',
    name: 'Operational Runbook',
    description: 'Track operational procedures, incident response steps, and ownership.',
    category: 'Runbook',
    tags: ['operations', 'support'],
    content: `<h1>Operational Runbook</h1><h2>Purpose</h2><p>Define the scenario this runbook covers.</p><h2>Owners</h2><p>List primary and backup owners.</p><h2>Procedure</h2><ol><li>Step one</li><li>Step two</li></ol><h2>Escalation</h2><p>Document escalation contacts and thresholds.</p><h2>Verification</h2><p>Explain how to confirm the system is healthy again.</p>`,
    source: 'built-in',
  },
]

export const documentTemplates = builtInDocumentTemplates

function isValidTemplate(value: unknown): value is DocumentTemplate {
  if (!value || typeof value !== 'object') {
    return false
  }

  const candidate = value as Partial<DocumentTemplate>
  return (
    typeof candidate.id === 'string' &&
    typeof candidate.name === 'string' &&
    typeof candidate.description === 'string' &&
    typeof candidate.category === 'string' &&
    Array.isArray(candidate.tags) &&
    candidate.tags.every((tag) => typeof tag === 'string') &&
    typeof candidate.content === 'string'
  )
}

function getStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    return window.localStorage
  } catch {
    return null
  }
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === 'string')
}

function buildCustomTemplateId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40) || 'template'

  const uniqueSuffix =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID().slice(0, 8)
      : `${Date.now()}`

  return `custom-${slug}-${uniqueSuffix}`
}

export function loadCustomDocumentTemplates(): DocumentTemplate[] {
  const storage = getStorage()
  if (!storage) {
    return []
  }

  try {
    const raw = storage.getItem(CUSTOM_TEMPLATE_STORAGE_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      storage.removeItem(CUSTOM_TEMPLATE_STORAGE_KEY)
      return []
    }

    return parsed
      .filter(isValidTemplate)
      .map((template) => ({
        ...template,
        source: 'custom' as const,
      }))
  } catch {
    return []
  }
}

export function loadHiddenBuiltInTemplateIds(): string[] {
  const storage = getStorage()
  if (!storage) {
    return []
  }

  try {
    const raw = storage.getItem(HIDDEN_BUILT_IN_TEMPLATE_STORAGE_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw) as unknown
    if (!isStringArray(parsed)) {
      storage.removeItem(HIDDEN_BUILT_IN_TEMPLATE_STORAGE_KEY)
      return []
    }

    return parsed
  } catch {
    return []
  }
}

function saveCustomDocumentTemplates(templates: DocumentTemplate[]) {
  const storage = getStorage()
  if (!storage) {
    return
  }

  try {
    storage.setItem(CUSTOM_TEMPLATE_STORAGE_KEY, JSON.stringify(templates))
  } catch {
    // Ignore quota and storage access failures.
  }
}

function saveHiddenBuiltInTemplateIds(templateIds: string[]) {
  const storage = getStorage()
  if (!storage) {
    return
  }

  try {
    storage.setItem(
      HIDDEN_BUILT_IN_TEMPLATE_STORAGE_KEY,
      JSON.stringify(Array.from(new Set(templateIds))),
    )
  } catch {
    // Ignore quota and storage access failures.
  }
}

export function listDocumentTemplates(): DocumentTemplate[] {
  const hiddenBuiltInTemplateIds = new Set(loadHiddenBuiltInTemplateIds())
  return [
    ...loadCustomDocumentTemplates(),
    ...builtInDocumentTemplates.filter((template) => !hiddenBuiltInTemplateIds.has(template.id)),
  ]
}

export function createCustomDocumentTemplate(
  template: Omit<DocumentTemplate, 'id'> & { id?: string },
): DocumentTemplate {
  const nextTemplate: DocumentTemplate = {
    ...template,
    id: template.id || buildCustomTemplateId(template.name),
    source: 'custom',
    createdAt: template.createdAt || new Date().toISOString(),
  }

  const existing = loadCustomDocumentTemplates()
  saveCustomDocumentTemplates([nextTemplate, ...existing.filter((entry) => entry.id !== nextTemplate.id)])
  return nextTemplate
}

export function deleteCustomDocumentTemplate(templateId: string): void {
  const existing = loadCustomDocumentTemplates()
  saveCustomDocumentTemplates(existing.filter((template) => template.id !== templateId))
}

export function hideBuiltInDocumentTemplate(templateId: string): void {
  if (!builtInDocumentTemplates.some((template) => template.id === templateId)) {
    return
  }

  const existing = loadHiddenBuiltInTemplateIds()
  saveHiddenBuiltInTemplateIds([...existing, templateId])
}

export function deleteDocumentTemplate(templateId: string): void {
  if (loadCustomDocumentTemplates().some((template) => template.id === templateId)) {
    deleteCustomDocumentTemplate(templateId)
    return
  }

  hideBuiltInDocumentTemplate(templateId)
}

export function getDocumentTemplate(templateId: string) {
  return listDocumentTemplates().find((template) => template.id === templateId) ?? null
}
