import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DocumentsQuickCreatePanel } from './DocumentsQuickCreatePanel'

describe('DocumentsQuickCreatePanel', () => {
  it('shows clearer start guidance and triggers both actions', async () => {
    const user = userEvent.setup()
    const onCreate = vi.fn()
    const onUpload = vi.fn()

    render(<DocumentsQuickCreatePanel onCreate={onCreate} onUpload={onUpload} />)

    expect(screen.getByText('How do you want to begin?')).toBeInTheDocument()
    expect(screen.getByText('DOCX / PPTX import')).toBeInTheDocument()
    expect(screen.getByText('Audience settings later')).toBeInTheDocument()
    expect(screen.getByText('After creation, open Details to assign companies, review visibility, and finish audience setup.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /new document/i }))
    await user.click(screen.getByRole('button', { name: /upload file/i }))

    expect(onCreate).toHaveBeenCalled()
    expect(onUpload).toHaveBeenCalled()
  })
})
