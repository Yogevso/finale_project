import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import TemplateLibrary from '@/components/TemplateLibrary'
import { getDocumentTemplate } from '@/lib/documentTemplates'

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
  it('selects a template and pre-fills editor content', async () => {
    const user = userEvent.setup()
    const selectedTemplate = getDocumentTemplate('technical-spec')

    render(<TemplateLibraryHarness />)

    await user.click(screen.getByRole('button', { name: /technical spec/i }))

    expect(selectedTemplate).not.toBeNull()
    const editor = screen.getByLabelText('Editor content') as HTMLTextAreaElement
    expect(editor).toHaveValue(selectedTemplate?.content ?? '')
    expect(editor.value).toContain('Technical Specification')
  })
})
