import type { ReactNode } from 'react'

type NotFoundStateProps = {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

export default function NotFoundState({ title, description, icon, action }: NotFoundStateProps) {
  return (
    <div className="surface-card rounded-2xl p-10 text-center">
      <div className="text-5xl mb-4">{icon || '🔍'}</div>
      <h1 className="text-2xl font-display font-bold text-slate-900 mb-2">{title}</h1>
      {description && <p className="text-slate-500 mb-6">{description}</p>}
      {action}
    </div>
  )
}
