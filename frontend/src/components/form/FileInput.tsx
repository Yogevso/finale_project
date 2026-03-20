import {
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type InputHTMLAttributes,
} from 'react'
import { FileText, Image as ImageIcon, Upload } from 'lucide-react'
import OptimizedImage from '@/components/OptimizedImage'

import { FormField } from './FormField'

interface FileInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'onChange'> {
  label?: string
  error?: string
  hint?: string
  required?: boolean
  wrapperClassName?: string
  onChange?: (event: ChangeEvent<HTMLInputElement>) => void
  onFilesChange?: (files: File[]) => void
}

export function FileInput({
  id,
  label,
  error,
  hint,
  required = false,
  className = '',
  wrapperClassName = '',
  multiple = false,
  accept,
  disabled,
  onChange,
  onFilesChange,
  ...props
}: FileInputProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [previewUrls, setPreviewUrls] = useState<string[]>([])

  useEffect(() => {
    const nextPreviewUrls = selectedFiles
      .filter((file) => file.type.startsWith('image/'))
      .slice(0, 3)
      .map((file) => URL.createObjectURL(file))

    setPreviewUrls(nextPreviewUrls)

    return () => {
      nextPreviewUrls.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [selectedFiles])

  const updateFiles = (files: FileList | null) => {
    const nextFiles = Array.from(files ?? [])
    setSelectedFiles(nextFiles)
    onFilesChange?.(nextFiles)
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    updateFiles(event.target.files)
    onChange?.(event)
  }

  const content = (
    <div className="space-y-3">
      <input
        {...props}
        id={inputId}
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        required={required}
        className="sr-only"
        onChange={handleFileChange}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) {
            setIsDragging(true)
          }
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          if (disabled) {
            return
          }
          updateFiles(event.dataTransfer.files)
        }}
        className={[
          'flex w-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed px-5 py-8 text-center transition',
          isDragging
            ? 'border-sky-500 bg-sky-50 dark:bg-sky-950/30'
            : 'border-slate-300 bg-slate-50/80 hover:border-slate-400 hover:bg-white dark:border-slate-700 dark:bg-slate-900/70 dark:hover:border-slate-600',
          error ? 'border-rose-300 motion-error-shake dark:border-rose-800' : '',
          className,
        ].filter(Boolean).join(' ')}
        disabled={disabled}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-sky-600 shadow-sm dark:bg-slate-950 dark:text-sky-400">
          <Upload className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
            Drag and drop files here
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            or click to browse {multiple ? 'multiple files' : 'a file'}
          </p>
        </div>
      </button>
      {selectedFiles.length > 0 ? (
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Selected files
          </p>
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <div key={`${file.name}-${index}`} className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-950/70">
                {file.type.startsWith('image/') ? (
                  <ImageIcon className="h-4 w-4 text-sky-600 dark:text-sky-400" aria-hidden="true" />
                ) : (
                  <FileText className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden="true" />
                )}
                <span className="truncate text-sm text-slate-700 dark:text-slate-200">{file.name}</span>
              </div>
            ))}
          </div>
          {previewUrls.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-3">
              {previewUrls.map((url) => (
                <OptimizedImage
                  key={url}
                  src={url}
                  alt="Selected file preview"
                  className="h-28 w-full rounded-xl object-cover"
                  height={112}
                  sizes="(min-width: 640px) 33vw, 100vw"
                  width={320}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )

  if (label) {
    return (
      <FormField
        label={label}
        htmlFor={inputId}
        error={error}
        hint={hint}
        required={required}
        className={wrapperClassName}
      >
        {content}
      </FormField>
    )
  }

  return content
}
