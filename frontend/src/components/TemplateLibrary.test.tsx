import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import TemplateLibrary from '@/components/TemplateLibrary'
import {
  createCustomDocumentTemplate,
  getDocumentTemplate,
  loadHiddenBuiltInTemplateIds,
  loadCustomDocumentTemplates,
} from '@/lib/documentTemplates'

function TemplateLibraryHarness() {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [editorValue, setEditorValue] = useState('')

  return (
    <div>
      <TemplateLibrary
        selectedTemplateId={selectedTemplateId}
        onSelectTemplate={(template) => {
          setSelectedTemplateId(template.id)
          setEditorValue(template.content)
        }}
      />
      <textarea aria-label="Editor content" readOnly value={editorValue} />
    </div>
  )
}

describe('TemplateLibrary', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('selects a template and pre-fills editor content', async () => {
    const user = userEvent.setup()
    const selectedTemplate = getDocumentTemplate('technical-spec')

    render(<TemplateLibraryHarness />)

    await user.click(screen.getByRole('button', { name: /use template technical spec/i }))

    expect(selectedTemplate).not.toBeNull()
    const editor = screen.getByLabelText('Editor content') as HTMLTextAreaElement
    expect(editor).toHaveValue(selectedTemplate?.content ?? '')
    expect(editor.value).toContain('Technical Specification')
  })

  it('renders and deletes custom templates from local storage', async () => {
    const user = userEvent.setup()
    createCustomDocumentTemplate({
      name: 'My Operations Template',
      description: 'Reusable internal template',
      category: 'Operations',
      tags: ['ops'],
      content: '<h1>My Operations Template</h1><p>Body</p>',
    })

    render(<TemplateLibraryHarness />)

    expect(screen.getByText('My Operations Template')).toBeInTheDocument()
    expect(screen.getByText('Custom')).toBeInTheDocument()

    await user.click(screen.getByLabelText(/delete template my operations template/i))

    expect(screen.queryByText('My Operations Template')).not.toBeInTheDocument()
    expect(loadCustomDocumentTemplates()).toHaveLength(0)
  })

  it('hides built-in templates from the library when deleted', async () => {
    const user = userEvent.setup()

    render(<TemplateLibraryHarness />)

    expect(screen.getByRole('button', { name: /use template technical spec/i })).toBeInTheDocument()

    await user.click(screen.getByLabelText(/delete template technical spec/i))

    expect(screen.queryByRole('button', { name: /use template technical spec/i })).not.toBeInTheDocument()
    expect(loadHiddenBuiltInTemplateIds()).toEqual(['technical-spec'])
  })
})
