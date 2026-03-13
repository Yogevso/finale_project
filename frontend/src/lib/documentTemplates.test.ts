import { beforeEach, describe, expect, it } from 'vitest'
import {
  createCustomDocumentTemplate,
  deleteDocumentTemplate,
  getDocumentTemplate,
  listDocumentTemplates,
  loadHiddenBuiltInTemplateIds,
  loadCustomDocumentTemplates,
} from '@/lib/documentTemplates'

describe('documentTemplates', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('persists custom templates in local storage and includes them in the library list', () => {
    const created = createCustomDocumentTemplate({
      name: 'Customer Brief',
      description: 'Reusable outline',
      category: 'Brief',
      tags: ['customer', 'brief'],
      content: '<h1>Customer Brief</h1><p>Summary</p>',
    })

    expect(created.source).toBe('custom')
    expect(loadCustomDocumentTemplates()).toEqual([created])
    expect(getDocumentTemplate(created.id)).toEqual(created)
    expect(listDocumentTemplates().some((template) => template.id === created.id)).toBe(true)
  })

  it('removes deleted custom templates without affecting built-in templates', () => {
    const created = createCustomDocumentTemplate({
      name: 'Runbook Variant',
      description: 'Reusable runbook',
      category: 'Runbook',
      tags: ['ops'],
      content: '<h1>Runbook Variant</h1>',
    })

    deleteDocumentTemplate(created.id)

    expect(loadCustomDocumentTemplates()).toEqual([])
    expect(getDocumentTemplate('runbook')?.name).toBe('Operational Runbook')
  })

  it('hides built-in templates locally without touching custom templates', () => {
    const custom = createCustomDocumentTemplate({
      name: 'My Template',
      description: 'Reusable custom content',
      category: 'General',
      tags: ['custom'],
      content: '<h1>My Template</h1>',
    })

    deleteDocumentTemplate('technical-spec')

    expect(loadHiddenBuiltInTemplateIds()).toEqual(['technical-spec'])
    expect(getDocumentTemplate('technical-spec')).toBeNull()
    expect(listDocumentTemplates().some((template) => template.id === 'technical-spec')).toBe(false)
    expect(getDocumentTemplate(custom.id)).toEqual(custom)
  })
})
