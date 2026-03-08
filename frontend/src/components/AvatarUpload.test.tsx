import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AvatarUpload from './AvatarUpload'

const uploadMyAvatarMock = vi.fn()
const createObjectURLMock = vi.fn()
const revokeObjectURLMock = vi.fn()

vi.mock('@/lib/api', () => ({
  api: {
    uploadMyAvatar: (...args: unknown[]) => uploadMyAvatarMock(...args),
  },
}))

vi.mock('@/lib/toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

describe('AvatarUpload', () => {
  beforeEach(() => {
    uploadMyAvatarMock.mockReset()
    createObjectURLMock.mockReset()
    revokeObjectURLMock.mockReset()
    createObjectURLMock.mockReturnValue('blob:avatar-preview')

    vi.stubGlobal('URL', {
      ...globalThis.URL,
      createObjectURL: createObjectURLMock,
      revokeObjectURL: revokeObjectURLMock,
    })
  })

  it('selects image file, renders preview, and submits upload', async () => {
    const user = userEvent.setup()
    const queryClient = createQueryClient()
    const onUploaded = vi.fn()
    const selectedFile = new File(['image-bytes'], 'avatar.png', { type: 'image/png' })

    uploadMyAvatarMock.mockResolvedValue({
      avatar_url: 'https://cdn.example.com/avatar.jpg',
      message: 'Avatar uploaded successfully',
    })

    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <AvatarUpload currentAvatarUrl={null} onUploaded={onUploaded} />
      </QueryClientProvider>,
    )

    const fileInput = container.querySelector('input[type="file"]')
    expect(fileInput).not.toBeNull()
    await user.upload(fileInput as HTMLInputElement, selectedFile)

    const previewImage = await screen.findByAltText('Avatar preview')
    expect(previewImage).toHaveAttribute('src', 'blob:avatar-preview')

    await user.click(screen.getByRole('button', { name: /upload avatar/i }))

    await waitFor(() => {
      expect(uploadMyAvatarMock).toHaveBeenCalledWith(selectedFile)
      expect(onUploaded).toHaveBeenCalledWith('https://cdn.example.com/avatar.jpg')
    })
  })
})
