import {
  PLATFORM_UPLOAD_MAX_SIZE_BYTES,
  PLATFORM_UPLOAD_MAX_SIZE_LABEL,
} from './uploadLimits'

const MAX_ATTACHMENT_SIZE_BYTES = PLATFORM_UPLOAD_MAX_SIZE_BYTES

const ALLOWED_ATTACHMENT_MIME_TYPES = new Set([
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/pdf',
  'application/json',
  'text/markdown',
  'text/html',
  'text/plain',
  'text/csv',
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
])

const ALLOWED_ATTACHMENT_EXTENSIONS = new Set([
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
  '.pdf',
  '.txt',
  '.md',
  '.html',
  '.htm',
  '.json',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
])

export const ATTACHMENT_INPUT_ACCEPT = Array.from(ALLOWED_ATTACHMENT_EXTENSIONS).join(',')
export const ATTACHMENT_MAX_SIZE_BYTES = MAX_ATTACHMENT_SIZE_BYTES

function getExtension(filename: string): string {
  const lastDot = filename.lastIndexOf('.')
  if (lastDot === -1) {
    return ''
  }
  return filename.slice(lastDot).toLowerCase()
}

export function validateAttachmentFile(file: Pick<File, 'name' | 'size' | 'type'>): string | null {
  if (file.size > MAX_ATTACHMENT_SIZE_BYTES) {
    return `File too large. Max size: ${PLATFORM_UPLOAD_MAX_SIZE_LABEL}.`
  }

  const normalizedType = (file.type || '').toLowerCase()
  const extension = getExtension(file.name)
  if (
    (normalizedType && ALLOWED_ATTACHMENT_MIME_TYPES.has(normalizedType)) ||
    ALLOWED_ATTACHMENT_EXTENSIONS.has(extension)
  ) {
    return null
  }

  return 'File type not allowed. Supported: DOC, DOCX, XLS, XLSX, PPT, PPTX, PDF, TXT, MD, HTML, JSON, CSV, PNG, JPG, GIF, WEBP.'
}
