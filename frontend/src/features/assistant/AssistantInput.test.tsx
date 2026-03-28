import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AssistantInput from './AssistantInput'

vi.mock('@/lib/api', () => ({
  api: {
    getToken: vi.fn(() => 'assistant-token'),
    getDocuments: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

describe('AssistantInput', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('forwards uploaded file ids when sending a message', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        file_id: 91,
        filename: 'notes.txt',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { container } = render(
      <AssistantInput
        onSend={onSend}
        onCancel={() => {}}
        isLoading={false}
      />,
    )

    const fileInput = container.querySelector('input[type="file"]')
    expect(fileInput).not.toBeNull()

    await user.upload(fileInput as HTMLInputElement, new File(['file body'], 'notes.txt', { type: 'text/plain' }))

    await waitFor(() => {
      expect(screen.getByText(/notes\.txt/i)).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText(/type a message/i), 'Use the uploaded file')
    await user.click(screen.getByTitle('Send message'))

    expect(onSend).toHaveBeenCalledWith('Use the uploaded file', undefined, [91])
  })
})
