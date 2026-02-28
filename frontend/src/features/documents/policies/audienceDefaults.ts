import type { DocumentVisibility, UserRole } from '@/types'

type RoleAudienceDefaultsMap = Record<UserRole, DocumentVisibility>

const ROLE_AUDIENCE_DEFAULTS: RoleAudienceDefaultsMap = {
  system_admin: 'internal',
  admin: 'internal',
  manager: 'internal',
  editor: 'internal',
  viewer: 'public',
  customer: 'company',
}

export function getDefaultAudienceForRole(role: UserRole | null | undefined): DocumentVisibility {
  if (!role) {
    return 'public'
  }
  return ROLE_AUDIENCE_DEFAULTS[role] ?? 'public'
}
