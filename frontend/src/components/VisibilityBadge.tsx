import { Globe, Building2, Lock } from 'lucide-react'
import type { DocumentVisibility } from '@/types'

interface VisibilityBadgeProps {
  visibility: DocumentVisibility
  showLabel?: boolean
  size?: 'sm' | 'md'
}

const visibilityConfig = {
  public: {
    icon: Globe,
    label: 'Public',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
    iconColor: 'text-green-600',
    description: 'Visible to everyone',
  },
  internal: {
    icon: Building2,
    label: 'Internal',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
    iconColor: 'text-blue-600',
    description: 'Visible to internal staff only',
  },
  company: {
    icon: Lock,
    label: 'Company',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-700',
    iconColor: 'text-orange-600',
    description: 'Visible to assigned companies + staff',
  },
}

export default function VisibilityBadge({ 
  visibility, 
  showLabel = true, 
  size = 'md' 
}: VisibilityBadgeProps) {
  const config = visibilityConfig[visibility] || visibilityConfig.internal
  const Icon = config.icon
  
  const sizeClasses = size === 'sm' 
    ? 'px-1.5 py-0.5 text-xs gap-1' 
    : 'px-2 py-1 text-xs gap-1.5'
  
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'
  
  return (
    <span 
      className={`inline-flex items-center rounded-full ${config.bgColor} ${config.textColor} ${sizeClasses}`}
      title={config.description}
    >
      <Icon className={`${iconSize} ${config.iconColor}`} />
      {showLabel && <span>{config.label}</span>}
    </span>
  )
}
