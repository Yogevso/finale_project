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
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-700',
    iconColor: 'text-emerald-600',
    borderColor: 'border-emerald-200',
    description: 'Visible to everyone',
  },
  internal: {
    icon: Building2,
    label: 'Internal',
    bgColor: 'bg-sky-50',
    textColor: 'text-sky-700',
    iconColor: 'text-sky-600',
    borderColor: 'border-sky-200',
    description: 'Visible to internal staff only',
  },
  company: {
    icon: Lock,
    label: 'Company',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    iconColor: 'text-amber-600',
    borderColor: 'border-amber-200',
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
    ? 'px-2 py-0.5 text-xs gap-1' 
    : 'px-2.5 py-1 text-xs gap-1.5'
  
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'
  
  return (
    <span 
      className={`inline-flex items-center rounded-full border ${config.bgColor} ${config.textColor} ${config.borderColor} ${sizeClasses} font-medium`}
      title={config.description}
    >
      <Icon className={`${iconSize} ${config.iconColor}`} />
      {showLabel && <span>{config.label}</span>}
    </span>
  )
}
