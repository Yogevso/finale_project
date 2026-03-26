import type { UserRole } from '@/types'

export type UserCreateFormData = {
  email: string
  username: string
  full_name: string
  password: string
  role: UserRole
  tenant_id?: number
}

export type UserUpdateFormData = {
  email?: string
  full_name?: string
  role?: UserRole
  is_active?: boolean
  tenant_id?: number | null
}

export type UserFormSubmission = UserCreateFormData | UserUpdateFormData

export type PendingConfirmState = {
  title: string
  description: string
  onConfirm: () => void
} | null
