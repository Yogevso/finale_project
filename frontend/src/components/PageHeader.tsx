import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  eyebrow?: string
  actions?: ReactNode
  meta?: ReactNode
  className?: string
}

export default function PageHeader({
  title,
  subtitle,
  eyebrow = 'Internal Portal',
  actions,
  meta,
  className = '',
}: PageHeaderProps) {
  return (
    <section
      className={`surface-card rounded-2xl border border-sky-100 bg-gradient-to-r from-white via-sky-50/70 to-white px-6 py-5 ${className}`.trim()}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500">{eyebrow}</div>
          <h1 className="text-2xl md:text-3xl font-display font-bold text-slate-900 mt-1">{title}</h1>
          {subtitle && <p className="text-slate-600 mt-1">{subtitle}</p>}
          {meta && <div className="mt-3">{meta}</div>}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </section>
  )
}

