import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { UploadCloud, UserCircle2 } from 'lucide-react'

import { api } from '@/lib/api'
import { useToast } from '@/lib/toast'

type AvatarUploadProps = {
  currentAvatarUrl?: string | null
  onUploaded?: (avatarUrl: string) => void
}

export default function AvatarUpload({ currentAvatarUrl, onUploaded }: AvatarUploadProps) {
  const toast = useToast()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const effectivePreviewUrl = useMemo(() => {
    if (previewUrl) return previewUrl
    return currentAvatarUrl || null
  }, [previewUrl, currentAvatarUrl])

  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadMyAvatar(file),
    onSuccess: (response) => {
      toast.success('Avatar updated')
      setSelectedFile(null)
      setPreviewUrl(null)
      onUploaded?.(response.avatar_url)
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
        'Failed to upload avatar'
      toast.error('Avatar upload failed', message)
    },
  })

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0]
    if (!nextFile) return

    if (!nextFile.type.startsWith('image/')) {
      toast.error('Invalid file', 'Please select an image file.')
      return
    }

    if (previewUrl && previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl)
    }

    setSelectedFile(nextFile)
    setPreviewUrl(URL.createObjectURL(nextFile))
  }

  return (
    <div className="surface-card rounded-2xl p-6 space-y-4">
      <div>
        <h3 className="text-lg font-display font-semibold text-slate-900">Avatar</h3>
        <p className="text-sm text-slate-500 mt-1">Upload a profile image. It will be resized to 200 x 200.</p>
      </div>

      <div className="flex items-center gap-4">
        <div className="h-20 w-20 rounded-full bg-slate-100 border border-slate-200 overflow-hidden flex items-center justify-center">
          {effectivePreviewUrl ? (
            <img src={effectivePreviewUrl} alt="Avatar preview" className="h-full w-full object-cover" />
          ) : (
            <UserCircle2 className="h-10 w-10 text-slate-400" />
          )}
        </div>

        <div className="flex-1 space-y-3">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleFileChange}
            className="block w-full text-sm text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
          />
          <button
            type="button"
            className="btn-secondary inline-flex items-center gap-2"
            disabled={!selectedFile || uploadMutation.isPending}
            onClick={() => selectedFile && uploadMutation.mutate(selectedFile)}
          >
            <UploadCloud className="h-4 w-4" />
            {uploadMutation.isPending ? 'Uploading...' : 'Upload Avatar'}
          </button>
        </div>
      </div>
    </div>
  )
}
